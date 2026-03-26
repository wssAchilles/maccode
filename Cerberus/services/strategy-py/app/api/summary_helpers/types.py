from __future__ import annotations

from typing import Literal

SummarySource = Literal["auto", "supabase", "firestore"]


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    return normalized or "BTCUSDT"


def normalize_source(source: str) -> SummarySource:
    if source == "supabase":
        return "supabase"
    if source == "firestore":
        return "firestore"
    return "auto"


__all__ = ["SummarySource", "normalize_symbol", "normalize_source"]
