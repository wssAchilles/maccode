use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::IntoResponse,
};
use tracing::error;

use crate::gateway_types::AppState;

pub(crate) async fn ws_market(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_market_ws(socket, state))
}

async fn handle_market_ws(mut socket: WebSocket, state: AppState) {
    let mut rx = state.market_tx.subscribe();
    while let Ok(event) = rx.recv().await {
        if socket
            .send(Message::Text(match serde_json::to_string(&event) {
                Ok(s) => s.into(),
                Err(err) => {
                    error!("failed to serialize market event: {err}");
                    continue;
                }
            }))
            .await
            .is_err()
        {
            break;
        }
    }
}
