use std::time::Duration;

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::IntoResponse,
};
use tokio::time::timeout;
use tracing::warn;

use crate::gateway_types::AppState;

pub(crate) async fn ws_orders(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_orders_ws(socket, state))
}

async fn handle_orders_ws(mut socket: WebSocket, state: AppState) {
    let mut rx = state.orders_tx.subscribe();
    loop {
        match timeout(Duration::from_secs(10), rx.recv()).await {
            Ok(Ok(event)) => {
                let payload = match serde_json::to_string(&event) {
                    Ok(payload) => payload,
                    Err(err) => {
                        warn!("failed to serialize order event: {err}");
                        continue;
                    }
                };
                if socket.send(Message::Text(payload.into())).await.is_err() {
                    break;
                }
            }
            Ok(Err(_)) => break,
            Err(_) => {
                let heartbeat = serde_json::json!({
                    "type": "heartbeat",
                    "message": "orders stream alive"
                });
                if socket
                    .send(Message::Text(heartbeat.to_string().into()))
                    .await
                    .is_err()
                {
                    break;
                }
            }
        }
    }
}
