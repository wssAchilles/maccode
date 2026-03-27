from __future__ import annotations

import pytest

from app.market_ingest_runtime import stream_processing
from app.schemas import Signal, TickEvent


class FakeStreamWorker:
    def __init__(self) -> None:
        self.ingested_ticks: list[TickEvent] = []
        self.processed_stream_ids: list[str] = []
        self.last_error: str | None = None
        self.fail_on_ingest: Exception | None = None

    async def ingest_tick(self, tick: TickEvent) -> Signal:
        if self.fail_on_ingest is not None:
            raise self.fail_on_ingest
        self.ingested_ticks.append(tick)
        return Signal(
            strategy_id="default",
            symbol=tick.symbol,
            signal="BUY",
            confidence=0.9,
        )

    def mark_market_stream_event_processed(self, stream_id: str) -> None:
        self.processed_stream_ids.append(stream_id)

    def set_last_error(self, message: str) -> None:
        self.last_error = message


@pytest.mark.asyncio
async def test_process_market_stream_batch_acks_processed_and_invalid_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = FakeStreamWorker()
    ack_calls: list[list[str]] = []

    async def fake_ack(
        _worker: FakeStreamWorker,
        _stream_key: str,
        _group: str,
        ids: list[str],
    ) -> None:
        ack_calls.append(ids)

    monkeypatch.setattr(stream_processing, "ack_market_stream_entries", fake_ack)

    entries = [
        ("1-0", {"data": "not-json"}),
        (
            "2-0",
            {
                "data": '{"symbol":"BTCUSDT","price":100.0,"quantity":0.1,"event_time":"2026-03-27T12:00:00Z"}',
                "channel": "cerberus.market.BTCUSDT",
            },
        ),
    ]

    await stream_processing.process_market_stream_batch(
        worker,
        "cerberus.market.events",
        "strategy-market",
        entries,
    )

    assert len(worker.ingested_ticks) == 1
    assert worker.processed_stream_ids == ["2-0"]
    assert ack_calls == [["1-0", "2-0"]]


@pytest.mark.asyncio
async def test_process_market_stream_batch_acks_prior_entries_before_retriable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = FakeStreamWorker()
    ack_calls: list[list[str]] = []

    async def fake_ack(
        _worker: FakeStreamWorker,
        _stream_key: str,
        _group: str,
        ids: list[str],
    ) -> None:
        ack_calls.append(ids)

    monkeypatch.setattr(stream_processing, "ack_market_stream_entries", fake_ack)

    seen = {"count": 0}

    async def flaky_ingest(tick: TickEvent) -> Signal:
        seen["count"] += 1
        if seen["count"] == 2:
            raise ConnectionError("temporary failure")
        worker.ingested_ticks.append(tick)
        return Signal(
            strategy_id="default",
            symbol=tick.symbol,
            signal="BUY",
            confidence=0.9,
        )

    worker.ingest_tick = flaky_ingest  # type: ignore[method-assign]
    entries = [
        (
            "1-0",
            {
                "data": '{"symbol":"BTCUSDT","price":100.0,"quantity":0.1,"event_time":"2026-03-27T12:00:00Z"}',
            },
        ),
        (
            "2-0",
            {
                "data": '{"symbol":"BTCUSDT","price":101.0,"quantity":0.1,"event_time":"2026-03-27T12:00:01Z"}',
            },
        ),
    ]

    with pytest.raises(ConnectionError, match="temporary failure"):
        await stream_processing.process_market_stream_batch(
            worker,
            "cerberus.market.events",
            "strategy-market",
            entries,
        )

    assert worker.processed_stream_ids == ["1-0"]
    assert ack_calls == [["1-0"]]
    assert worker.last_error == "temporary failure"


@pytest.mark.asyncio
async def test_process_market_stream_batch_acks_failed_entry_on_non_retriable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = FakeStreamWorker()
    ack_calls: list[list[str]] = []

    async def fake_ack(
        _worker: FakeStreamWorker,
        _stream_key: str,
        _group: str,
        ids: list[str],
    ) -> None:
        ack_calls.append(ids)

    monkeypatch.setattr(stream_processing, "ack_market_stream_entries", fake_ack)
    worker.fail_on_ingest = ValueError("bad tick")

    entries = [
        (
            "9-0",
            {
                "data": '{"symbol":"BTCUSDT","price":100.0,"quantity":0.1,"event_time":"2026-03-27T12:00:00Z"}',
            },
        )
    ]

    await stream_processing.process_market_stream_batch(
        worker,
        "cerberus.market.events",
        "strategy-market",
        entries,
    )

    assert worker.processed_stream_ids == []
    assert ack_calls == [["9-0"]]
    assert worker.last_error == "bad tick"
