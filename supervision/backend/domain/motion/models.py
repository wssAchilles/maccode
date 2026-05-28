from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MotionProfile:
    category: str
    process_noise: str
    should_track: bool
    should_estimate_speed: bool
    track_buffer: int
    matching_threshold: float
    context_role: str
    fallback_models: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
