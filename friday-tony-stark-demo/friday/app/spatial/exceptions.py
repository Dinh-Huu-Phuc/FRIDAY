class SpatialError(Exception):
    """Base exception for spatial engine failures."""


class CameraUnavailableError(SpatialError):
    """Raised when the webcam cannot be opened."""


class VisionDependencyError(SpatialError):
    """Raised when optional vision dependencies are not installed."""
