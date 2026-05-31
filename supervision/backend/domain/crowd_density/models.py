from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrowdDensityInput:
    points_m: list[tuple[float, float]]
    region_name: str
    region_width_m: float
    region_length_m: float
    direct_detection_count: int
    trigger_threshold: int = 30
    cell_size_m: float = 1.0
    kernel_bandwidth_m: float = 1.5
    visible_area_sqm: float | None = None
    visible_area_source: str = "full_region_rect"


@dataclass(frozen=True)
class CrowdDensityResult:
    region_name: str
    people_count: int
    direct_detection_count: int
    integrated_people_count: float
    density_people_per_sqm: float
    peak_density_people_per_sqm: float
    estimation_method: str
    density_integral_triggered: bool
    crowding_level: str
    density_field: dict[str, float | int | str]
    unit: str = "person"
    model_reference: str = "Model 9 density field integral + Model 10 fallback policy"

    def to_dict(self) -> dict[str, object]:
        return {
            "region_name": self.region_name,
            "people_count": self.people_count,
            "direct_detection_count": self.direct_detection_count,
            "integrated_people_count": self.integrated_people_count,
            "density_people_per_sqm": self.density_people_per_sqm,
            "peak_density_people_per_sqm": self.peak_density_people_per_sqm,
            "unit": self.unit,
            "estimation_method": self.estimation_method,
            "density_integral_triggered": self.density_integral_triggered,
            "crowding_level": self.crowding_level,
            "density_field": self.density_field,
            "model_reference": self.model_reference,
        }
