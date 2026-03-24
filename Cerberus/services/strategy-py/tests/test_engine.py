from app.engine import MovingAverageEngine


def test_engine_stays_hold_before_warmup() -> None:
    engine = MovingAverageEngine(fast_window=2, slow_window=4)
    assert engine.add_price(100).signal == "HOLD"
    assert engine.add_price(101).signal == "HOLD"


def test_engine_emits_buy_when_fast_above_slow() -> None:
    engine = MovingAverageEngine(fast_window=2, slow_window=4)
    for price in [100.0, 100.0, 101.0, 103.0]:
        result = engine.add_price(price)

    assert result.signal == "BUY"
    assert result.confidence > 0
