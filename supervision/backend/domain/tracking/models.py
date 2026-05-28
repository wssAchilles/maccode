from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Track:
    tracker_id: int
    class_id: int
    class_name: str
    confidence: float
    xyxy: list[float]
    first_seen_frame: int
    last_seen_frame: int
    speed_kmh: float | None = None
    speed_uncertainty_kmh: float | None = None
    speed_confidence: float | None = None
    speed_confidence_interval_kmh: list[float] | None = None
    position_rmse_m: float | None = None
    ground_x_m: float | None = None
    ground_y_m: float | None = None
    velocity_x_mps: float | None = None
    velocity_y_mps: float | None = None
    heading_deg: float | None = None
    acceleration_mps2: float | None = None

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)

    def with_detection(self, xyxy: list[float], confidence: float, frame_index: int) -> Track:
        return replace(
            self,
            xyxy=list(xyxy),
            confidence=confidence,
            last_seen_frame=frame_index,
        )

    def with_speed(
        self,
        speed_kmh: float | None,
        speed_uncertainty_kmh: float | None = None,
        speed_confidence: float | None = None,
        speed_confidence_interval_kmh: list[float] | None = None,
        position_rmse_m: float | None = None,
        ground_x_m: float | None = None,
        ground_y_m: float | None = None,
        velocity_x_mps: float | None = None,
        velocity_y_mps: float | None = None,
        heading_deg: float | None = None,
        acceleration_mps2: float | None = None,
    ) -> Track:
        return replace(
            self,
            speed_kmh=speed_kmh,
            speed_uncertainty_kmh=speed_uncertainty_kmh,
            speed_confidence=speed_confidence,
            speed_confidence_interval_kmh=speed_confidence_interval_kmh,
            position_rmse_m=position_rmse_m,
            ground_x_m=ground_x_m,
            ground_y_m=ground_y_m,
            velocity_x_mps=velocity_x_mps,
            velocity_y_mps=velocity_y_mps,
            heading_deg=heading_deg,
            acceleration_mps2=acceleration_mps2,
        )
