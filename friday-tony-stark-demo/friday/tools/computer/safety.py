"""Safety checks for local shell execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re


DESTRUCTIVE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\brm\s+-rf\b", "Recursive deletion is blocked."),
    (r"\bdel\s+/f\b", "Forced deletion is blocked."),
    (r"\bformat\s+[a-z]:", "Formatting a drive is blocked."),
    (r"\bshutdown\b", "Shutdown commands are blocked."),
    (r"\brestart-computer\b", "Restart commands are blocked."),
)
HIGH_RISK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bremove-item\b", "File removal commands are high risk."),
    (r"\brmdir\b", "Directory removal commands are high risk."),
    (r"\btaskkill\b", "Killing processes is high risk."),
    (r"\bsc\s+stop\b", "Stopping services is high risk."),
    (r"\breg\s+add\b", "Registry edits are high risk."),
)
MEDIUM_RISK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(curl|wget|invoke-webrequest|iwr)\b", "Downloading remote content needs review."),
    (r"\b(pip|uv)\s+(install|sync)\b", "Installing dependencies changes the environment."),
    (r"\bgit\s+(pull|push|merge|rebase)\b", "Repository mutation commands need review."),
)
LOW_RISK_PREFIXES: tuple[str, ...] = (
    "dir",
    "echo",
    "get-childitem",
    "get-content",
    "git status",
    "ls",
    "pwd",
    "type",
    "where",
    "whoami",
)


@dataclass(slots=True, frozen=True)
class CommandSafetyResult:
    allowed: bool
    risk_level: str
    reason: str

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def validate_command(command: str, safety_mode: str = "strict") -> CommandSafetyResult:
    normalized = " ".join(str(command or "").strip().lower().split())
    mode = str(safety_mode or "strict").strip().lower() or "strict"
    if not normalized:
        return CommandSafetyResult(
            allowed=False,
            risk_level="medium",
            reason="Shell command is empty.",
        )

    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, normalized):
            return CommandSafetyResult(allowed=False, risk_level="critical", reason=reason)

    for pattern, reason in HIGH_RISK_PATTERNS:
        if re.search(pattern, normalized):
            return CommandSafetyResult(
                allowed=mode == "off",
                risk_level="high",
                reason=reason,
            )

    for pattern, reason in MEDIUM_RISK_PATTERNS:
        if re.search(pattern, normalized):
            return CommandSafetyResult(
                allowed=mode in {"moderate", "off"},
                risk_level="medium",
                reason=reason,
            )

    if normalized.startswith(LOW_RISK_PREFIXES):
        return CommandSafetyResult(
            allowed=True,
            risk_level="low",
            reason="Command matched the low-risk allowlist.",
        )

    return CommandSafetyResult(
        allowed=mode in {"moderate", "off"},
        risk_level="medium",
        reason="Command is not on the low-risk allowlist.",
    )
