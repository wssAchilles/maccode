use axum::{http::StatusCode, Json};

use crate::gateway_types::{AlpacaOrderRequest, AppState};
use crate::gateway_utils::{parse_positive_number, symbol_allowed};
use crate::handlers::common::error_body;

pub(super) struct PreparedAlpacaCreate {
    pub(super) symbol: String,
    pub(super) payload: serde_json::Value,
}

pub(super) fn validate_alpaca_create(
    state: &AppState,
    req: &AlpacaOrderRequest,
    request_id: &str,
) -> Result<PreparedAlpacaCreate, (StatusCode, Json<serde_json::Value>)> {
    let symbol = req.symbol.trim().to_ascii_uppercase();
    if symbol.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "symbol is required", request_id),
        ));
    }

    let qty_raw = req.qty.trim();
    let qty = parse_positive_number("qty", qty_raw)
        .map_err(|(status, message)| (status, error_body("validation_error", message, request_id)))?;

    let side = req.side.trim().to_ascii_lowercase();
    if side != "buy" && side != "sell" {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "side must be buy or sell", request_id),
        ));
    }

    let order_type = req.order_type.trim().to_ascii_lowercase();
    if order_type != "market" && order_type != "limit" {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "type must be market or limit", request_id),
        ));
    }

    if state.trading_policy.enforced {
        if !symbol_allowed(&symbol, &state.trading_policy.alpaca_allowed_symbols) {
            return Err((
                StatusCode::FORBIDDEN,
                error_body(
                    "policy_rejected",
                    format!("symbol {symbol} is blocked by trading policy"),
                    request_id,
                ),
            ));
        }
        if let Some(max_qty) = state.trading_policy.max_alpaca_order_qty {
            if qty > max_qty {
                return Err((
                    StatusCode::BAD_REQUEST,
                    error_body(
                        "policy_rejected",
                        format!("qty {qty} exceeds policy max_alpaca_order_qty {max_qty}"),
                        request_id,
                    ),
                ));
            }
        }
    }

    let mut payload = serde_json::json!({
        "symbol": symbol,
        "qty": qty_raw,
        "side": side,
        "type": order_type,
        "time_in_force": req.time_in_force.trim().to_ascii_lowercase()
    });
    if order_type == "limit" {
        let limit_price = req.limit_price.as_deref().ok_or((
            StatusCode::BAD_REQUEST,
            error_body(
                "validation_error",
                "limit_price is required for limit orders",
                request_id,
            ),
        ))?;
        let limit_price_raw = limit_price.trim().to_string();
        let limit_price_num = parse_positive_number("limit_price", &limit_price_raw)
            .map_err(|(status, message)| (status, error_body("validation_error", message, request_id)))?;

        if state.trading_policy.enforced {
            if let Some(max_notional) = state.trading_policy.max_alpaca_limit_notional_usd {
                let notional = qty * limit_price_num;
                if notional > max_notional {
                    return Err((
                        StatusCode::BAD_REQUEST,
                        error_body(
                            "policy_rejected",
                            format!(
                                "notional {notional:.6} exceeds policy max_alpaca_limit_notional_usd {max_notional}"
                            ),
                            request_id,
                        ),
                    ));
                }
            }
        }

        payload["limit_price"] = serde_json::Value::String(limit_price_raw);
    }

    Ok(PreparedAlpacaCreate { symbol, payload })
}
