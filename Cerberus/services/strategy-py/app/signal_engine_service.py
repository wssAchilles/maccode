from __future__ import annotations

from app.engine import MovingAverageEngine
from app.schemas import Signal, TickEvent


class SignalEngineService:
    def __init__(self, *, fast_window: int, slow_window: int) -> None:
        self._fast_window = fast_window
        self._slow_window = slow_window
        self._engines: dict[str, MovingAverageEngine] = {}

    @property
    def tracked_symbols(self) -> list[str]:
        return sorted(self._engines.keys())

    def evaluate_tick(self, tick: TickEvent) -> tuple[Signal, str]:
        engine = self._engine_for_symbol(tick.symbol)
        result = engine.add_price(tick.price)
        signal = Signal(
            strategy_id="default",
            symbol=tick.symbol,
            signal=result.signal,
            confidence=result.confidence,
        )
        return signal, self.build_signal_id(tick, signal)

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str:
        event_time = tick.event_time.strip() or "0"
        return f"{signal.strategy_id}:{signal.symbol}:{event_time}:{signal.signal}"

    def _engine_for_symbol(self, symbol: str) -> MovingAverageEngine:
        engine = self._engines.get(symbol)
        if engine is not None:
            return engine
        engine = MovingAverageEngine(
            fast_window=self._fast_window,
            slow_window=self._slow_window,
        )
        self._engines[symbol] = engine
        return engine
