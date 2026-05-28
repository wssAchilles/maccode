from __future__ import annotations

from fastapi import APIRouter

from domain.zones.models import ZoneConfig
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=ResponseWrapper[list[ZoneConfig]])
def get_zones() -> ResponseWrapper[list[ZoneConfig]]:
    return ResponseWrapper.success_response([ZoneConfig("main_gate", [0, 10], [80, 10])])
