use crate::gateway_types::{AppState, OrderEvent, MAX_RECENT_ORDER_EVENTS};
use crate::gateway_utils::current_millis;

pub(crate) async fn publish_order_event(
    state: &AppState,
    channel: String,
    payload: serde_json::Value,
) {
    let event = OrderEvent {
        channel,
        payload,
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

pub(crate) fn event_matches_account(event: &OrderEvent, account_id: &str) -> bool {
    if event.channel.ends_with(&format!(".{account_id}")) {
        return true;
    }

    ["account_id", "maker_account_id", "taker_account_id"]
        .iter()
        .any(|key| {
            event
                .payload
                .get(key)
                .and_then(|value| value.as_str())
                .is_some_and(|value| value == account_id)
        })
}
