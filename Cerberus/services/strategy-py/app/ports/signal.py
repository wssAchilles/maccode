from __future__ import annotations

from typing import Literal, Protocol

from app.schemas import Signal, SignalRecord, TickEvent

SignalHistorySource = Literal["auto", "supabase", "firestore"]
SignalStoreSource = Literal["supabase", "firestore", "none"]


class SignalRuntimePort(Protocol):
    def read_current_signal(self) -> Signal | None: ...

    async def ingest_tick(self, tick: TickEvent) -> Signal: ...


class SignalStorePort(Protocol):
    async def list_recent(
        self,
        limit: int,
        source: SignalHistorySource = "auto",
    ) -> tuple[SignalStoreSource, list[SignalRecord]]: ...


class SignalPublisherPort(Protocol):
    async def publish_signal(self, signal: Signal) -> None: ...
