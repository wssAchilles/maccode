from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from pydantic import BaseModel

from app.ports.signal import SignalHistorySource, SignalStoreSource
from app.schemas import SignalRecord


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _serialize_value(value.to_dict())
    if isinstance(value, BaseModel):
        return value.model_dump()
    if is_dataclass(value):
        return {key: _serialize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class SummaryError:
    code: str
    message: str
    request_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
        }


@dataclass(frozen=True, slots=True)
class SummaryComponent:
    ok: bool
    status_code: int
    payload: Any | None = None
    error: SummaryError | None = None

    @classmethod
    def ok_result(cls, payload: Any, *, status_code: int = 200) -> SummaryComponent:
        return cls(ok=True, status_code=status_code, payload=payload)

    @classmethod
    def error_result(
        cls,
        *,
        code: str,
        message: str,
        request_id: str,
        status_code: int,
    ) -> SummaryComponent:
        return cls(
            ok=False,
            status_code=status_code,
            error=SummaryError(
                code=code,
                message=message,
                request_id=request_id,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "status_code": self.status_code,
        }
        if self.ok:
            payload["payload"] = _serialize_value(self.payload)
        else:
            payload["error"] = self.error.to_dict() if self.error is not None else None
        return payload


@dataclass(frozen=True, slots=True)
class SummarySignalPayload:
    status: str
    signal: str
    confidence: float
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class SummaryRecentSignalsPayload:
    source: SignalStoreSource
    count: int
    signals: list[SignalRecord]


@dataclass(frozen=True, slots=True)
class SummaryResult:
    symbol: str
    source: SignalHistorySource
    recent_limit: int
    orderbook_depth: int
    signal: SummaryComponent
    recent_signals: SummaryComponent
    persistence: SummaryComponent
    matching_orderbook: SummaryComponent

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "source": self.source,
            "recent_limit": self.recent_limit,
            "orderbook_depth": self.orderbook_depth,
            "signal": self.signal.to_dict(),
            "recent_signals": self.recent_signals.to_dict(),
            "persistence": self.persistence.to_dict(),
            "matching_orderbook": self.matching_orderbook.to_dict(),
        }
