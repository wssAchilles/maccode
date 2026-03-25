from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import uuid4

import grpc

from app.order_client_proto import order_pb2_grpc


class MatchingRpcTransport:
    def __init__(self, target: str) -> None:
        self._target = target
        self._channel: grpc.aio.Channel | None = None
        self._stub: order_pb2_grpc.OrderServiceStub | None = None

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def ensure_stub(self) -> order_pb2_grpc.OrderServiceStub:
        if self._stub is not None:
            return self._stub

        resolved = resolve_matching_target(self._target)
        if resolved.secure:
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.aio.secure_channel(resolved.endpoint, credentials)
        else:
            self._channel = grpc.aio.insecure_channel(resolved.endpoint)
        self._stub = order_pb2_grpc.OrderServiceStub(self._channel)
        return self._stub

    async def wait_ready(self, timeout_seconds: float) -> None:
        await self.ensure_stub()
        assert self._channel is not None
        await asyncio.wait_for(self._channel.channel_ready(), timeout=timeout_seconds)

    def build_metadata(self, request_id: str | None = None) -> tuple[list[tuple[str, str]], str]:
        candidate = (request_id or "").strip()
        rid = candidate if candidate else uuid4().hex
        return [("x-request-id", rid)], rid


def _sanitize_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("http://"):
        return target.removeprefix("http://")
    if target.startswith("https://"):
        return target.removeprefix("https://")
    return target


@dataclass(frozen=True)
class MatchingGrpcTarget:
    endpoint: str
    secure: bool


def resolve_matching_target(raw_target: str) -> MatchingGrpcTarget:
    target = raw_target.strip()
    if not target:
        raise ValueError("MATCHING_GRPC_TARGET is empty")

    parsed = urlparse(target)
    if parsed.scheme in ("http", "https", "grpc", "grpcs"):
        host = parsed.hostname
        if not host:
            raise ValueError(f"invalid MATCHING_GRPC_TARGET: {raw_target!r}")
        secure = parsed.scheme in ("https", "grpcs")
        default_port = 443 if secure else 80
        endpoint = f"{host}:{parsed.port or default_port}"
        return MatchingGrpcTarget(endpoint=endpoint, secure=secure)

    if "://" in target:
        raise ValueError(f"unsupported MATCHING_GRPC_TARGET scheme: {parsed.scheme}")

    endpoint = _sanitize_target(target).split("/", maxsplit=1)[0]
    return MatchingGrpcTarget(endpoint=endpoint, secure=False)
