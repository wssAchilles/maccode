from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ResponseWrapper(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorDetail | None = None

    @classmethod
    def success_response(cls, data: T) -> ResponseWrapper[T]:
        return cls(success=True, data=data, error=None)

    @classmethod
    def error_response(cls, error: ErrorDetail) -> ResponseWrapper[None]:
        return ResponseWrapper[None](success=False, data=None, error=error)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
