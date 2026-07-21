"""
FRIDAY - Voice Agent (MCP-powered)
==================================
Iron Man-style voice assistant that controls RGB lighting, runs diagnostics,
scans the network, and triggers dramatic boot sequences via an MCP server
running on the Windows host.

MCP Server URL is auto-resolved from WSL to Windows host IP.

Run:
  uv run server/agent_friday.py dev      - LiveKit Cloud mode
  uv run server/agent_friday.py console  - text-only console mode
"""

from collections import deque

from friday.config import config
from friday.app.power import PowerIntent, detect_power_intent, get_power_state
from friday.log import DailyInteractionLogger
from friday.refiner import STTCorrector
from friday.trainModel import ConversationDatasetStore
from friday.trainModel.memory import MemoryManager
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession
from server.agent_runtime.bootstrap import bootstrap_environment, logger

bootstrap_environment()

from server.agent_runtime.friday_agent import FridayAgent
from server.agent_runtime.providers import (
    GEMINI_LLM_MODEL,
    GOOGLE_STT_MODEL,
    LLM_PROVIDER,
    OPENAI_LLM_MODEL,
    OPENAI_TTS_MODEL,
    STT_PROVIDER,
    TTS_PROVIDER,
    build_llm,
    build_stt,
    build_tts,
    endpointing_delay,
    turn_detection,
)
from server.agent_runtime.training import build_news_service, build_train_model_config, get_or_start_scheduler

# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------


def _extract_user_text_from_content(text: str) -> str:
    marker = "[CURRENT_USER_MESSAGE]"
    content = (text or "").strip()
    if marker in content:
        return content.split(marker, maxsplit=1)[1].strip()
    return content


async def entrypoint(ctx: JobContext) -> None:
    logger.info(
        "FRIDAY online - room: %s | STT=%s | LLM=%s | TTS=%s",
        ctx.room.name,
        STT_PROVIDER,
        LLM_PROVIDER,
        TTS_PROVIDER,
    )

    stt = build_stt()
    llm = build_llm()
    tts = build_tts()
    train_cfg = build_train_model_config()
    dataset_store = ConversationDatasetStore(train_cfg)
    scheduler = get_or_start_scheduler(train_cfg)
    news_service = build_news_service()
    stt_corrector = STTCorrector(
        enabled=config.STT_REFINER_ENABLED,
        provider_name=config.STT_REFINER_PROVIDER,
        groq_api_key=config.GROQ_API_KEY,
        groq_model=config.GROQ_MODEL,
        openai_api_key=config.OPENAI_API_KEY,
        timeout_seconds=config.STT_REFINER_TIMEOUT,
    )
    memory_manager = MemoryManager()
    memory_session_id = f"room:{ctx.room.name}"
    agent = FridayAgent(
        stt=stt,
        llm=llm,
        tts=tts,
        memory_manager=memory_manager,
        memory_session_id=memory_session_id,
        stt_corrector=stt_corrector,
        news_service=news_service,
    )

    session = AgentSession(
        turn_detection=turn_detection(),
        min_endpointing_delay=endpointing_delay(),
    )
    interaction_logger = DailyInteractionLogger()
    interaction_logger.attach(
        session,
        room_name=ctx.room.name,
        agent_name=agent.__class__.__name__,
        metadata={
            "stt_provider": STT_PROVIDER,
            "llm_provider": LLM_PROVIDER,
            "tts_provider": TTS_PROVIDER,
            "stt_model": GOOGLE_STT_MODEL if STT_PROVIDER == "google" else None,
            "llm_model": GEMINI_LLM_MODEL if LLM_PROVIDER == "gemini" else OPENAI_LLM_MODEL,
            "tts_model": OPENAI_TTS_MODEL if TTS_PROVIDER == "openai" else "bulbul:v3",
        },
    )

    pending_user_turns: deque[dict[str, str | bool | None]] = deque()
    agent.bind_pending_turns(pending_user_turns)

    def _enqueue_user_turn(
        user_id: str | None,
        raw_text: str,
        refined_text: str | None = None,
        provider: str | None = None,
        fallback: bool = True,
    ) -> None:
        raw = (raw_text or "").strip()
        refined = (refined_text or "").strip()
        if not raw and not refined:
            return
        latest = pending_user_turns[-1] if pending_user_turns else None
        if latest and (latest.get("raw_text") == raw or latest.get("refined_text") == refined):
            return
        pending_user_turns.append(
            {
                "user_id": user_id,
                "raw_text": raw,
                "refined_text": refined or raw,
                "provider": provider,
                "fallback": fallback,
            }
        )

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(event) -> None:
        if not getattr(event, "is_final", False):
            return
        transcript = str(getattr(event, "transcript", "") or "").strip()
        if get_power_state().sleeping and detect_power_intent(transcript) != PowerIntent.WAKE:
            return
        _enqueue_user_turn(
            getattr(event, "speaker_id", None),
            raw_text=transcript,
            refined_text=transcript,
            provider="stt",
            fallback=False,
        )

    @session.on("conversation_item_added")
    def _on_conversation_item_added(event) -> None:
        item = getattr(event, "item", None)
        if item is None or getattr(item, "type", None) != "message":
            return

        role = getattr(item, "role", "")
        text = (getattr(item, "text_content", None) or "").strip()
        if not text:
            return

        if role == "user":
            if get_power_state().sleeping and detect_power_intent(text) != PowerIntent.WAKE:
                return
            if not pending_user_turns:
                extracted = _extract_user_text_from_content(text)
                _enqueue_user_turn(
                    None,
                    raw_text=extracted,
                    refined_text=extracted,
                    provider="text_input",
                    fallback=False,
                )
            return

        if role == "assistant" and pending_user_turns:
            user_turn = pending_user_turns.popleft()
            refined_text = str(user_turn.get("refined_text") or user_turn.get("raw_text") or "")
            raw_text = str(user_turn.get("raw_text") or "")
            provider = str(user_turn.get("provider") or "unknown")
            fallback = bool(user_turn.get("fallback"))
            memory_manager.update_memory_after_response(
                session_id=memory_session_id,
                user_id=user_turn.get("user_id"),
                user_message=refined_text,
                assistant_message=text,
                metadata={
                    "source": "agent_session_events",
                    "room_name": ctx.room.name,
                    "refiner_provider": provider,
                    "refiner_fallback": fallback,
                },
            )
            if isinstance(user_turn.get("user_id"), str) and user_turn.get("user_id"):
                agent._memory_user_id = str(user_turn.get("user_id"))
            dataset_store.append_raw_turn(
                session_id=memory_session_id,
                user_id=str(user_turn.get("user_id")) if user_turn.get("user_id") else None,
                user_message=refined_text,
                assistant_message=text,
                source="agent_runtime",
                refined_input=refined_text if refined_text != raw_text else None,
                metadata={
                    "room_name": ctx.room.name,
                    "raw_user_message": raw_text,
                    "refiner_provider": provider,
                    "refiner_fallback": fallback,
                },
            )

    @session.on("close")
    def _on_close(_) -> None:
        if scheduler.state.running:
            logger.info("Scheduler is active with latest trigger=%s", scheduler.state.last_trigger_reason)

    await session.start(
        agent=agent,
        room=ctx.room,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


def dev():
    """Wrapper to run the agent in dev mode automatically."""
    import sys

    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()


if __name__ == "__main__":
    main()

