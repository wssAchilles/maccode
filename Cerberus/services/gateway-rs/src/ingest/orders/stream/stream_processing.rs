use redis::{aio::MultiplexedConnection, streams::StreamId};

use crate::event_bus::publish_order_event;
use crate::gateway_types::AppState;

use super::stream_io::ack_stream_entries;
use super::stream_payload::{
    decode_stream_payload, extract_stream_channel, stringify_stream_entry,
};

pub(super) async fn process_stream_batch(
    state: &AppState,
    conn: &mut MultiplexedConnection,
    entries: Vec<StreamId>,
) -> anyhow::Result<()> {
    let mut stream_ids = Vec::with_capacity(entries.len());
    for entry in entries {
        let payload = decode_stream_payload(&entry).unwrap_or_else(|| {
            serde_json::json!({
                "raw": stringify_stream_entry(&entry),
            })
        });
        let channel = extract_stream_channel(&payload, &state.order_event_stream.stream_key);
        publish_order_event(state, channel, payload).await;
        stream_ids.push(entry.id);
    }
    ack_stream_entries(state, conn, &stream_ids).await?;
    Ok(())
}
