from __future__ import annotations

from typing import Any


def _as_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def build_matching_submission_payload(
    *,
    strategy_id: str,
    account_id: str,
    order_event: dict[str, Any],
) -> dict[str, Any]:
    accepted = bool(order_event.get("accepted", False))
    order_id = _as_text(order_event.get("order_id")) or ""
    symbol = _as_text(order_event.get("symbol")) or ""
    signal_side = _as_text(order_event.get("signal"))
    request_id = _as_text(order_event.get("request_id"))
    reason = _as_text(order_event.get("reason"))

    return {
        "event": "matching.order.submitted",
        "provider": "matching",
        "strategy_id": strategy_id,
        "account_id": account_id,
        "order_id": order_id,
        "symbol": symbol,
        "side": signal_side,
        "status": "submitted" if accepted else "rejected",
        "accepted": accepted,
        "reason": reason or "",
        "request_id": request_id,
    }


def build_matching_execution_payload(
    *,
    account_id: str,
    execution: dict[str, Any],
) -> dict[str, Any]:
    execution_id = _as_text(execution.get("execution_id")) or ""
    order_id = _as_text(execution.get("order_id")) or ""
    symbol = _as_text(execution.get("symbol")) or ""
    request_id = _as_text(execution.get("request_id"))

    return {
        "event": "matching.execution.filled",
        "provider": "matching",
        "account_id": account_id,
        "execution_id": execution_id,
        "order_id": order_id,
        "symbol": symbol,
        "status": "filled",
        "price": execution.get("price"),
        "quantity": execution.get("quantity"),
        "event_time": execution.get("event_time"),
        "request_id": request_id,
    }
