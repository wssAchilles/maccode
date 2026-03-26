use crate::gateway_types::{AppState, OrderEvent, MAX_RECENT_ORDER_EVENTS};
use crate::gateway_utils::current_millis;

use super::envelope::normalize_order_payload;

pub(crate) async fn publish_order_event(
    state: &AppState,
    channel: String,
    payload: serde_json::Value,
) {
    let normalized_payload = normalize_order_payload(&channel, payload);
    let event = OrderEvent {
        channel,
        payload: normalized_payload,
        received_at: current_millis(),
    };

    let _ = state.orders_tx.send(event.clone());
    {
        let mut recent = state.recent_order_events.write().await;
        recent.push_back(event);
        if recent.len() > MAX_RECENT_ORDER_EVENTS {
            recent.pop_front();
        }
    }
    {
        let mut metrics = state.metrics.write().await;
        metrics.order_events += 1;
        metrics.last_order_event_at = Some(current_millis());
        metrics.last_order_ingest_error = None;
    }
}
