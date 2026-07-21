from __future__ import annotations

from friday.gmail_system_agent import check_unread_gmail_with_timeout, format_gmail_report


def register(mcp):
    @mcp.tool()
    async def check_unread_gmail_messages(include_locally_reported: bool = False) -> str:
        """
        Check unread Gmail through the read-only Gmail API, save a local log,
        and report the important content. Use for inbox, unread mail, or email reports.
        """

        result = await check_unread_gmail_with_timeout(
            include_locally_reported=include_locally_reported,
        )
        return format_gmail_report(result)
