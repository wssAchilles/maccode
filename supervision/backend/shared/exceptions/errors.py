class TrafficPerceptionError(Exception):
    """Base class for project-specific exceptions."""


class CVEngineError(TrafficPerceptionError):
    """Raised when the CV engine cannot complete a requested operation."""


class ModelLoadError(CVEngineError):
    """Raised when a detection model cannot be loaded."""


class InferenceError(CVEngineError):
    """Raised when model inference fails."""


class TrackingError(CVEngineError):
    """Raised when multi-object tracking fails."""


class CalibrationError(TrafficPerceptionError):
    """Raised when camera calibration data is invalid."""


class VideoError(TrafficPerceptionError):
    """Raised when video input or output fails."""


class ZoneError(TrafficPerceptionError):
    """Raised when a traffic zone configuration is invalid."""


class LLMError(TrafficPerceptionError):
    """Raised when LLM report generation fails."""
