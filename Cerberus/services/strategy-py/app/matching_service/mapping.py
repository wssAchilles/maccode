from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from app.schemas import (
    MatchingCancelResponse,
    MatchingExecutionView,
    MatchingHealthView,
    MatchingOrderBookView,
    MatchingOrderView,
    MatchingStatsView,
    MatchingSubmitResponse,
)


def to_submit_response(
    result: Mapping[str, Any],
    *,
    request_id: str,
) -> MatchingSubmitResponse:
    return MatchingSubmitResponse(
        accepted=bool(result.get("accepted", False)),
        order_id=str(result.get("order_id", "")),
        reason=str(result.get("reason", "")),
        request_id=str(result.get("request_id") or request_id),
        schema_version=result.get("schema_version"),
        correlation_id=result.get("correlation_id"),
    )


def to_cancel_response(
    result: Mapping[str, Any],
    *,
    request_id: str,
) -> MatchingCancelResponse:
    return MatchingCancelResponse(
        canceled=bool(result.get("canceled", False)),
        reason=str(result.get("reason", "")),
        request_id=str(result.get("request_id") or request_id),
        schema_version=result.get("schema_version"),
        correlation_id=result.get("correlation_id"),
    )


def to_order_view(
    result: Mapping[str, Any],
    *,
    request_id: str | None = None,
) -> MatchingOrderView:
    payload = dict(result.items())
    if request_id and not payload.get("request_id"):
        payload["request_id"] = request_id
    payload["schema_version"] = payload.get("schema_version")
    payload["correlation_id"] = payload.get("correlation_id")
    return MatchingOrderView(**payload)


def to_execution_views(
    items: list[dict[str, Any]],
    *,
    request_id: str | None = None,
) -> list[MatchingExecutionView]:
    return [
        MatchingExecutionView(
            **{
                **item,
                "request_id": item.get("request_id") or request_id,
                "schema_version": item.get("schema_version"),
                "correlation_id": item.get("correlation_id"),
            }
        )
        for item in items
    ]


def to_health_view(
    payload: Mapping[str, Any],
    *,
    request_id: str | None = None,
) -> MatchingHealthView:
    normalized = dict(payload.items())
    if bool(normalized.get("reachable", False)):
        if request_id and not normalized.get("request_id"):
            normalized["request_id"] = request_id
        return MatchingHealthView(**normalized)

    reason = str(
        normalized.get("reason") or normalized.get("status") or "matching unavailable"
    )
    normalized["degraded"] = True
    normalized["reachable"] = False
    normalized["reason"] = reason
    if request_id and not normalized.get("request_id"):
        normalized["request_id"] = request_id
    return MatchingHealthView(**normalized)


def to_stats_view(payload: Mapping[str, Any]) -> MatchingStatsView:
    return MatchingStatsView(**dict(payload.items()))


def to_orderbook_view(
    payload: Mapping[str, Any],
    *,
    request_id: str | None = None,
) -> MatchingOrderBookView:
    normalized = dict(payload.items())
    if request_id and not normalized.get("request_id"):
        normalized["request_id"] = request_id
    return cast(MatchingOrderBookView, MatchingOrderBookView(**normalized))
