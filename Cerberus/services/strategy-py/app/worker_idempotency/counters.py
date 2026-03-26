from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IdempotencyCounters:
    signal_claim_attempts: int = 0
    signal_claim_conflicts: int = 0
    signal_claim_rollbacks: int = 0
    order_claim_attempts: int = 0
    order_claim_conflicts: int = 0
    order_claim_rollbacks: int = 0
    redis_errors: int = 0

    def snapshot(self, *, redis_enabled: bool) -> dict[str, int | bool]:
        return {
            "redis_enabled": redis_enabled,
            "signal_claim_attempts": self.signal_claim_attempts,
            "signal_claim_conflicts": self.signal_claim_conflicts,
            "signal_claim_rollbacks": self.signal_claim_rollbacks,
            "order_claim_attempts": self.order_claim_attempts,
            "order_claim_conflicts": self.order_claim_conflicts,
            "order_claim_rollbacks": self.order_claim_rollbacks,
            "redis_errors": self.redis_errors,
        }

    def increment_claim_attempt(self, *, order_scope: bool) -> None:
        if order_scope:
            self.order_claim_attempts += 1
            return
        self.signal_claim_attempts += 1

    def increment_claim_conflict(self, *, order_scope: bool) -> None:
        if order_scope:
            self.order_claim_conflicts += 1
            return
        self.signal_claim_conflicts += 1

    def increment_claim_rollback(self, *, order_scope: bool) -> None:
        if order_scope:
            self.order_claim_rollbacks += 1
            return
        self.signal_claim_rollbacks += 1

    def increment_redis_error(self) -> None:
        self.redis_errors += 1


__all__ = ["IdempotencyCounters"]
