mod consume;
mod maintenance;
mod stream_group;
mod stream_io;
mod stream_payload;
mod stream_processing;
mod stream_reclaim;

use anyhow::Context;
use tracing::info;

use crate::gateway_types::AppState;

use super::stream_metrics::clear_order_ingest_error;
use consume::stream_consume_loop;
use stream_group::{ensure_stream_consumer_group, replay_pending_entries};

pub(super) async fn run_order_events_stream_loop(state: &AppState) -> anyhow::Result<()> {
    let client = redis::Client::open(state.redis_url.as_str()).context("invalid redis url")?;
    let mut conn = client
        .get_multiplexed_async_connection()
        .await
        .context("redis stream connection failed")?;

    ensure_stream_consumer_group(&mut conn, &state.order_event_stream).await?;
    clear_order_ingest_error(state).await;

    replay_pending_entries(state, &mut conn).await?;
    info!(
        "consuming order events stream={} group={} consumer={}",
        state.order_event_stream.stream_key,
        state.order_event_stream.consumer_group,
        state.order_event_stream.consumer_name
    );
    stream_consume_loop(state, &mut conn).await
}
