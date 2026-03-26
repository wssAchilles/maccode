use axum::{http::StatusCode, Json};

use crate::gateway_types::StrategySummaryQuery;
use crate::handlers::common::error_body;

#[derive(Debug, Clone)]
pub(super) struct SummaryRequest {
    pub(super) symbol: String,
    pub(super) source: String,
    pub(super) recent_limit: u16,
    pub(super) orderbook_depth: u16,
}

impl SummaryRequest {
    pub(super) fn cache_key(&self) -> String {
        format!(
            "{}:{}:{}:{}",
            self.symbol, self.recent_limit, self.source, self.orderbook_depth
        )
    }
}

pub(super) fn parse_summary_request(
    query: StrategySummaryQuery,
    request_id: &str,
) -> Result<SummaryRequest, (StatusCode, Json<serde_json::Value>)> {
    let symbol = query
        .symbol
        .unwrap_or_else(|| "BTCUSDT".to_string())
        .trim()
        .to_ascii_uppercase();
    if symbol.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "symbol is required", request_id),
        ));
    }

    let source = query
        .source
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or("auto")
        .to_string();
    if source != "auto" && source != "supabase" && source != "firestore" {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body(
                "validation_error",
                "source must be one of: auto|supabase|firestore",
                request_id,
            ),
        ));
    }

    Ok(SummaryRequest {
        symbol,
        source,
        recent_limit: query.recent_limit.unwrap_or(8).clamp(1, 200),
        orderbook_depth: query.orderbook_depth.unwrap_or(10).clamp(1, 200),
    })
}
