"""MCP tools for finding and opening Windows apps."""

from __future__ import annotations

from friday.app.windows_launcher.service import open_app, search_apps


def register(mcp):
    @mcp.tool()
    def search_windows_apps(query: str, limit: int = 8) -> dict:
        """Search installed Windows apps by name, similar to the Start menu search."""
        response = search_apps(query=query, limit=limit)
        return response.model_dump(mode="json")

    @mcp.tool()
    def open_windows_app(query: str, min_score: float = 0.55) -> dict:
        """Open the best matching Windows app by name."""
        response = open_app(query=query, min_score=min_score)
        return response.model_dump(mode="json")
