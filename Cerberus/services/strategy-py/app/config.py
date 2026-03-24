from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "strategy-py"
    service_version: str = "0.1.0"
    cors_allow_origins: str = "*"
    redis_url: str = "redis://localhost:6379/0"
    market_channel: str = "md.orderbook.BTCUSDT"
    market_channels: str = ""
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


settings = Settings()
