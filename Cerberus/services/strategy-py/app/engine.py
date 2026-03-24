from collections import deque
from dataclasses import dataclass


@dataclass
class SignalResult:
    signal: str
    confidence: float


class MovingAverageEngine:
    def __init__(self, fast_window: int, slow_window: int) -> None:
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

        self.fast_window = fast_window
        self.slow_window = slow_window
        self._prices: deque[float] = deque(maxlen=slow_window)

    def add_price(self, price: float) -> SignalResult:
        self._prices.append(price)
        if len(self._prices) < self.slow_window:
            return SignalResult(signal="HOLD", confidence=0.0)

        prices = list(self._prices)
        fast_avg = sum(prices[-self.fast_window :]) / self.fast_window
        slow_avg = sum(prices) / self.slow_window

        delta = fast_avg - slow_avg
        confidence = min(abs(delta / slow_avg), 1.0) if slow_avg else 0.0

        if delta > 0:
            return SignalResult(signal="BUY", confidence=confidence)
        if delta < 0:
            return SignalResult(signal="SELL", confidence=confidence)
        return SignalResult(signal="HOLD", confidence=0.0)
