"""
System tools — time, environment info, shell commands, etc.
"""

import datetime
import platform

from friday.runtime_context import build_runtime_context_snapshot


def register(mcp):

    @mcp.tool()
    def get_current_time() -> str:
        """Return the current date and time in ISO 8601 format."""
        return datetime.datetime.now().isoformat()

    @mcp.tool()
    def get_system_info() -> dict:
        """Return basic information about the host system."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        }

    @mcp.tool()
    def get_work_context() -> dict:
        """Return FRIDAY's current device and effective location context."""
        snapshot = build_runtime_context_snapshot()
        snapshot["current_time"] = datetime.datetime.now().isoformat()
        return snapshot
