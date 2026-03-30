from __future__ import annotations

from typing import Literal, Protocol

from app.schemas import Signal, SignalRecord, TickEvent

SignalHistorySource = Literal["auto", "supabase", "firestore"]
SignalStoreSource = Literal["supabase", "firestore", "none"]


class SignalRuntimePort(Protocol):
    def read_current_signal(self) -> Signal | None: ...

    def evaluate_tick(self, tick: TickEvent) -> tuple[Signal, str]: ...

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str: ...

    def store_current_signal(self, signal: Signal) -> None: ...

    def record_tick_processed(self) -> None: ...


class SignalClaimPort(Protocol):
    async def claim_signal(self, signal_id: str) -> bool: ...

    async def release_signal_claim(self, signal_id: str) -> None: ...


class SignalEventPort(Protocol):
    async def publish_signal_flow(
        self,
        signal: Signal,
        tick: TickEvent,
        signal_id: str,
    ) -> None: ...


class SignalStorePort(Protocol):
    async def list_recent(
        self,
        limit: int,
        source: SignalHistorySource = "auto",
    ) -> tuple[SignalStoreSource, list[SignalRecord]]: ...


class SignalPublisherPort(Protocol):
    async def publish_signal(self, signal: Signal) -> None: ...
