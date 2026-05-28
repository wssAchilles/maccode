from __future__ import annotations

from shared.configs.settings import Settings
from shared.exceptions.errors import CalibrationError, TrafficPerceptionError
from shared.schemas.common import ErrorDetail, ResponseWrapper


def test_settings_loads_defaults_without_environment() -> None:
    settings = Settings()

    assert settings.app.name == "TrafficPerceptionEngine"
    assert settings.app.port == 8000
    assert settings.cv.yolo_model == "yolo11n.pt"
    assert settings.llm.enabled is False


def test_response_wrapper_success_shape() -> None:
    response = ResponseWrapper.success_response({"task_id": "demo"})

    assert response.success is True
    assert response.data == {"task_id": "demo"}
    assert response.error is None


def test_response_wrapper_error_shape() -> None:
    response = ResponseWrapper.error_response(
        ErrorDetail(code="calibration.invalid", message="need at least 4 points")
    )

    assert response.success is False
    assert response.data is None
    assert response.error is not None
    assert response.error.code == "calibration.invalid"


def test_domain_errors_share_common_base_class() -> None:
    error = CalibrationError("bad calibration")

    assert isinstance(error, TrafficPerceptionError)
    assert str(error) == "bad calibration"
