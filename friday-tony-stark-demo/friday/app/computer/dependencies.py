"""Dependency factories for the computer package."""

from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.service.executor import ComputerExecutor
from friday.app.computer.service.observer import ComputerObserver
from friday.app.computer.service.planner import ComputerPlanner
from friday.app.computer.service.service import ComputerService


def get_computer_settings() -> ComputerSettings:
    return ComputerSettings.from_env()


def get_computer_observer(
    settings: ComputerSettings | None = None,
) -> ComputerObserver:
    return ComputerObserver(settings=settings or get_computer_settings())


def get_computer_planner(
    settings: ComputerSettings | None = None,
) -> ComputerPlanner:
    return ComputerPlanner(settings=settings or get_computer_settings())


def get_computer_executor(
    settings: ComputerSettings | None = None,
) -> ComputerExecutor:
    return ComputerExecutor(settings=settings or get_computer_settings())


def get_computer_service() -> ComputerService:
    settings = get_computer_settings()
    return ComputerService(
        settings=settings,
        observer=get_computer_observer(settings),
        planner=get_computer_planner(settings),
        executor=get_computer_executor(settings),
    )
