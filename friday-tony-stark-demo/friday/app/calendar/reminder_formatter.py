from __future__ import annotations

from friday.app.calendar.schemas import CalendarEntry


def _sentence(value: str) -> str:
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return ""
    return normalized if normalized[-1] in ".!?" else f"{normalized}."


def format_calendar_reminder(
    entry: CalendarEntry,
    *,
    maximum_length: int = 260,
) -> str:
    hour = entry.start_time.strftime("%I").lstrip("0") or "12"
    clock = f"{hour}:{entry.start_time:%M} {entry.start_time:%p}"
    prefix = f"Boss, it is {clock}. {_sentence(entry.title)}"
    detail = _sentence(entry.details[0]) if entry.details else ""
    message = " ".join(part for part in (prefix, detail) if part).strip()
    if len(message) <= maximum_length:
        return message
    shortened = message[: max(1, maximum_length - 1)].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{shortened}."
