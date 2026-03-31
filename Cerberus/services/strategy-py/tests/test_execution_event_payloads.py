from app.execution_event_payloads import (
    build_matching_execution_payload,
    build_matching_submission_payload,
)


def test_build_matching_submission_payload_sets_status_and_ids() -> None:
    payload = build_matching_submission_payload(
        strategy_id="default",
        account_id="acc-1",
        order_event={
            "accepted": True,
            "order_id": "ord-1",
            "client_order_id": "cid-1",
            "symbol": "BTCUSDT",
            "signal": "BUY",
            "price": 100.25,
            "quantity": 0.4,
            "reason": "",
            "request_id": "rid-1",
        },
    )

    assert payload["event"] == "matching.order.submitted"
    assert payload["provider"] == "matching"
    assert payload["strategy_id"] == "default"
    assert payload["account_id"] == "acc-1"
    assert payload["order_id"] == "ord-1"
    assert payload["client_order_id"] == "cid-1"
    assert payload["symbol"] == "BTCUSDT"
    assert payload["side"] == "BUY"
    assert payload["status"] == "accepted"
    assert payload["accepted"] is True
    assert payload["price"] == 100.25
    assert payload["quantity"] == 0.4
    assert payload["request_id"] == "rid-1"


def test_build_matching_submission_payload_rejected_defaults() -> None:
    payload = build_matching_submission_payload(
        strategy_id="default",
        account_id="acc-1",
        order_event={
            "accepted": False,
            "reason": "insufficient liquidity",
        },
    )

    assert payload["status"] == "rejected"
    assert payload["order_id"] == ""
    assert payload["client_order_id"] == ""
    assert payload["symbol"] == ""
    assert payload["request_id"] is None
    assert payload["reason"] == "insufficient liquidity"


def test_build_matching_execution_payload_shape() -> None:
    payload = build_matching_execution_payload(
        account_id="acc-1",
        execution={
            "execution_id": "101",
            "order_id": "ord-1",
            "symbol": "BTCUSDT",
            "price": 100.5,
            "quantity": 0.2,
            "event_time": "2026-03-25T12:00:00+00:00",
            "request_id": "rid-exec-1",
        },
    )

    assert payload["event"] == "matching.execution.filled"
    assert payload["provider"] == "matching"
    assert payload["account_id"] == "acc-1"
    assert payload["execution_id"] == "101"
    assert payload["order_id"] == "ord-1"
    assert payload["symbol"] == "BTCUSDT"
    assert payload["status"] == "filled"
    assert payload["request_id"] == "rid-exec-1"
