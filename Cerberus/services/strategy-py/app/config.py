from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "strategy-py"
    service_version: str = "0.1.0"
    cors_allow_origins: str = "*"
    redis_url: str = "redis://localhost:6379/0"
    market_channel: str = "md.orderbook.BTCUSDT"
    market_channels: str = ""
    market_stream_enabled: bool = True
    market_stream_key: str = "cerberus.market.events"
    market_stream_consumer_group: str = "strategy-market"
    market_stream_consumer_name: str = ""
    market_stream_read_batch_size: int = 64
    market_stream_read_block_ms: int = 3000
    market_stream_pending_replay_count: int = 128
    market_stream_batch_window_ms: int = 100
    market_stream_max_retries_before_fallback: int = 6
    market_stream_retry_backoff_ms: int = 200
    market_stream_retry_backoff_max_ms: int = 5000
    market_stream_reclaim_enabled: bool = True
    market_stream_reclaim_interval_ms: int = 5000
    market_stream_reclaim_idle_ms: int = 30000
    market_stream_reclaim_batch_size: int = 64
    market_stream_max_delivery_attempts: int = 8
    market_stream_pending_warn_threshold: int = 2000
    market_stream_lag_warn_threshold: int = 2000
    market_stream_poison_stream_key: str = "cerberus.market.events.poison"
    market_stream_poison_stream_maxlen: int = 20000
    market_stream_legacy_pubsub_fallback: bool = True
    signal_channel: str = "strategy.signals.default"
    fast_window: int = 5
    slow_window: int = 20
    grb_licenseid: str | None = None
    grb_wlsaccessid: str | None = None
    grb_wlssecret: str | None = None
    firebase_enabled: bool = False
    firebase_project_id: str | None = None
    firebase_signal_collection: str = "strategy_signals"
    supabase_enabled: bool = False
    supabase_project_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_signal_table: str = "strategy_signals"
    supabase_timeout_seconds: float = 5.0
    signal_history_limit_default: int = 20
    signal_history_limit_max: int = 200
    matching_enabled: bool = False
    matching_grpc_target: str = "localhost:50051"
    matching_grpc_timeout_seconds: float = 2.0
    strategy_account_id: str = "default"
    strategy_order_quantity: float = 0.001
    trade_execution_channel_prefix: str = "trade.executions"
    execution_relay_interval_seconds: float = 1.0
    execution_relay_batch_limit: int = 100
    event_stream_enabled: bool = True
    event_stream_key: str = "cerberus.order.events"
    event_stream_maxlen: int = 10_000
    event_stream_publish_legacy_pubsub: bool = True
    event_schema_version: str = "v1"
    idempotency_store_redis_enabled: bool = True
    idempotency_redis_key_prefix: str = "cerberus:idempotency"
    signal_idempotency_ttl_seconds: int = 900
    idempotency_max_entries: int = 20_000
    retriable_base_backoff_seconds: float = 0.2
    retriable_max_backoff_seconds: float = 5.0


settings = Settings()
