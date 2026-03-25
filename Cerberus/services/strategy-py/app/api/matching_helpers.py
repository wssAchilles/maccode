import grpc
from fastapi import HTTPException

from app.redis_worker import RedisMarketWorker


def ensure_matching_enabled(worker: RedisMarketWorker) -> None:
    if not worker.matching_client.enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "matching_disabled",
                "message": "matching gRPC is disabled",
            },
        )


def grpc_details(exc: grpc.aio.AioRpcError) -> str:
    return exc.details() or str(exc)


def raise_get_order_error(exc: grpc.aio.AioRpcError) -> None:
    if exc.code() == grpc.StatusCode.NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "matching_order_not_found",
                "message": grpc_details(exc),
            },
        ) from exc
    if exc.code() == grpc.StatusCode.PERMISSION_DENIED:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "matching_order_forbidden",
                "message": grpc_details(exc),
            },
        ) from exc
    raise HTTPException(
        status_code=502,
        detail={
            "code": "matching_get_order_failed",
            "message": f"matching get_order failed: {grpc_details(exc)}",
        },
    ) from exc


def raise_orderbook_error(exc: grpc.aio.AioRpcError) -> None:
    if exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "matching_orderbook_invalid_argument",
                "message": grpc_details(exc),
            },
        ) from exc
    raise HTTPException(
        status_code=502,
        detail={
            "code": "matching_orderbook_failed",
            "message": f"matching orderbook failed: {grpc_details(exc)}",
        },
    ) from exc


def raise_gateway_grpc_error(prefix: str, exc: grpc.aio.AioRpcError) -> None:
    raise HTTPException(
        status_code=502,
        detail={
            "code": "matching_gateway_grpc_error",
            "message": f"{prefix}: {grpc_details(exc)}",
        },
    ) from exc
