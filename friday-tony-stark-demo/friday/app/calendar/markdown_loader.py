from __future__ import annotations

import re
from datetime import time
from pathlib import Path

from friday.app.calendar.schemas import CalendarEntry

_SECTION_PATTERN = re.compile(r"^#\s+(Monday to Friday|Saturday|Sunday)\b", re.IGNORECASE)
_TIME_HEADING_PATTERN = re.compile(
    r"^##\s+"
    r"(?P<start>\d{2}:\d{2})"
    r"(?:-(?P<end>\d{2}:\d{2}))?"
    r"\s+-\s+(?P<title>.+?)\s*$"
)
_BULLET_PATTERN = re.compile(r"^\s*-\s+(?P<text>.+?)\s*$")
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_MARKERS = re.compile(r"[*_`~]+")
_NON_SLUG = re.compile(r"[^a-z0-9]+")

_SECTIONS: dict[str, tuple[str, tuple[int, ...]]] = {
    "monday to friday": ("workdays", (0, 1, 2, 3, 4)),
    "saturday": ("saturday", (5,)),
    "sunday": ("sunday", (6,)),
}


class CalendarMarkdownError(ValueError):
    pass


def _parse_time(value: str, *, line_number: int) -> time:
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
        return time(hour=hour, minute=minute)
    except (TypeError, ValueError) as exc:
        raise CalendarMarkdownError(
            f"Invalid calendar time {value!r} on line {line_number}."
        ) from exc


def _plain_text(value: str) -> str:
    linked = _LINK_PATTERN.sub(r"\1", value)
    without_markers = _MARKDOWN_MARKERS.sub("", linked)
    return " ".join(without_markers.split()).strip()


def _slug(value: str) -> str:
    normalized = _NON_SLUG.sub("-", value.lower()).strip("-")
    return normalized or "reminder"


def parse_calendar_markdown(markdown: str) -> tuple[CalendarEntry, ...]:
    entries: list[CalendarEntry] = []
    current_scope = ""
    current_weekdays: tuple[int, ...] = ()
    pending: dict[str, object] | None = None

    def finish_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        title = str(pending["title"])
        start_time = pending["start_time"]
        if not isinstance(start_time, time):
            raise CalendarMarkdownError("Calendar entry has no valid start time.")
        entry_id = (
            f"{pending['scope']}:{start_time.isoformat(timespec='minutes')}:"
            f"{_slug(title)}"
        )
        entries.append(
            CalendarEntry(
                entry_id=entry_id,
                scope=str(pending["scope"]),
                weekdays=tuple(pending["weekdays"]),
                start_time=start_time,
                end_time=(
                    pending["end_time"]
                    if isinstance(pending.get("end_time"), time)
                    else None
                ),
                title=title,
                details=tuple(pending["details"]),
                source_line=int(pending["source_line"]),
            )
        )
        pending = None

    for line_number, raw_line in enumerate(markdown.splitlines(), start=1):
        section_match = _SECTION_PATTERN.match(raw_line)
        if section_match:
            finish_pending()
            section_key = section_match.group(1).lower()
            current_scope, current_weekdays = _SECTIONS[section_key]
            continue

        if raw_line.startswith("# ") and not raw_line.startswith("## "):
            finish_pending()
            current_scope = ""
            current_weekdays = ()
            continue

        if raw_line.startswith("## "):
            finish_pending()
            if not current_scope:
                continue
            heading_match = _TIME_HEADING_PATTERN.match(raw_line)
            if heading_match is None:
                raise CalendarMarkdownError(
                    f"Expected a timed calendar heading on line {line_number}: "
                    f"{raw_line!r}"
                )
            pending = {
                "scope": current_scope,
                "weekdays": current_weekdays,
                "start_time": _parse_time(
                    heading_match.group("start"),
                    line_number=line_number,
                ),
                "end_time": (
                    _parse_time(
                        heading_match.group("end"),
                        line_number=line_number,
                    )
                    if heading_match.group("end")
                    else None
                ),
                "title": _plain_text(heading_match.group("title")),
                "details": [],
                "source_line": line_number,
            }
            continue

        bullet_match = _BULLET_PATTERN.match(raw_line)
        if pending is not None and bullet_match:
            detail = _plain_text(bullet_match.group("text"))
            if detail:
                pending["details"].append(detail)

    finish_pending()
    identifiers = [entry.entry_id for entry in entries]
    if len(identifiers) != len(set(identifiers)):
        raise CalendarMarkdownError("The calendar contains duplicate timed entries.")
    if not entries:
        raise CalendarMarkdownError("No timed calendar entries were found.")
    return tuple(entries)


def load_calendar_entries(path: Path) -> tuple[CalendarEntry, ...]:
    try:
        markdown = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalendarMarkdownError(f"Could not read calendar file: {path}") from exc
    return parse_calendar_markdown(markdown)
