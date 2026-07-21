from __future__ import annotations

import re


def build_gmail_runtime_hint(*, command: str, report: str) -> str:
    compact_report = re.sub(r"\s+", " ", report).strip()
    if len(compact_report) > 2200:
        compact_report = f"{compact_report[:2200].rstrip()}..."
    return (
        "[GMAIL_CONTEXT]\n"
        f"command={command}\n"
        f"assistant_reply={compact_report}\n"
        "The read-only Gmail check has already completed.\n"
        "Reply with exactly assistant_reply in English.\n"
        "Do not call more tools or reveal implementation details."
    )


def build_windows_launcher_runtime_hint(*, command: str, app_query: str, result: dict) -> str:
    ok = bool(result.get("ok"))
    message = str(result.get("message") or "").strip()
    selected = result.get("selected") if isinstance(result.get("selected"), dict) else None
    selected_name = str((selected or {}).get("name") or app_query or "application").strip()
    assistant_reply = f"Opened {selected_name}, boss." if ok else message or f"I could not open {app_query}, boss."
    return (
        "[WINDOWS_LAUNCHER_CONTEXT]\n"
        f"command={command}\napp_query={app_query}\ntool_ok={ok}\n"
        f"tool_message={message}\nassistant_reply={assistant_reply}\n"
        "The Windows launcher action has already completed.\n"
        "Reply with exactly assistant_reply. Do not claim success unless tool_ok=true.\n"
        "Do not call more tools for this turn."
    )
