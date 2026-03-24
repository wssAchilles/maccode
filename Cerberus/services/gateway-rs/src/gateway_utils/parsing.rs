use axum::http::StatusCode;

use crate::gateway_types::BinanceSymbolRule;

pub(crate) fn parse_binance_symbol_rule(
    payload: &serde_json::Value,
    symbol: &str,
) -> BinanceSymbolRule {
    let mut min_notional = None;
    let mut min_qty = None;
    let mut step_size = None;
    let mut tick_size = None;

    let symbol_entry = payload
        .get("symbols")
        .and_then(|v| v.as_array())
        .and_then(|symbols| {
            symbols
                .iter()
                .find(|item| item.get("symbol").and_then(|v| v.as_str()) == Some(symbol))
        });

    if let Some(entry) = symbol_entry {
        if let Some(filters) = entry.get("filters").and_then(|v| v.as_array()) {
            for filter in filters {
                let filter_type = filter
                    .get("filterType")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default();
                match filter_type {
                    "MIN_NOTIONAL" | "NOTIONAL" => {
                        if min_notional.is_none() {
                            min_notional = json_number(filter.get("minNotional"))
                                .or_else(|| json_number(filter.get("notional")));
                        }
                    }
                    "LOT_SIZE" | "MARKET_LOT_SIZE" => {
                        if min_qty.is_none() {
                            min_qty = json_number(filter.get("minQty"));
                        }
                        if step_size.is_none() {
                            step_size = json_number(filter.get("stepSize"));
                        }
                    }
                    "PRICE_FILTER" => {
                        if tick_size.is_none() {
                            tick_size = json_number(filter.get("tickSize"));
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    BinanceSymbolRule {
        symbol: symbol.to_string(),
        min_notional,
        min_qty,
        step_size,
        tick_size,
        refreshed_at: super::current_millis(),
    }
}

pub(crate) fn parse_positive_number(field: &str, value: &str) -> Result<f64, (StatusCode, String)> {
    let parsed = value.parse::<f64>().map_err(|_| {
        (
            StatusCode::BAD_REQUEST,
            format!("{field} must be a valid number"),
        )
    })?;
    if !parsed.is_finite() || parsed <= 0.0 {
        return Err((StatusCode::BAD_REQUEST, format!("{field} must be > 0")));
    }
    Ok(parsed)
}

pub(crate) fn symbol_allowed(symbol: &str, allowlist: &[String]) -> bool {
    if allowlist.is_empty() {
        return true;
    }
    allowlist.iter().any(|allowed| allowed == symbol)
}

fn json_number(value: Option<&serde_json::Value>) -> Option<f64> {
    let value = value?;
    if let Some(v) = value.as_f64() {
        return Some(v);
    }
    value.as_str()?.parse::<f64>().ok()
}
