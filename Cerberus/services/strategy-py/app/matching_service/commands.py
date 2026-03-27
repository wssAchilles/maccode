from __future__ import annotations

from app.api.matching_helpers import ensure_matching_enabled
from app.config import settings
from app.ports import MatchingGatewayPort
from app.schemas import (
    MatchingCancelRequest,
    MatchingCancelResponse,
    MatchingSubmitRequest,
    MatchingSubmitResponse,
)

from .mapping import to_cancel_response, to_submit_response


async def submit_order(
    gateway: MatchingGatewayPort,
    payload: MatchingSubmitRequest,
    *,
    request_id: str,
    idempotency_key: str | None,
) -> MatchingSubmitResponse:
    ensure_matching_enabled(gateway)
    account_id = payload.account_id or settings.strategy_account_id
    result = await gateway.submit_limit_order(
        account_id=account_id,
        symbol=payload.symbol,
        side=payload.side,
        price=payload.price,
        quantity=payload.quantity,
        client_order_id=payload.client_order_id or "",
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    return to_submit_response(result, request_id=request_id)


async def cancel_order(
    gateway: MatchingGatewayPort,
    *,
    order_id: str,
    payload: MatchingCancelRequest,
    request_id: str,
) -> MatchingCancelResponse:
    ensure_matching_enabled(gateway)
    account_id = payload.account_id or settings.strategy_account_id
    result = await gateway.cancel_order(
        account_id=account_id,
        order_id=order_id,
        request_id=request_id,
    )
    return to_cancel_response(result, request_id=request_id)


__all__ = ["submit_order", "cancel_order"]
