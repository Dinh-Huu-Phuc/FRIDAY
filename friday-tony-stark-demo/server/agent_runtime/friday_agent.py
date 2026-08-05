from __future__ import annotations

import asyncio
import os
from collections import deque

from livekit.agents import StopResponse
from livekit.agents.llm import mcp
from livekit.agents.voice import Agent
from livekit.plugins import silero

from friday.about import match_about_response
from friday.app import open_social_platform, resolve_social_platform
from friday.app.agent_console.greeting_engine import build_time_greeting
from friday.app.browser_automation import (
    is_binance_market_request,
    is_browser_search_request,
    is_platform_video_search_request,
    run_binance_market,
    run_browser_search,
    run_platform_video_search,
)
from friday.app.computer import (
    is_screen_understanding_request,
    understand_current_screen,
)
from friday.app.computer.dependencies import get_computer_service
from friday.app.computer.schemas.requests import RunRequest
from friday.app.computer.schemas.responses import RunResponse
from friday.app.messenger import (
    check_latest_messenger_message,
    is_messenger_latest_request,
)
from friday.app.power import (
    PowerIntent,
    detect_power_intent,
    get_power_state,
    handle_power_message,
    minimize_application_windows,
    restore_application_windows,
)
from friday.app.research import (
    SEARCH_ACKNOWLEDGEMENT,
    build_web_research_context,
    is_web_research_request,
    research_public_web,
    should_announce_search,
)
from friday.app.secure_browser import handle_secure_browser_message
from friday.app.windows_launcher.service import open_app as open_windows_app
from friday.gmail_system_agent import (
    check_unread_gmail_with_timeout,
    format_gmail_report,
)
from friday.messages.promt_agent_friday import build_daily_briefing_runtime_hint
from friday.news import NewsService
from friday.prompts import build_social_open_runtime_hint
from friday.refiner import STTCorrector
from friday.trainModel.memory import MemoryManager
from server.agent_runtime.bootstrap import logger, mcp_server_url
from server.agent_runtime.intents import (
    extract_windows_app_query,
    is_daily_briefing_request,
    is_gmail_check_request,
    is_social_open_request,
)
from server.agent_runtime.providers import GOOGLE_STT_LANGUAGE
from server.agent_runtime.runtime_hints import build_windows_launcher_runtime_hint
from server.agent_runtime.startup import build_startup_greeting_message
from server.prompts.agent_friday import build_runtime_agent_instructions


def run_computer_agent_cycle(goal: str, *, safety_mode: str | None = None) -> RunResponse:
    """
    Execute one observe -> plan -> safety-check -> execute cycle through the
    dedicated computer service layer.
    """
    service = get_computer_service()
    request = RunRequest(goal=goal, safety_mode=safety_mode)
    return service.run_single_cycle(request)


class FridayAgent(Agent):
    """
    F.R.I.D.A.Y. voice assistant.
    All tools are provided via the MCP server on the Windows host.
    """

    def __init__(
        self,
        stt,
        llm,
        tts,
        memory_manager: MemoryManager | None = None,
        memory_session_id: str = "",
        stt_corrector: STTCorrector | None = None,
        news_service: NewsService | None = None,
    ) -> None:
        self._memory_manager = memory_manager
        self._memory_session_id = memory_session_id
        self._memory_user_id: str | None = None
        self._stt_corrector = stt_corrector
        self._news_service = news_service
        self._pending_user_turns: deque[dict[str, str | bool | None]] | None = None
        super().__init__(
            instructions=build_runtime_agent_instructions(),
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            mcp_servers=[
                mcp.MCPServerHTTP(
                    url=mcp_server_url(),
                    transport_type="sse",
                    client_session_timeout_seconds=30,
                ),
            ],
        )

    async def on_enter(self) -> None:
        """Greet the user based on the machine's current local time."""
        if get_power_state().sleeping:
            logger.info("FRIDAY entered while sleeping; startup greeting skipped")
            return
        if os.getenv("FRIDAY_START_MODE", "fast").strip().lower() == "fast":
            await self.session.say(build_time_greeting(event="startup"), add_to_chat_ctx=True)
            if os.getenv("FRIDAY_BACKGROUND_WARMUP", "true").lower() in {"1", "true", "yes", "on"}:
                asyncio.create_task(self._deliver_startup_briefing())
            return
        await self.session.say(
            await build_startup_greeting_message(),
            add_to_chat_ctx=True,
        )

    async def _deliver_startup_briefing(self) -> None:
        try:
            message = await build_startup_greeting_message()
            if not get_power_state().sleeping:
                await self.session.say(message, add_to_chat_ctx=True)
        except Exception as exc:
            logger.warning("Background startup briefing failed: %s", type(exc).__name__)

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """
        Inject runtime memory context into each user turn before the model responds.
        """
        if hasattr(new_message, "extra") and isinstance(new_message.extra, dict):
            speaker_id = new_message.extra.get("speaker_id") or new_message.extra.get("participant_identity")
            if isinstance(speaker_id, str) and speaker_id.strip():
                self._memory_user_id = speaker_id.strip()

        raw_user_text = (new_message.text_content or "").strip()
        if not raw_user_text:
            return

        previous_power_state = get_power_state()
        power_intent = detect_power_intent(raw_user_text)
        power_result = handle_power_message(
            raw_user_text,
            source="livekit",
            silent_when_sleeping=True,
        )
        if power_result.handled:
            logger.info("Power command handled state=%s", power_result.snapshot.state)
            if power_intent == PowerIntent.WAKE:
                restore_result = await asyncio.to_thread(restore_application_windows)
                logger.info("Window restore result: %s", restore_result.message)
            if power_result.reply:
                await self.session.say(power_result.reply, add_to_chat_ctx=True)
            if power_intent == PowerIntent.SLEEP and not previous_power_state.sleeping:
                minimize_result = await asyncio.to_thread(minimize_application_windows)
                logger.info("Window minimize result: %s", minimize_result.message)
            raise StopResponse()

        refined_user_text = raw_user_text
        refiner_provider = "disabled"
        refiner_fallback = True
        if self._stt_corrector is not None:
            memory_hint = ""
            if self._memory_manager is not None and self._memory_session_id:
                memory_context = self._memory_manager.load_memory_for_response(
                    session_id=self._memory_session_id,
                    user_id=self._memory_user_id,
                )
                memory_hint = str(memory_context.get("session_summary") or "")

            correction = await asyncio.to_thread(
                self._stt_corrector.correct,
                raw_user_text,
                language=GOOGLE_STT_LANGUAGE,
                conversation_hint=memory_hint[:300],
            )
            refined_user_text = correction.refined_text or raw_user_text
            refiner_provider = correction.provider
            refiner_fallback = correction.fallback_used

            logger.info(
                "STT refiner provider=%s fallback=%s raw='%s' refined='%s'",
                refiner_provider,
                refiner_fallback,
                raw_user_text[:160],
                refined_user_text[:160],
            )

        if should_announce_search(refined_user_text):
            await self.session.say(SEARCH_ACKNOWLEDGEMENT, add_to_chat_ctx=False)

        if is_binance_market_request(refined_user_text):
            binance_result = await asyncio.to_thread(
                run_binance_market,
                refined_user_text,
            )
            logger.info(
                "Binance market workflow completed ok=%s symbol='%s' url='%s'",
                binance_result.ok,
                binance_result.query,
                binance_result.url,
            )
            await self.session.say(binance_result.message, add_to_chat_ctx=True)
            raise StopResponse()

        if is_platform_video_search_request(refined_user_text):
            video_result = await asyncio.to_thread(
                run_platform_video_search,
                refined_user_text,
            )
            logger.info(
                "Platform video search completed ok=%s platform=%s query='%s' rank=%s",
                video_result.ok,
                video_result.platform,
                video_result.query[:160],
                video_result.selected_rank,
            )
            await self.session.say(video_result.message, add_to_chat_ctx=True)
            raise StopResponse()

        if is_browser_search_request(refined_user_text):
            browser_result = await asyncio.to_thread(run_browser_search, refined_user_text)
            logger.info(
                "Chrome search workflow completed ok=%s query='%s' url='%s'",
                browser_result.ok,
                browser_result.query[:160],
                browser_result.url[:240],
            )
            await self.session.say(browser_result.message, add_to_chat_ctx=True)
            raise StopResponse()

        secure_browser_result = handle_secure_browser_message(refined_user_text)
        if secure_browser_result.handled:
            logger.info(
                "FRIDAY Browser command completed accepted=%s action=%s",
                secure_browser_result.accepted,
                secure_browser_result.action.value,
            )
            await self.session.say(
                secure_browser_result.message,
                add_to_chat_ctx=True,
            )
            raise StopResponse()

        if is_messenger_latest_request(refined_user_text):
            messenger_result = await asyncio.to_thread(check_latest_messenger_message)
            logger.info(
                "Messenger latest-message workflow completed ok=%s login_required=%s",
                messenger_result.ok,
                messenger_result.login_required,
            )
            await self.session.say(messenger_result.message, add_to_chat_ctx=True)
            raise StopResponse()

        if is_screen_understanding_request(refined_user_text):
            logger.info("Explicit local screen understanding request detected")
            screen_reply = await understand_current_screen(refined_user_text)
            await self.session.say(screen_reply, add_to_chat_ctx=True)
            raise StopResponse()

        social_platform: str | None = None
        social_open_result = ""
        if is_social_open_request(refined_user_text):
            social_platform = resolve_social_platform(refined_user_text)
            social_open_result = await asyncio.to_thread(
                open_social_platform,
                refined_user_text,
            )
            logger.info(
                "Social open request detected platform=%s result=%s text='%s'",
                social_platform,
                social_open_result,
                refined_user_text[:160],
            )

        windows_launcher_hint = ""
        if not social_open_result:
            windows_app_query = extract_windows_app_query(refined_user_text)
            if windows_app_query:
                windows_open_response = await asyncio.to_thread(
                    open_windows_app,
                    query=windows_app_query,
                )
                windows_launcher_hint = build_windows_launcher_runtime_hint(
                    command=refined_user_text,
                    app_query=windows_app_query,
                    result=windows_open_response.model_dump(mode="json"),
                )
                logger.info(
                    "Windows app open request detected query=%s ok=%s text='%s'",
                    windows_app_query,
                    windows_open_response.ok,
                    refined_user_text[:160],
                )

        daily_briefing_hint = ""
        if is_daily_briefing_request(refined_user_text):
            daily_briefing_hint = build_daily_briefing_runtime_hint()

        about_match = match_about_response(refined_user_text, response_type="voice")
        if not social_open_result and about_match.matched:
            logger.info(
                "About self-intro detected document=%s text='%s'",
                about_match.document_id,
                refined_user_text[:160],
            )
            await self.session.say(about_match.response, add_to_chat_ctx=True)
            raise StopResponse()

        gmail_hint = ""
        if not social_open_result and is_gmail_check_request(refined_user_text):
            gmail_result = await check_unread_gmail_with_timeout()
            gmail_report = format_gmail_report(gmail_result)
            logger.info(
                "Gmail check detected ok=%s unread=%s reported=%s skipped=%s text='%s'",
                gmail_result.ok,
                gmail_result.unread_count,
                gmail_result.reported_count,
                gmail_result.skipped_count,
                refined_user_text[:160],
            )
            await self.session.say(gmail_report, add_to_chat_ctx=True)
            raise StopResponse()

        news_status = "not_news"
        news_topic: str | None = None
        news_country: str | None = None
        news_count = 0
        news_context = ""
        web_research_context = ""
        web_research_url = ""
        if not social_open_result and not gmail_hint and self._news_service is not None:
            try:
                news_result = await asyncio.to_thread(
                    self._news_service.handle_user_query,
                    refined_user_text,
                )
                if news_result.is_news_intent:
                    news_status = news_result.status
                    news_topic = news_result.query.topic
                    news_country = news_result.query.country
                    news_count = news_result.article_count
                    news_context = news_result.agent_context
                    logger.info(
                        "News intent detected status=%s topic=%s country=%s count=%s",
                        news_status,
                        news_topic,
                        news_country,
                        news_count,
                    )
            except Exception as exc:
                logger.warning("News service failed with fallback context: %s", exc)
                news_status = "error"
                news_context = (
                    "[NEWS_CONTEXT]\n"
                    "status=error\n"
                    "fallback_user_message=The news feed is unstable, boss. Would you like me to retry?\n"
                    "response_rules=Reply briefly in English without exposing implementation details."
                )

        should_research_web = bool(
            not social_open_result
            and is_web_research_request(refined_user_text)
            and news_status in {"not_news", "error", "no_data"}
        )
        if should_research_web:
            research_result = await asyncio.to_thread(
                research_public_web,
                refined_user_text,
            )
            web_research_context = build_web_research_context(research_result)
            web_research_url = research_result.url
            if web_research_context:
                news_context = ""
                logger.info(
                    "Web research completed query='%s' url='%s'",
                    research_result.query[:160],
                    research_result.url[:240],
                )
            elif news_status == "not_news":
                await self.session.say(research_result.message, add_to_chat_ctx=True)
                raise StopResponse()

        if self._pending_user_turns is not None:
            self._upsert_pending_turn(
                raw_text=raw_user_text,
                refined_text=refined_user_text,
                user_id=self._memory_user_id,
                provider=refiner_provider,
                fallback=refiner_fallback,
            )

        if self._memory_manager is None or not self._memory_session_id:
            if social_open_result:
                social_hint = build_social_open_runtime_hint(
                    command=refined_user_text,
                    platform_name=social_platform,
                    assistant_reply=social_open_result,
                )
                new_message.content = [f"{social_hint}\n\n[CURRENT_USER_MESSAGE]\n{refined_user_text}"]
            elif windows_launcher_hint:
                new_message.content = [f"{windows_launcher_hint}\n\n[CURRENT_USER_MESSAGE]\n{refined_user_text}"]
            elif daily_briefing_hint:
                new_message.content = [f"{daily_briefing_hint}\n\n[CURRENT_USER_MESSAGE]\n{refined_user_text}"]
            elif gmail_hint:
                new_message.content = [f"{gmail_hint}\n\n[CURRENT_USER_MESSAGE]\n{refined_user_text}"]
            elif news_context:
                new_message.content = [f"{news_context}\n\n[CURRENT_USER_MESSAGE]\n{refined_user_text}"]
            elif web_research_context:
                new_message.content = [
                    f"{web_research_context}\n\n[CURRENT_USER_MESSAGE]\n{refined_user_text}"
                ]
            else:
                new_message.content = [refined_user_text]
            return

        memory_prefix = self._memory_manager.build_instruction_prefix(
            session_id=self._memory_session_id,
            user_id=self._memory_user_id,
        )
        composed_parts = [memory_prefix.strip()]
        if social_open_result:
            composed_parts.append(
                build_social_open_runtime_hint(
                    command=refined_user_text,
                    platform_name=social_platform,
                    assistant_reply=social_open_result,
                ).strip()
            )
        elif windows_launcher_hint:
            composed_parts.append(windows_launcher_hint.strip())
        elif daily_briefing_hint:
            composed_parts.append(daily_briefing_hint.strip())
        elif gmail_hint:
            composed_parts.append(gmail_hint.strip())
        elif news_context:
            composed_parts.append(news_context.strip())
        elif web_research_context:
            composed_parts.append(web_research_context.strip())
        composed_parts.append(f"[CURRENT_USER_MESSAGE]\n{refined_user_text}")
        new_message.content = ["\n\n".join(part for part in composed_parts if part)]

        if not hasattr(new_message, "extra") or not isinstance(new_message.extra, dict):
            new_message.extra = {}
        new_message.extra["raw_user_message"] = raw_user_text
        new_message.extra["refined_user_message"] = refined_user_text
        new_message.extra["stt_refiner_provider"] = refiner_provider
        new_message.extra["stt_refiner_fallback"] = refiner_fallback
        new_message.extra["news_status"] = news_status
        new_message.extra["news_topic"] = news_topic
        new_message.extra["news_country"] = news_country
        new_message.extra["news_count"] = news_count
        new_message.extra["web_research_url"] = web_research_url
        new_message.extra["social_open_platform"] = social_platform
        new_message.extra["social_open_result"] = social_open_result
        new_message.extra["windows_launcher_used"] = bool(windows_launcher_hint)
        new_message.extra["daily_briefing_requested"] = bool(daily_briefing_hint)
        new_message.extra["gmail_check_requested"] = bool(gmail_hint)

    def bind_pending_turns(self, queue: deque[dict[str, str | bool | None]]) -> None:
        self._pending_user_turns = queue

    def _upsert_pending_turn(
        self,
        *,
        raw_text: str,
        refined_text: str,
        user_id: str | None,
        provider: str,
        fallback: bool,
    ) -> None:
        if self._pending_user_turns is None:
            return
        raw_norm = raw_text.strip().lower()
        for item in reversed(self._pending_user_turns):
            queued_raw = str(item.get("raw_text") or "").strip().lower()
            if queued_raw == raw_norm:
                item["refined_text"] = refined_text
                item["provider"] = provider
                item["fallback"] = fallback
                if user_id:
                    item["user_id"] = user_id
                return
        self._pending_user_turns.append(
            {
                "user_id": user_id,
                "raw_text": raw_text,
                "refined_text": refined_text,
                "provider": provider,
                "fallback": fallback,
            }
        )
