from __future__ import annotations

from dataclasses import dataclass

Point = list[float]


@dataclass(frozen=True)
class ZoneConfig:
    name: str
    line_start: Point
    line_end: Point

    def __post_init__(self) -> None:
        if len(self.line_start) != 2 or len(self.line_end) != 2:
            raise ValueError("line_start and line_end must be [x, y]")
        if self.line_start == self.line_end:
            raise ValueError("zone line must have non-zero length")


@dataclass(frozen=True)
class ZoneStats:
    name: str
    in_count: int = 0
    out_count: int = 0
