from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Any

from livekit.agents.llm import ChatMessage, FunctionCall, FunctionCallOutput

from friday.log.paths import friday_save_log_dir


class DailyInteractionLogger:
    """Persist agent and user interaction events into a daily JSON file."""

    _TRACKED_EVENTS = (
        "user_state_changed",
        "agent_state_changed",
        "user_input_transcribed",
        "conversation_item_added",
        "agent_false_interruption",
        "overlapping_speech",
        "function_tools_executed",
        "session_usage_updated",
        "speech_created",
        "error",
        "close",
    )

    def __init__(
        self,
        *,
        save_dir: str | Path | None = None,
        tzinfo: tzinfo | None = None,
    ) -> None:
        self._save_dir = Path(save_dir) if save_dir else friday_save_log_dir()
        self._save_dir.mkdir(parents=True, exist_ok=True)

        self._tzinfo = tzinfo or datetime.now().astimezone().tzinfo or timezone.utc
        self._lock = threading.Lock()
        self._session_id = self._build_session_id()
        self._session_info: dict[str, Any] = {}
        self._attached = False

    @property
    def session_id(self) -> str:
        return self._session_id

    def attach(
        self,
        session: Any,
        *,
        room_name: str | None = None,
        agent_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._attached:
            raise RuntimeError("DailyInteractionLogger is already attached to a session.")

        started_at = self._now()
        self._session_info = {
            "session_id": self._session_id,
            "room_name": room_name,
            "agent_name": agent_name,
            "started_at": self._isoformat(started_at),
            "started_at_unix": started_at.timestamp(),
            "status": "running",
            "metadata": metadata or {},
        }

        for event_name in self._TRACKED_EVENTS:
            session.on(event_name, self._build_handler(event_name))

        self._attached = True
        self._append_event(
            event_type="session_started",
            payload={
                "room_name": room_name,
                "agent_name": agent_name,
                "metadata": metadata or {},
            },
            created_at=started_at.timestamp(),
        )

    def record_custom_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
        created_at: float | None = None,
    ) -> None:
        timestamp = created_at if created_at is not None else self._now().timestamp()
        self._append_event(
            event_type=event_type,
            payload=payload or {},
            created_at=timestamp,
        )

    def _build_handler(self, event_name: str):
        def _handler(event: Any) -> None:
            created_at = getattr(event, "created_at", self._now().timestamp())
            payload = self._serialize_event(event_name=event_name, event=event)
            self._append_event(
                event_type=event_name,
                payload=payload,
                created_at=created_at,
            )

        return _handler

    def _append_event(self, *, event_type: str, payload: dict[str, Any], created_at: float) -> None:
        with self._lock:
            dt = datetime.fromtimestamp(created_at, tz=self._tzinfo)
            data = self._load_daily_data(dt)

            self._ensure_session_entry(data, dt)

            event_record = {
                "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                "session_id": self._session_id,
                "event_type": event_type,
                "created_at": created_at,
                "timestamp": self._isoformat(dt),
                "payload": payload,
            }
            data["events"].append(event_record)

            session_entry = data["sessions"][self._session_id]
            session_entry["last_event_at"] = self._isoformat(dt)
            session_entry["last_event_at_unix"] = created_at

            if event_type == "close":
                session_entry["status"] = "closed"
                session_entry["closed_at"] = self._isoformat(dt)
                session_entry["closed_at_unix"] = created_at

            self._update_summary(data, event_record)
            data["updated_at"] = self._isoformat(self._now())
            self._write_daily_data(dt, data)

    def _update_summary(self, data: dict[str, Any], event_record: dict[str, Any]) -> None:
        summary = data["summary"]
        summary["total_events"] = len(data["events"])
        summary["sessions"] = len(data["sessions"])

        event_type = event_record["event_type"]
        payload = event_record["payload"]

        if event_type == "conversation_item_added":
            item = payload.get("item", {})
            if item.get("type") == "message":
                role = item.get("role")
                if role == "user":
                    summary["user_messages"] += 1
                elif role == "assistant":
                    summary["agent_messages"] += 1
        elif event_type == "function_tools_executed":
            calls = payload.get("function_calls", [])
            outputs = payload.get("function_call_outputs", [])
            summary["tool_calls"] += len(calls)
            summary["tool_errors"] += sum(
                1 for output in outputs if isinstance(output, dict) and output.get("is_error")
            )
        elif event_type == "error":
            summary["errors"] += 1

    def _ensure_session_entry(self, data: dict[str, Any], dt: datetime) -> None:
        session_entry = data["sessions"].setdefault(
            self._session_id,
            {
                "session_id": self._session_id,
                "room_name": self._session_info.get("room_name"),
                "agent_name": self._session_info.get("agent_name"),
                "started_at": self._session_info.get("started_at"),
                "started_at_unix": self._session_info.get("started_at_unix"),
                "metadata": self._session_info.get("metadata", {}),
                "status": self._session_info.get("status", "running"),
                "date": dt.date().isoformat(),
                "last_event_at": self._isoformat(dt),
                "last_event_at_unix": dt.timestamp(),
                "closed_at": None,
                "closed_at_unix": None,
            },
        )

        session_entry["status"] = self._session_info.get("status", session_entry.get("status", "running"))

    def _load_daily_data(self, dt: datetime) -> dict[str, Any]:
        path = self._daily_file_path(dt)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        return {
            "date": dt.date().isoformat(),
            "updated_at": self._isoformat(self._now()),
            "summary": {
                "total_events": 0,
                "sessions": 0,
                "user_messages": 0,
                "agent_messages": 0,
                "tool_calls": 0,
                "tool_errors": 0,
                "errors": 0,
            },
            "sessions": {},
            "events": [],
        }

    def _write_daily_data(self, dt: datetime, data: dict[str, Any]) -> None:
        path = self._daily_file_path(dt)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _daily_file_path(self, dt: datetime) -> Path:
        return self._save_dir / f"{dt.date().isoformat()}.json"

    def _serialize_event(self, *, event_name: str, event: Any) -> dict[str, Any]:
        if event_name in {"user_state_changed", "agent_state_changed"}:
            return {
                "old_state": getattr(event, "old_state", None),
                "new_state": getattr(event, "new_state", None),
            }

        if event_name == "user_input_transcribed":
            return {
                "transcript": getattr(event, "transcript", None),
                "is_final": getattr(event, "is_final", None),
                "speaker_id": getattr(event, "speaker_id", None),
                "language": self._safe_value(getattr(event, "language", None)),
            }

        if event_name == "conversation_item_added":
            return {
                "item": self._serialize_conversation_item(getattr(event, "item", None)),
            }

        if event_name == "agent_false_interruption":
            return {
                "resumed": getattr(event, "resumed", None),
            }

        if event_name == "overlapping_speech":
            return self._safe_model_dump(event)

        if event_name == "function_tools_executed":
            function_calls = [self._serialize_function_call(item) for item in event.function_calls]
            function_call_outputs = [
                self._serialize_function_output(item) if item is not None else None
                for item in event.function_call_outputs
            ]
            return {
                "has_tool_reply": getattr(event, "has_tool_reply", False),
                "has_agent_handoff": getattr(event, "has_agent_handoff", False),
                "function_calls": function_calls,
                "function_call_outputs": function_call_outputs,
            }

        if event_name == "session_usage_updated":
            usage = getattr(event, "usage", None)
            return self._safe_model_dump(usage)

        if event_name == "speech_created":
            speech_handle = getattr(event, "speech_handle", None)
            return {
                "user_initiated": getattr(event, "user_initiated", None),
                "source": getattr(event, "source", None),
                "speech_id": getattr(speech_handle, "id", None),
                "allow_interruptions": getattr(speech_handle, "allow_interruptions", None),
            }

        if event_name == "error":
            return {
                "source": self._safe_value(getattr(event, "source", None)),
                "error": self._serialize_error(getattr(event, "error", None)),
            }

        if event_name == "close":
            self._session_info["status"] = "closed"
            return {
                "reason": self._safe_value(getattr(event, "reason", None)),
                "error": self._serialize_error(getattr(event, "error", None)),
            }

        return self._safe_model_dump(event)

    def _serialize_conversation_item(self, item: Any) -> dict[str, Any]:
        if item is None:
            return {"type": "unknown", "value": None}

        item_type = getattr(item, "type", None)
        if item_type == "message" or isinstance(item, ChatMessage):
            return self._serialize_chat_message(item)
        if item_type == "function_call" or isinstance(item, FunctionCall):
            return self._serialize_function_call(item)
        if item_type == "function_call_output" or isinstance(item, FunctionCallOutput):
            return self._serialize_function_output(item)

        return self._safe_model_dump(item)

    def _serialize_chat_message(self, message: ChatMessage) -> dict[str, Any]:
        return {
            "id": message.id,
            "type": message.type,
            "role": message.role,
            "text": message.text_content,
            "interrupted": message.interrupted,
            "transcript_confidence": message.transcript_confidence,
            "metrics": self._safe_value(message.metrics),
            "created_at": message.created_at,
            "timestamp": self._isoformat_from_ts(message.created_at),
            "content": [self._serialize_chat_content(item) for item in message.content],
            "extra": self._safe_value(message.extra),
        }

    def _serialize_chat_content(self, item: Any) -> dict[str, Any]:
        if isinstance(item, str):
            return {"type": "text", "text": item}

        item_type = getattr(item, "type", item.__class__.__name__)

        if item_type == "instructions":
            return {"type": "instructions", "text": str(item)}

        if item_type == "image_content":
            image_value = getattr(item, "image", None)
            if isinstance(image_value, str):
                image_kind = "url_or_data"
            else:
                image_kind = image_value.__class__.__name__ if image_value is not None else None

            return {
                "type": "image_content",
                "image_kind": image_kind,
                "mime_type": getattr(item, "mime_type", None),
                "inference_width": getattr(item, "inference_width", None),
                "inference_height": getattr(item, "inference_height", None),
                "inference_detail": getattr(item, "inference_detail", None),
            }

        if item_type == "audio_content":
            frames = getattr(item, "frame", None) or []
            return {
                "type": "audio_content",
                "transcript": getattr(item, "transcript", None),
                "frame_count": len(frames),
            }

        return {"type": str(item_type), "value": self._safe_value(item)}

    def _serialize_function_call(self, item: FunctionCall) -> dict[str, Any]:
        return {
            "id": item.id,
            "type": item.type,
            "call_id": item.call_id,
            "name": item.name,
            "arguments": item.arguments,
            "group_id": item.group_id,
            "created_at": item.created_at,
            "timestamp": self._isoformat_from_ts(item.created_at),
            "extra": self._safe_value(item.extra),
        }

    def _serialize_function_output(self, item: FunctionCallOutput) -> dict[str, Any]:
        return {
            "id": item.id,
            "type": item.type,
            "call_id": item.call_id,
            "name": item.name,
            "output": item.output,
            "is_error": item.is_error,
            "created_at": item.created_at,
            "timestamp": self._isoformat_from_ts(item.created_at),
        }

    def _serialize_error(self, error: Any) -> dict[str, Any] | None:
        if error is None:
            return None

        if hasattr(error, "model_dump"):
            return self._safe_model_dump(error)

        return {
            "type": error.__class__.__name__,
            "message": str(error),
        }

    def _safe_model_dump(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}

        if hasattr(value, "model_dump"):
            return self._safe_value(value.model_dump())

        return {"value": self._safe_value(value)}

    def _safe_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): self._safe_value(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._safe_value(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if hasattr(value, "value"):
            try:
                return value.value
            except Exception:
                return str(value)
        if hasattr(value, "model_dump"):
            return self._safe_value(value.model_dump())
        return str(value)

    def _build_session_id(self) -> str:
        now = self._now()
        return f"session_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _now(self) -> datetime:
        return datetime.now(self._tzinfo)

    def _isoformat(self, dt: datetime) -> str:
        return dt.isoformat(timespec="seconds")

    def _isoformat_from_ts(self, timestamp: float | None) -> str | None:
        if timestamp is None:
            return None
        dt = datetime.fromtimestamp(timestamp, tz=self._tzinfo)
        return self._isoformat(dt)
