from __future__ import annotations

from domain.zones.models import ZoneConfig
from fastapi import APIRouter, Request
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=ResponseWrapper[list[ZoneConfig]])
def get_zones(request: Request) -> ResponseWrapper[list[ZoneConfig]]:
    return ResponseWrapper.success_response(request.app.state.runtime.get_zones())


@router.put("/zones", response_model=ResponseWrapper[list[ZoneConfig]])
def update_zones(zones: list[ZoneConfig], request: Request) -> ResponseWrapper[list[ZoneConfig]]:
    return ResponseWrapper.success_response(request.app.state.runtime.update_zones(zones))
