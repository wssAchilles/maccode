from __future__ import annotations

import grpc

from app.api.matching_helpers import ensure_matching_enabled
from app.ports import MatchingGatewayPort
from app.schemas import MatchingHealthView, MatchingStatsView

from .fallbacks import build_degraded_stats


async def health(gateway: MatchingGatewayPort, *, request_id: str) -> MatchingHealthView:
    ensure_matching_enabled(gateway)
    return await gateway.health(request_id=request_id)


async def stats(gateway: MatchingGatewayPort, *, request_id: str) -> MatchingStatsView:
    ensure_matching_enabled(gateway)
    try:
        return await gateway.get_service_stats(request_id=request_id)
    except grpc.aio.AioRpcError as exc:
        return build_degraded_stats(
            request_id=request_id,
            reason=f"{exc.code().name}: {exc.details()}",
        )
    except Exception as exc:
        return build_degraded_stats(
            request_id=request_id,
            reason=f"matching stats error: {exc}",
        )


__all__ = ["health", "stats"]
