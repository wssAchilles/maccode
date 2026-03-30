from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
from typing import Iterable

import numpy as np


def _sample_std(values: Iterable[float]) -> float:
    array = np.asarray(tuple(values), dtype=np.float64)
    if array.size < 2:
        return 0.0
    return float(array.std(ddof=1))


@dataclass(slots=True)
class SymbolFeatureBuffer:
    feature_columns: tuple[str, ...]
    lookback: int
    prices: deque[float] = field(default_factory=lambda: deque(maxlen=56))
    quantities: deque[float] = field(default_factory=lambda: deque(maxlen=21))
    notionals: deque[float] = field(default_factory=lambda: deque(maxlen=21))
    feature_rows: deque[np.ndarray] = field(default_factory=deque)
    ema_8: float | None = None
    ema_21: float | None = None
    ema_55: float | None = None

    def __post_init__(self) -> None:
        self.feature_rows = deque(maxlen=self.lookback)

    def update(self, *, price: float, quantity: float) -> np.ndarray | None:
        self.prices.append(float(price))
        self.quantities.append(float(quantity))
        self.notionals.append(float(price * quantity))
        self.ema_8 = self._update_ema(self.ema_8, price, span=8)
        self.ema_21 = self._update_ema(self.ema_21, price, span=21)
        self.ema_55 = self._update_ema(self.ema_55, price, span=55)

        features = self._build_feature_row(price=price, quantity=quantity)
        if features is None:
            return None
        self.feature_rows.append(features)
        if len(self.feature_rows) < self.lookback:
            return None
        return np.asarray(self.feature_rows, dtype=np.float32)

    @staticmethod
    def _update_ema(current: float | None, price: float, *, span: int) -> float:
        alpha = 2.0 / (span + 1)
        if current is None:
            return float(price)
        return float((alpha * price) + ((1.0 - alpha) * current))

    def _build_feature_row(self, *, price: float, quantity: float) -> np.ndarray | None:
        if len(self.prices) < 22 or len(self.quantities) < 21 or len(self.notionals) < 21:
            return None
        if self.ema_8 is None or self.ema_21 is None or self.ema_55 is None:
            return None

        price_list = list(self.prices)
        quantity_list = list(self.quantities)
        notional_list = list(self.notionals)

        previous_price = price_list[-2]
        features = {
            "log_ret_1": math.log(price) - math.log(previous_price),
            "ret_1": (price / previous_price) - 1.0,
            "ret_3": self._pct_change(price_list, periods=3),
            "ret_8": self._pct_change(price_list, periods=8),
            "ret_21": self._pct_change(price_list, periods=21),
            "log_quantity": math.log1p(quantity),
            "ema_gap_8": (price - self.ema_8) / (self.ema_8 + 1e-12),
            "ema_gap_21": (price - self.ema_21) / (self.ema_21 + 1e-12),
            "ema_cross_8_21": (self.ema_8 - self.ema_21) / (self.ema_21 + 1e-12),
            "ema_cross_21_55": (self.ema_21 - self.ema_55) / (self.ema_55 + 1e-12),
            "vol_8": _sample_std(price_list[-8:]),
            "vol_21": _sample_std(price_list[-21:]),
            "qty_z_21": self._zscore(quantity_list),
            "notional_z_21": self._zscore(notional_list),
        }
        return np.asarray(
            [float(features[column]) for column in self.feature_columns],
            dtype=np.float32,
        )

    @staticmethod
    def _pct_change(prices: list[float], *, periods: int) -> float:
        baseline = prices[-(periods + 1)]
        return (prices[-1] / baseline) - 1.0

    @staticmethod
    def _zscore(values: list[float]) -> float:
        current = values[-1]
        mean = float(np.mean(values))
        std = _sample_std(values)
        return (current - mean) / (std + 1e-6)
