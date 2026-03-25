from pydantic import BaseModel, Field


class TickEvent(BaseModel):
    symbol: str
    price: float = Field(gt=0)
    quantity: float = Field(ge=0)
    event_time: str


class Signal(BaseModel):
    strategy_id: str
    symbol: str
    signal: str
    confidence: float = Field(ge=0, le=1)


class SignalRecord(Signal):
    created_at: str


class OptimizeRequest(BaseModel):
    asset_names: list[str]
    expected_returns: list[float]
    covariance: list[list[float]]
    risk_aversion: float = Field(default=1.0, gt=0)


class OptimizeResponse(BaseModel):
    objective: float
    weights: dict[str, float]


class MatchingSubmitRequest(BaseModel):
    symbol: str
    side: str = Field(pattern="^(BUY|SELL)$")
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    account_id: str | None = None
    client_order_id: str | None = None


class MatchingCancelRequest(BaseModel):
    account_id: str | None = None


class MatchingSubmitResponse(BaseModel):
    accepted: bool
    order_id: str
    reason: str
    request_id: str | None = None


class MatchingCancelResponse(BaseModel):
    canceled: bool
    reason: str
    request_id: str | None = None


class MatchingOrderView(BaseModel):
    order_id: str
    account_id: str
    symbol: str
    side: str
    order_type: str
    price: float
    quantity: float
    filled_quantity: float
    status: str
    updated_at: str | None = None
    request_id: str | None = None


class MatchingExecutionView(BaseModel):
    execution_id: str
    order_id: str
    account_id: str
    symbol: str
    price: float
    quantity: float
    event_time: str | None = None
    request_id: str | None = None


class MatchingHealthView(BaseModel):
    enabled: bool = True
    reachable: bool = True
    status: str
    service: str
    version: str
    uptime_seconds: int
    request_id: str | None = None
    reason: str | None = None


class MatchingStatsView(BaseModel):
    enabled: bool = True
    live_orders: int
    trade_count: int
    tracked_orders: int
    rejected_orders: int
    symbols: int
    best_bid: float | None = None
    best_ask: float | None = None
    request_id: str | None = None


class MatchingOrderBookLevelView(BaseModel):
    price: float
    total_quantity: float
    order_count: int


class MatchingOrderBookView(BaseModel):
    enabled: bool = True
    symbol: str
    depth: int
    bids: list[MatchingOrderBookLevelView]
    asks: list[MatchingOrderBookLevelView]
    generated_at_ms: int
    request_id: str | None = None
