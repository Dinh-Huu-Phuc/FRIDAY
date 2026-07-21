from __future__ import annotations

from friday.about import get_friday_self_intro


def register(mcp):
    @mcp.tool()
    async def get_friday_about_response(response_type: str = "voice") -> str:
        """
        Return the prepared FRIDAY self-introduction from friday/about/messages.
        Use response_type='voice' for speech, 'short' for quick replies, or 'full' for detail.
        """

        return get_friday_self_intro(response_type=response_type)
