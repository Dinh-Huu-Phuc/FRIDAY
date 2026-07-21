"""Custom exceptions for the computer module."""


class ComputerError(Exception):
    """Base exception for the computer module."""


class ComputerConfigurationError(ComputerError):
    """Raised when computer settings are invalid."""


class ComputerObservationError(ComputerError):
    """Raised when screen observation fails."""


class ComputerPlanningError(ComputerError):
    """Raised when the planner cannot produce a valid next action."""


class ComputerExecutionError(ComputerError):
    """Raised when executing a computer action fails."""


class ComputerSafetyError(ComputerError):
    """Raised when an action fails safety validation."""
