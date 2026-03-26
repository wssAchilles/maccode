#[derive(Clone)]
pub(crate) struct OrderEventsStreamConfig {
    pub(crate) enabled: bool,
    pub(crate) legacy_pubsub_fallback: bool,
    pub(crate) stream_key: String,
    pub(crate) consumer_group: String,
    pub(crate) consumer_name: String,
    pub(crate) read_batch_size: usize,
    pub(crate) read_block_ms: usize,
    pub(crate) pending_replay_count: usize,
    pub(crate) batch_window_ms: u64,
    pub(crate) max_retries_before_fallback: usize,
    pub(crate) retry_backoff_base_ms: u64,
    pub(crate) retry_backoff_max_ms: u64,
    pub(crate) reclaim_enabled: bool,
    pub(crate) reclaim_interval_ms: u64,
    pub(crate) reclaim_idle_ms: u64,
    pub(crate) reclaim_batch_size: usize,
    pub(crate) max_delivery_attempts: usize,
    pub(crate) poison_stream_key: String,
    pub(crate) poison_stream_maxlen: usize,
    pub(crate) pending_warn_threshold: usize,
    pub(crate) lag_warn_threshold: usize,
}

#[derive(Clone)]
pub(crate) struct MarketEventsStreamPublishConfig {
    pub(crate) enabled: bool,
    pub(crate) stream_key: String,
    pub(crate) max_len: usize,
    pub(crate) publish_legacy_pubsub: bool,
    pub(crate) schema_version: String,
}
