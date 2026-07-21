"""Computer control feature module for FRIDAY."""

from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.dependencies import get_computer_service, get_computer_settings
from friday.app.computer.service.service import ComputerService
from friday.app.computer.service.screen_understanding import (
    is_screen_understanding_request,
    understand_current_screen,
    wants_all_screens,
)

__all__ = [
    "ComputerService",
    "ComputerSettings",
    "get_computer_service",
    "get_computer_settings",
    "is_screen_understanding_request",
    "understand_current_screen",
    "wants_all_screens",
]
