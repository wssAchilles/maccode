from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app
from app.schemas import SignalRecord


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "strategy-py"


def test_health_propagates_request_id_header() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={"x-request-id": "rid-health-001"})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "rid-health-001"


def test_ready_endpoint_shape() -> None:
    client = TestClient(app)
    response = client.get("/ready", headers={"x-request-id": "rid-ready-001"})
    assert response.status_code in (200, 503)
    assert response.headers.get("x-request-id") == "rid-ready-001"
    payload = response.json()
    assert "ready" in payload
    assert "worker" in payload
    assert "reasons" in payload


def test_optimize_validation() -> None:
    client = TestClient(app)
    payload = {
        "asset_names": ["A", "B"],
        "expected_returns": [0.1],
        "covariance": [[0.1, 0.0], [0.0, 0.1]],
        "risk_aversion": 1.0,
    }
    response = client.post("/api/v1/optimize/mean-variance", json=payload)
    assert response.status_code == 400


def test_recent_signals_endpoint() -> None:
    async def fake_list_recent(limit: int, source: str = "auto") -> tuple[str, list[SignalRecord]]:
        assert limit == 2
        assert source == "supabase"
        return (
            "supabase",
            [
                SignalRecord(
                    strategy_id="default",
                    symbol="BTCUSDT",
                    signal="BUY",
                    confidence=0.7,
                    created_at="2026-03-23T00:00:00Z",
                )
            ],
        )

    main_module.signal_store.list_recent = fake_list_recent  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.get("/api/v1/signals/recent?limit=2&source=supabase")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "supabase"
    assert payload["count"] == 1
    assert payload["signals"][0]["signal"] == "BUY"


def test_persistence_status_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/status/persistence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "worker" in payload
    assert "matching" in payload
    assert "stores" in payload


def test_matching_submit_returns_503_when_disabled() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/matching/orders",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 100.0,
            "quantity": 0.01,
        },
    )
    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "matching_disabled"
    assert payload["error"]["request_id"]


def test_matching_submit_endpoint_uses_client() -> None:
    async def fake_submit_limit_order(
        *,
        account_id: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        client_order_id: str = "",
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        assert account_id == "default"
        assert symbol == "BTCUSDT"
        assert side == "BUY"
        assert price == 100.0
        assert quantity == 0.01
        assert client_order_id == "cid-1"
        assert request_id
        assert idempotency_key is None
        return {
            "accepted": True,
            "order_id": "oid-1",
            "reason": "",
        }

    main_module.worker.matching_client._enabled = True  # type: ignore[attr-defined]
    main_module.worker.matching_client.submit_limit_order = fake_submit_limit_order  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.post(
        "/api/v1/matching/orders",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 100.0,
            "quantity": 0.01,
            "client_order_id": "cid-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["order_id"] == "oid-1"
    assert payload["request_id"]


def test_matching_health_endpoint_uses_client() -> None:
    async def fake_health(request_id: str | None = None) -> dict[str, object]:
        assert request_id
        return {
            "enabled": True,
            "reachable": True,
            "status": "ok",
            "service": "matching-cpp",
            "version": "0.1.0",
            "uptime_seconds": 120,
            "request_id": "rid-1",
        }

    main_module.worker.matching_client._enabled = True  # type: ignore[attr-defined]
    main_module.worker.matching_client.health = fake_health  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.get("/api/v1/matching/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "matching-cpp"


def test_matching_stats_endpoint_uses_client() -> None:
    async def fake_stats(request_id: str | None = None) -> dict[str, object]:
        assert request_id
        return {
            "enabled": True,
            "live_orders": 3,
            "trade_count": 7,
            "tracked_orders": 10,
            "rejected_orders": 1,
            "symbols": 2,
            "best_bid": 100.0,
            "best_ask": 101.0,
            "request_id": "rid-2",
        }

    main_module.worker.matching_client._enabled = True  # type: ignore[attr-defined]
    main_module.worker.matching_client.get_service_stats = fake_stats  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.get("/api/v1/matching/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["live_orders"] == 3
    assert payload["trade_count"] == 7


def test_metrics_endpoint_exposes_prometheus_format() -> None:
    main_module.worker.matching_client._enabled = False  # type: ignore[attr-defined]
    client = TestClient(app)
    response = client.get("/metrics", headers={"x-request-id": "rid-metrics-001"})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "rid-metrics-001"
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("text/plain")
    body = response.text
    assert "cerberus_strategy_up 1" in body
    assert "cerberus_strategy_build_info" in body
    assert "cerberus_strategy_processed_ticks_total" in body


def test_matching_orderbook_endpoint_uses_client() -> None:
    async def fake_orderbook(
        *, symbol: str, depth: int = 20, request_id: str | None = None
    ) -> dict[str, object]:
        assert symbol == "BTCUSDT"
        assert depth == 5
        assert request_id
        return {
            "enabled": True,
            "symbol": "BTCUSDT",
            "depth": 5,
            "bids": [{"price": 100.0, "total_quantity": 1.2, "order_count": 2}],
            "asks": [{"price": 100.5, "total_quantity": 0.8, "order_count": 1}],
            "generated_at_ms": 1700000000000,
            "request_id": "rid-orderbook",
        }

    main_module.worker.matching_client._enabled = True  # type: ignore[attr-defined]
    main_module.worker.matching_client.get_order_book = fake_orderbook  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.get("/api/v1/matching/orderbook?symbol=BTCUSDT&depth=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSDT"
    assert payload["depth"] == 5
    assert payload["bids"][0]["price"] == 100.0
    assert payload["asks"][0]["order_count"] == 1


def test_matching_executions_endpoint_filters_by_symbol_order_and_request_id() -> None:
    async def fake_executions(
        *, account_id: str, limit: int = 20, request_id: str | None = None
    ) -> list[dict[str, object]]:
        assert account_id == "acc-1"
        assert limit == 20
        assert request_id
        return [
            {
                "execution_id": "e1",
                "order_id": "o1",
                "account_id": "acc-1",
                "symbol": "BTCUSDT",
                "price": 100.0,
                "quantity": 1.0,
                "event_time": "2025-01-01T00:00:00+00:00",
                "request_id": "rid-e1",
            },
            {
                "execution_id": "e2",
                "order_id": "o2",
                "account_id": "acc-1",
                "symbol": "ETHUSDT",
                "price": 2000.0,
                "quantity": 2.0,
                "event_time": "2025-01-01T00:01:00+00:00",
                "request_id": "rid-e2",
            },
        ]

    main_module.worker.matching_client._enabled = True  # type: ignore[attr-defined]
    main_module.worker.matching_client.list_recent_executions = fake_executions  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.get(
        "/api/v1/matching/executions"
        "?account_id=acc-1&symbol=BTCUSDT&order_id=o1&request_id=rid-e1"
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["order_id"] == "o1"
    assert payload[0]["symbol"] == "BTCUSDT"
    assert payload[0]["account_id"] == "acc-1"
    assert payload[0]["request_id"] == "rid-e1"
