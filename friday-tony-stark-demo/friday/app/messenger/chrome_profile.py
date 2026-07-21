from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


_PROFILE_DIRECTORY_PATTERN = re.compile(r"(?:Default|Profile \d+)")
_MESSENGER_URL = "https://www.messenger.com/"


class ChromeProfileLaunchError(RuntimeError):
    pass


class ChromeProfileLauncher:
    def __init__(
        self,
        *,
        profile_directory: str | None = None,
        chrome_path: Path | None = None,
    ) -> None:
        self.profile_directory = (
            profile_directory
            or os.getenv("FRIDAY_CHROME_PROFILE_DIRECTORY", "Default")
        ).strip()
        self.chrome_path = chrome_path or find_chrome_executable()

    def open_messenger(self) -> None:
        if not _PROFILE_DIRECTORY_PATTERN.fullmatch(self.profile_directory):
            raise ChromeProfileLaunchError(
                "FRIDAY_CHROME_PROFILE_DIRECTORY must be Default or Profile followed by a number."
            )
        if self.chrome_path is None:
            raise ChromeProfileLaunchError("Google Chrome could not be found on this machine.")
        try:
            subprocess.Popen(
                [
                    str(self.chrome_path),
                    f"--profile-directory={self.profile_directory}",
                    _MESSENGER_URL,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise ChromeProfileLaunchError(
                f"Chrome profile {self.profile_directory} could not be opened."
            ) from exc


def find_chrome_executable() -> Path | None:
    configured = os.getenv("FRIDAY_BROWSER_PATH", "").strip()
    candidates = [Path(configured)] if configured else []
    discovered = shutil.which("chrome.exe") or shutil.which("chrome")
    if discovered:
        candidates.append(Path(discovered))
    for env_name in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.getenv(env_name)
        if root:
            candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    return next((candidate for candidate in candidates if candidate.is_file()), None)
