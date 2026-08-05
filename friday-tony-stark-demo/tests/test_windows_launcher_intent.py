from unittest.mock import patch

from friday.app.windows_launcher import extract_windows_app_query
from friday.app.windows_launcher.registry import _discover_system_executables


def test_extracts_explicit_windows_application_commands() -> None:
    assert (
        extract_windows_app_query("FRIDAY, launch Visual Studio Code.")
        == "Visual Studio Code"
    )
    assert extract_windows_app_query("Open Chrome.") == "Chrome"
    assert extract_windows_app_query("Start Notepad for me.") == "Notepad"
    assert extract_windows_app_query("Run Calculator now.") == "Calculator"


def test_rejects_commands_owned_by_other_agent_routes() -> None:
    assert extract_windows_app_query("FRIDAY, open code map.") is None
    assert extract_windows_app_query("FRIDAY, open Neural Network.") is None
    assert extract_windows_app_query("FRIDAY, run a cycle.") is None
    assert (
        extract_windows_app_query(
            "FRIDAY, open a new Chrome tab and search current news."
        )
        is None
    )
    assert extract_windows_app_query("FRIDAY, open the browser.") is None
    assert extract_windows_app_query("FRIDAY, open browser settings.") is None
    assert extract_windows_app_query("FRIDAY, open YouTube and search Iron Man.") is None
    assert extract_windows_app_query("FRIDAY, open Binance Bitcoin market.") is None


def test_discovers_standard_windows_executables() -> None:
    with patch(
        "friday.app.windows_launcher.registry.shutil.which",
        side_effect=lambda executable: f"C:/Windows/{executable}",
    ):
        apps = _discover_system_executables()

    assert {app.name for app in apps} >= {
        "Calculator",
        "Command Prompt",
        "File Explorer",
        "Notepad",
        "Task Manager",
    }
    assert all(app.source == "windows_system" for app in apps)
