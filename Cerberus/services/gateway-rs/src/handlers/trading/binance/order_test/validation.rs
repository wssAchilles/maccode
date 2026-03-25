use axum::{http::StatusCode, Json};

use crate::gateway_types::{AppState, BinanceTestOrderRequest};
use crate::gateway_utils::{current_millis, parse_positive_number, symbol_allowed};
use crate::handlers::common::error_body;

pub(super) struct PreparedBinanceOrderTest {
    pub(super) symbol: String,
    pub(super) params: Vec<(String, String)>,
}

pub(super) fn validate_order_test_input(
    state: &AppState,
    req: &BinanceTestOrderRequest,
    request_id: &str,
) -> Result<PreparedBinanceOrderTest, (StatusCode, Json<serde_json::Value>)> {
    let symbol = req.symbol.trim().to_ascii_uppercase();
    if symbol.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "symbol is required", request_id),
        ));
    }

    let side = req.side.trim().to_ascii_uppercase();
    if side != "BUY" && side != "SELL" {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "side must be BUY or SELL", request_id),
        ));
    }

    let order_type = req.order_type.trim().to_ascii_uppercase();
    let quantity_raw = req.quantity.trim();
    let quantity =
        parse_positive_number("quantity", quantity_raw).map_err(|(status, message)| {
            (status, error_body("validation_error", message, request_id))
        })?;

    if state.trading_policy.enforced {
        if !symbol_allowed(&symbol, &state.trading_policy.binance_allowed_symbols) {
            return Err((
                StatusCode::FORBIDDEN,
                error_body(
                    "policy_rejected",
                    format!("symbol {symbol} is blocked by trading policy"),
                    request_id,
                ),
            ));
        }

        if let Some(max_qty) = state.trading_policy.max_binance_order_qty {
            if quantity > max_qty {
                return Err((
                    StatusCode::BAD_REQUEST,
                    error_body(
                        "policy_rejected",
                        format!(
                            "quantity {quantity} exceeds policy max_binance_order_qty {max_qty}"
                        ),
                        request_id,
                    ),
                ));
            }
        }
    }

    let mut params = vec![
        ("symbol".to_string(), symbol.clone()),
        ("side".to_string(), side),
        ("type".to_string(), order_type.clone()),
        ("quantity".to_string(), quantity_raw.to_string()),
        ("timestamp".to_string(), current_millis().to_string()),
    ];

    if let Some(recv_window) = req.recv_window {
        params.push(("recvWindow".to_string(), recv_window.to_string()));
    }

    if order_type == "LIMIT" {
        let price_raw = req.price.as_deref().ok_or((
            StatusCode::BAD_REQUEST,
            error_body(
                "validation_error",
                "price is required for LIMIT order",
                request_id,
            ),
        ))?;
        let price =
            parse_positive_number("price", price_raw.trim()).map_err(|(status, message)| {
                (status, error_body("validation_error", message, request_id))
            })?;

        if state.trading_policy.enforced {
            if let Some(max_notional) = state.trading_policy.max_binance_order_notional_usd {
                let notional = quantity * price;
                if notional > max_notional {
                    return Err((
                        StatusCode::BAD_REQUEST,
                        error_body(
                            "policy_rejected",
                            format!(
                                "notional {notional:.6} exceeds policy max_binance_order_notional_usd {max_notional}"
                            ),
                            request_id,
                        ),
                    ));
                }
            }
        }

        params.push(("price".to_string(), price_raw.trim().to_string()));
        params.push((
            "timeInForce".to_string(),
            req.time_in_force
                .clone()
                .unwrap_or_else(|| "GTC".to_string()),
        ));
    }

    Ok(PreparedBinanceOrderTest { symbol, params })
}
