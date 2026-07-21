"""MCP tools for opening social websites through FRIDAY social modules."""

from friday.app import open_social_platform


def register(mcp):
    @mcp.tool()
    def open_social_platform_homepage(command: str) -> str:
        """Open the requested social platform homepage in a new browser tab."""
        return open_social_platform(command)
