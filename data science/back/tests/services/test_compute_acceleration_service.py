from services.compute_acceleration_service import ComputeAccelerationService


def test_runtime_component_status_recovers_after_recent_healthy_window():
    status = ComputeAccelerationService._runtime_component_status(
        component='feature_engineering',
        last_duration_ms=121.076,
        avg_duration_ms=418.478,
        p95_duration_ms=4399.951,
        recent_durations=[
            71.519,
            52.934,
            50.623,
            72.681,
            60.384,
            75.605,
            62.566,
            56.177,
            61.647,
            53.777,
            39.815,
            2999.938,
            72.773,
            4399.951,
            4499.934,
            2789.665,
            10.271,
            4.308,
            14.732,
            77.499,
            73.585,
            66.021,
            71.529,
            121.076,
        ],
        active_backend='python_pandas',
        native_enabled=False,
        native_available=False,
    )

    assert status == 'ok'


def test_runtime_component_status_flags_active_over_budget_window_as_error():
    status = ComputeAccelerationService._runtime_component_status(
        component='feature_engineering',
        last_duration_ms=430.0,
        avg_duration_ms=390.0,
        p95_duration_ms=410.0,
        recent_durations=[180.0, 420.0, 455.0, 430.0],
        active_backend='python_pandas',
        native_enabled=False,
        native_available=False,
    )

    assert status == 'error'
