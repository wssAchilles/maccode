use std::{env, time::Duration};

use anyhow::Context;
use futures_util::StreamExt;
use tokio::time::sleep;
use tokio_tungstenite::connect_async;
use tracing::{error, info};

use crate::gateway_types::{AppState, DEFAULT_BINANCE_STREAM_BASE};
use crate::gateway_utils::current_millis;

use super::decode::parse_market_event;
use super::redis_publish::{connect_redis, publish_market_event};
use super::ws_url::build_binance_market_ws_url;

pub(crate) fn spawn_market_ingest(state: AppState) {
    tokio::spawn(async move {
        loop {
            if let Err(err) = run_ingest_loop(state.clone()).await {
                error!("market ingest failed: {err:#}");
                {
                    let mut metrics = state.metrics.write().await;
                    metrics.last_market_ingest_error = Some(err.to_string());
                }
                sleep(Duration::from_secs(2)).await;
            }
        }
    });
}

async fn run_ingest_loop(state: AppState) -> anyhow::Result<()> {
    let ws_url = env::var("MARKET_WS_URL").unwrap_or_else(|_| {
        build_binance_market_ws_url(
            &state.market_symbols,
            DEFAULT_BINANCE_STREAM_BASE,
            "@bookTicker",
        )
    });
    info!("connecting market stream: {ws_url}");

    let (ws_stream, _) = connect_async(&ws_url)
        .await
        .context("websocket connect failed")?;
    let (_, mut read) = ws_stream.split();
    {
        let mut metrics = state.metrics.write().await;
        metrics.last_market_ingest_error = None;
    }

    let mut redis_conn = connect_redis(state.redis_url.as_str()).await;

    while let Some(message) = read.next().await {
        let message = message?;
        if !message.is_text() {
            continue;
        }

        let raw = message.to_text()?;
        let Some(event) = parse_market_event(raw) else {
            continue;
        };

        let payload = serde_json::to_string(&event)?;
        publish_market_event(&state, &mut redis_conn, &event, payload.as_str()).await;

        {
            let mut guard = state.latest_event.write().await;
            *guard = Some(event.clone());
        }
        {
            let mut by_symbol = state.latest_by_symbol.write().await;
            by_symbol.insert(event.symbol.clone(), event.clone());
        }

        {
            let mut metrics = state.metrics.write().await;
            metrics.market_events += 1;
            metrics.last_market_event_at = Some(current_millis());
            metrics.last_market_ingest_error = None;
        }

        let _ = state.market_tx.send(event);
    }

    Ok(())
}
