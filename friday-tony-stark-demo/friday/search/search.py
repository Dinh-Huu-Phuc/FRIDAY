"""
Google web search helper powered by Gemini + Google Search grounding.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from google import genai
from google.genai import types
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)


def _extract_sources(response: types.GenerateContentResponse, limit: int = 5) -> List[Tuple[str, str]]:
    """Extract grounded web sources from a Gemini response."""
    data = response.to_json_dict()
    candidates = data.get("candidates", [])
    if not candidates:
        return []

    grounding = candidates[0].get("groundingMetadata", {})
    chunks = grounding.get("groundingChunks", [])

    sources: List[Tuple[str, str]] = []
    seen_urls = set()
    for chunk in chunks:
        web = chunk.get("web", {})
        title = (web.get("title") or "").strip()
        url = (web.get("uri") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append((title or "Reference source", url))
        if len(sources) >= limit:
            break
    return sources


def _format_search_error(exc: Exception) -> str:
    """Convert provider and network errors into concise diagnostics."""
    message = " ".join(str(part).strip() for part in exc.args if str(part).strip()) or str(exc).strip()
    lower = message.lower()

    if (
        "10013" in lower
        or "forbidden by its access permissions" in lower
        or "socket" in lower and "forbidden" in lower
    ):
        return (
            "Web search is blocked from making outbound connections. Check Windows Firewall, "
            "antivirus, proxy/VPN settings, and Python or uv network permissions."
        )

    if (
        "timed out" in lower
        or "timeout" in lower
        or "deadline exceeded" in lower
    ):
        return "Web search timed out because the outbound connection is too slow."

    if (
        "getaddrinfo failed" in lower
        or "name or service not known" in lower
        or "temporary failure in name resolution" in lower
        or "nodename nor servname provided" in lower
    ):
        return "Web search is unavailable because DNS resolution or internet access failed."

    if (
        "api key" in lower
        or "unauthenticated" in lower
        or "permission_denied" in lower
        or "permission denied" in lower
        or "401" in lower
        or "403" in lower
    ):
        return "Web search failed because the API key or Google Search permission is invalid."

    return f"Web search is unavailable right now: {message}"


def google_web_search(query: str, max_sources: int = 5) -> str:
    """
    Search the web with Gemini Google Search grounding and return a concise report.
    Requires GOOGLE_API_KEY in .env.
    """
    query = (query or "").strip()
    if not query:
        return "No search query was provided."

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return "GOOGLE_API_KEY is missing from .env, so web search is unavailable."

    model = os.getenv("GOOGLE_SEARCH_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
    client = genai.Client(api_key=api_key)

    prompt = (
        "You are a careful web research assistant. Reply in concise, honest English and state "
        "when information is unknown. Summarize the following query in four to eight sentences.\n\n"
        f"Query: {query}"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception as exc:
        return _format_search_error(exc)

    summary = (response.text or "").strip()
    if not summary:
        summary = "The search completed, but no clear summary could be extracted."

    sources = _extract_sources(response, limit=max_sources)
    if not sources:
        return summary

    lines = [summary, "", "### Sources:"]
    for idx, (title, url) in enumerate(sources, 1):
        lines.append(f"{idx}. {title} - {url}")
    return "\n".join(lines)
