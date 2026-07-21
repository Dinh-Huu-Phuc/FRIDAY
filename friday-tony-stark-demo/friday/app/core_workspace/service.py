from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .schemas import (
    WorkspaceBlockedRule,
    WorkspaceFileSummary,
    WorkspaceIndexResponse,
    WorkspaceReadResponse,
    WorkspaceSearchMatch,
    WorkspaceSearchResponse,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
FRIDAY_DIR = ROOT_DIR / "friday"

ALLOWED_ROOTS = (
    "friday/app",
    "friday/core",
    "friday/docs",
    "friday/language",
    "friday/messages",
    "friday/news",
    "friday/prompts",
    "friday/resources",
    "friday/src",
    "friday/tools",
)

BLOCKED_PATH_PATTERNS = (
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "*.dump",
    "*.bak",
    "*.backup",
    "*.log",
    "*.pyc",
    "__pycache__/*",
    "*/__pycache__/*",
    "friday/app/.env",
    "friday/app/.env.*",
    "friday/googleServiceCloud/*",
    "friday/log/*",
    "friday/trainModel/*",
    "*/node_modules/*",
    "*/.git/*",
    "*/.venv/*",
    "*/venv/*",
)

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".txt",
    ".ts",
    ".tsx",
    ".yml",
    ".yaml",
}

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password|credential)(\s*[:=]\s*)([^\s\"']+)"),
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
)


def _to_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def _is_under_allowed_root(path: Path) -> bool:
    try:
        relative = _to_relative(path)
    except ValueError:
        return False

    return any(relative == root or relative.startswith(f"{root}/") for root in ALLOWED_ROOTS)


def _block_reason(path: Path) -> str | None:
    try:
        relative = _to_relative(path)
    except ValueError:
        return "Path is outside the FRIDAY workspace."

    if not _is_under_allowed_root(path):
        return "Path is outside the Core AI allowlist."

    for pattern in BLOCKED_PATH_PATTERNS:
        if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern):
            return f"Blocked by sensitive-data rule: {pattern}"

    if path.suffix and path.suffix.lower() not in TEXT_EXTENSIONS:
        return "Only source, documentation, and structured text files are readable."

    return None


def _iter_safe_files() -> list[Path]:
    files: list[Path] = []

    for allowed_root in ALLOWED_ROOTS:
        root = ROOT_DIR / allowed_root
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if _block_reason(path) is not None:
                continue
            files.append(path)

    return sorted(files, key=lambda item: _to_relative(item))


def _classify_file(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "text"


def _redact_secrets(content: str) -> str:
    redacted = content
    redacted = SECRET_PATTERNS[0].sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted)
    for pattern in SECRET_PATTERNS[1:]:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def index_workspace(max_files: int = 240) -> WorkspaceIndexResponse:
    files = _iter_safe_files()
    selected = files[:max_files]
    return WorkspaceIndexResponse(
        root=ROOT_DIR.as_posix(),
        allowed_roots=list(ALLOWED_ROOTS),
        blocked_rules=[
            WorkspaceBlockedRule(rule=rule, reason="Sensitive, generated, binary, credential, or private runtime data.")
            for rule in BLOCKED_PATH_PATTERNS
        ],
        files=[
            WorkspaceFileSummary(
                path=_to_relative(path),
                size_bytes=path.stat().st_size,
                kind=_classify_file(path),
            )
            for path in selected
        ],
        truncated=len(files) > len(selected),
    )


def read_workspace_file(path: str, max_chars: int = 12000) -> WorkspaceReadResponse:
    candidate = (ROOT_DIR / path).resolve()
    reason = _block_reason(candidate)
    relative = path.replace("\\", "/")

    if reason:
        return WorkspaceReadResponse(ok=False, path=relative, blocked=True, reason=reason)

    if not candidate.exists() or not candidate.is_file():
        return WorkspaceReadResponse(ok=False, path=relative, reason="File does not exist.")

    try:
        content = candidate.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return WorkspaceReadResponse(ok=False, path=relative, reason=str(exc))

    content = _redact_secrets(content)
    truncated = len(content) > max_chars
    return WorkspaceReadResponse(
        ok=True,
        path=_to_relative(candidate),
        content=content[:max_chars],
        truncated=truncated,
    )


def search_workspace(query: str, max_results: int = 12, max_chars_per_match: int = 420) -> WorkspaceSearchResponse:
    normalized_query = " ".join(query.lower().split())
    if not normalized_query:
        return WorkspaceSearchResponse(query=query, matches=[])

    terms = [term for term in re.split(r"[^a-zA-Z0-9_./-]+", normalized_query) if len(term) >= 2]
    matches: list[WorkspaceSearchMatch] = []

    for path in _iter_safe_files():
        if len(matches) >= max_results:
            break

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for line_number, line in enumerate(lines, start=1):
            line_normalized = line.lower()
            if not any(term in line_normalized for term in terms):
                continue

            snippet = _redact_secrets(line.strip())
            if len(snippet) > max_chars_per_match:
                snippet = f"{snippet[:max_chars_per_match].rstrip()}..."

            matches.append(
                WorkspaceSearchMatch(
                    path=_to_relative(path),
                    line=line_number,
                    snippet=snippet,
                )
            )

            if len(matches) >= max_results:
                break

    return WorkspaceSearchResponse(
        query=query,
        matches=matches,
        truncated=len(matches) >= max_results,
    )


def build_workspace_context(message: str, max_chars: int = 3500) -> str:
    index = index_workspace(max_files=80)
    search = search_workspace(message, max_results=8, max_chars_per_match=320)

    lines = [
        "Safe FRIDAY workspace context for this answer.",
        "Security: .env, keys, credentials, logs, dumps, trainModel data, google service-account files, databases, and binaries are blocked by allowlist rules.",
        f"Allowed roots: {', '.join(index.allowed_roots)}",
        "Visible files:",
    ]

    for file in index.files[:26]:
        lines.append(f"- {file.path} ({file.kind}, {file.size_bytes} bytes)")

    if search.matches:
        lines.append("Relevant search matches:")
        for match in search.matches:
            lines.append(f"- {match.path}:{match.line}: {match.snippet}")

    context = "\n".join(lines)
    if len(context) > max_chars:
        return f"{context[:max_chars].rstrip()}\n[workspace context truncated]"
    return context
