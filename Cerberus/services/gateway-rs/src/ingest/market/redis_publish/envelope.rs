use uuid::Uuid;

use crate::gateway_types::{AppState, MarketEvent};
use crate::gateway_utils::current_millis;

pub(super) fn build_market_event_envelope(
    state: &AppState,
    event: &MarketEvent,
    symbol_channel: &str,
) -> serde_json::Value {
    serde_json::json!({
        "event_type": "market.book_ticker.updated",
        "event_id": format!("evt-{}", Uuid::new_v4().simple()),
        "created_at": current_millis(),
        "schema_version": state.market_event_stream.schema_version,
        "channel": symbol_channel,
        "correlation_id": format!("{}:{}", event.symbol, event.event_time),
        "payload": event,
    })
}
