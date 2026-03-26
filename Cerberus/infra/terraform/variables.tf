variable "project_id" {
  description = "GCP project id"
  type        = string
  default     = "cerberus-9d94f"
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "asia-east2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "container_images" {
  description = "Container image URIs for Cloud Run services"
  type = object({
    gateway  = string
    strategy = string
    matching = optional(string)
  })
  default = {
    gateway  = "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/gateway:latest"
    strategy = "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/strategy:latest"
    matching = "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/matching:latest"
  }
}

variable "gurobi_licenseid" {
  description = "Gurobi WLS LICENSEID"
  type        = string
  sensitive   = true
}

variable "gurobi_wlsaccessid" {
  description = "Gurobi WLS ACCESS ID"
  type        = string
  sensitive   = true
}

variable "gurobi_wlssecret" {
  description = "Gurobi WLS SECRET"
  type        = string
  sensitive   = true
}

variable "upstash_redis_url" {
  description = "Upstash Redis URL"
  type        = string
  sensitive   = true
}

variable "upstash_redis_rest_url" {
  description = "Upstash Redis REST URL"
  type        = string
  sensitive   = true
}

variable "upstash_redis_rest_token" {
  description = "Upstash Redis REST token"
  type        = string
  sensitive   = true
}

variable "supabase_project_url" {
  description = "Supabase project URL"
  type        = string
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase anon key"
  type        = string
  sensitive   = true
}

variable "supabase_service_role_key" {
  description = "Supabase service role key"
  type        = string
  sensitive   = true
}

variable "supabase_db_url" {
  description = "Supabase DB connection URL"
  type        = string
  sensitive   = true
}

variable "firebase_web_api_key" {
  description = "Firebase Web API key for gateway ID token verification"
  type        = string
  sensitive   = true
}

variable "binance_api_key" {
  description = "Binance API key for signed gateway trading endpoint"
  type        = string
  sensitive   = true
}

variable "binance_api_secret" {
  description = "Binance API secret for signed gateway trading endpoint"
  type        = string
  sensitive   = true
}

variable "alpaca_api_key" {
  description = "Alpaca API key for paper trading endpoint"
  type        = string
  sensitive   = true
}

variable "alpaca_api_secret" {
  description = "Alpaca API secret for paper trading endpoint"
  type        = string
  sensitive   = true
}

variable "firebase_project_id" {
  description = "Firebase project id"
  type        = string
  default     = "cerberus-9d94f"
}

variable "firebase_enabled" {
  description = "Enable Firebase writes in strategy service"
  type        = bool
  default     = true
}

variable "firebase_signal_collection" {
  description = "Firestore collection for strategy signals"
  type        = string
  default     = "strategy_signals"
}

variable "supabase_enabled" {
  description = "Enable Supabase persistence in strategy service"
  type        = bool
  default     = true
}

variable "matching_enabled" {
  description = "Enable strategy -> matching gRPC integration"
  type        = bool
  default     = false
}

variable "strategy_internal_auth_enabled" {
  description = "Enable gateway -> strategy internal service auth via GCP metadata identity token"
  type        = bool
  default     = true
}

variable "strategy_internal_auth_token_ttl_seconds" {
  description = "Gateway cache TTL for strategy internal auth token"
  type        = number
  default     = 300

  validation {
    condition = (
      var.strategy_internal_auth_token_ttl_seconds >= 30 &&
      var.strategy_internal_auth_token_ttl_seconds <= 3600
    )
    error_message = "strategy_internal_auth_token_ttl_seconds must be in [30,3600]."
  }
}

variable "strategy_internal_auth_metadata_identity_url" {
  description = "Metadata identity endpoint used by gateway to mint internal auth token"
  type        = string
  default     = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
}

variable "strategy_upstream_timeout_ms" {
  description = "Gateway timeout for strategy summary/status upstream calls"
  type        = number
  default     = 1800

  validation {
    condition     = var.strategy_upstream_timeout_ms >= 100 && var.strategy_upstream_timeout_ms <= 30000
    error_message = "strategy_upstream_timeout_ms must be in [100,30000]."
  }
}

variable "strategy_upstream_health_timeout_ms" {
  description = "Gateway timeout for strategy health upstream call"
  type        = number
  default     = 1500

  validation {
    condition = (
      var.strategy_upstream_health_timeout_ms >= 100 &&
      var.strategy_upstream_health_timeout_ms <= 30000
    )
    error_message = "strategy_upstream_health_timeout_ms must be in [100,30000]."
  }
}

variable "strategy_upstream_max_inflight" {
  description = "Gateway max in-flight upstream requests to strategy"
  type        = number
  default     = 64

  validation {
    condition     = var.strategy_upstream_max_inflight >= 1 && var.strategy_upstream_max_inflight <= 10000
    error_message = "strategy_upstream_max_inflight must be in [1,10000]."
  }
}

variable "strategy_upstream_queue_timeout_ms" {
  description = "Gateway max wait time for strategy upstream queue slot"
  type        = number
  default     = 250

  validation {
    condition = (
      var.strategy_upstream_queue_timeout_ms >= 1 &&
      var.strategy_upstream_queue_timeout_ms <= 10000
    )
    error_message = "strategy_upstream_queue_timeout_ms must be in [1,10000]."
  }
}

variable "strategy_upstream_circuit_enabled" {
  description = "Enable gateway strategy upstream circuit breaker"
  type        = bool
  default     = true
}

variable "strategy_upstream_circuit_failure_threshold" {
  description = "Consecutive upstream failures required to open circuit"
  type        = number
  default     = 6

  validation {
    condition = (
      var.strategy_upstream_circuit_failure_threshold >= 1 &&
      var.strategy_upstream_circuit_failure_threshold <= 100
    )
    error_message = "strategy_upstream_circuit_failure_threshold must be in [1,100]."
  }
}

variable "strategy_upstream_circuit_open_ms" {
  description = "Duration circuit stays open before probe retries"
  type        = number
  default     = 15000

  validation {
    condition = (
      var.strategy_upstream_circuit_open_ms >= 100 &&
      var.strategy_upstream_circuit_open_ms <= 300000
    )
    error_message = "strategy_upstream_circuit_open_ms must be in [100,300000]."
  }
}

variable "firebase_auth_required" {
  description = "Require Firebase ID token verification on protected gateway APIs"
  type        = bool
  default     = true
}

variable "jwt_auth_enabled" {
  description = "Enable gateway JWT verification for protected APIs in non-production environments"
  type        = bool
  default     = false
}

variable "jwt_auth_require_in_production" {
  description = "Force gateway JWT verification when APP_ENV=production"
  type        = bool
  default     = true
}

variable "jwt_hs256_secret" {
  description = "Gateway JWT HS256 shared secret"
  type        = string
  sensitive   = true
}

variable "jwt_issuer" {
  description = "Expected JWT issuer claim for gateway verification (optional)"
  type        = string
  default     = ""
}

variable "jwt_audience" {
  description = "Expected JWT audience claim for gateway verification (optional)"
  type        = string
  default     = ""
}

variable "cors_allow_origins" {
  description = "Comma separated allowed origins for gateway and strategy"
  type        = string
  default     = "*"
}

variable "binance_api_base" {
  description = "Binance REST API base URL"
  type        = string
  default     = "https://demo-fapi.binance.com"
}

variable "binance_order_test_path" {
  description = "Binance order test API path"
  type        = string
  default     = "/fapi/v1/order/test"
}

variable "kline_api_url" {
  description = "Binance kline API URL"
  type        = string
  default     = "https://demo-fapi.binance.com/fapi/v1/klines"
}

variable "trading_policy_enforced" {
  description = "Enable gateway-side trading policy checks"
  type        = bool
  default     = true
}

variable "binance_allowed_symbols" {
  description = "Comma separated Binance allowed symbols"
  type        = string
  default     = "BTCUSDT,ETHUSDT"
}

variable "alpaca_allowed_symbols" {
  description = "Comma separated Alpaca allowed symbols"
  type        = string
  default     = "AAPL,TSLA,NVDA"
}

variable "max_binance_order_qty" {
  description = "Maximum Binance order quantity"
  type        = number
  default     = 0.05
}

variable "max_binance_order_notional_usd" {
  description = "Maximum Binance order notional in USD"
  type        = number
  default     = 5000
}

variable "max_alpaca_order_qty" {
  description = "Maximum Alpaca order quantity"
  type        = number
  default     = 100
}

variable "max_alpaca_limit_notional_usd" {
  description = "Maximum Alpaca limit order notional in USD"
  type        = number
  default     = 20000
}

variable "alpaca_trading_base_url" {
  description = "Alpaca trading base URL"
  type        = string
  default     = "https://paper-api.alpaca.markets/v2"
}

variable "market_symbols" {
  description = "Comma separated market symbols"
  type        = string
  default     = "BTCUSDT,ETHUSDT"
}

variable "redis_order_events_channels" {
  description = "Comma separated order event channels consumed by gateway"
  type        = string
  default     = "strategy.signals.default,trade.executions.default"
}

variable "redis_order_events_stream_enabled" {
  description = "Enable gateway order events stream consumer-group ingest path"
  type        = bool
  default     = true
}

variable "redis_order_events_stream_key" {
  description = "Redis stream key consumed by gateway for order events"
  type        = string
  default     = "cerberus.order.events"
}

variable "redis_order_events_consumer_group" {
  description = "Gateway consumer group for order events stream"
  type        = string
  default     = "gateway-orders"
}

variable "redis_order_events_consumer_name" {
  description = "Gateway consumer name for order events stream"
  type        = string
  default     = ""
}

variable "redis_order_events_read_batch_size" {
  description = "Gateway order stream read batch size"
  type        = number
  default     = 64

  validation {
    condition     = var.redis_order_events_read_batch_size >= 1 && var.redis_order_events_read_batch_size <= 1024
    error_message = "redis_order_events_read_batch_size must be in [1,1024]."
  }
}

variable "redis_order_events_read_block_ms" {
  description = "Gateway order stream read block timeout in milliseconds"
  type        = number
  default     = 3000
}

variable "redis_order_events_pending_replay_count" {
  description = "Gateway order stream pending replay batch size on startup"
  type        = number
  default     = 128

  validation {
    condition = (
      var.redis_order_events_pending_replay_count >= 1 &&
      var.redis_order_events_pending_replay_count <= 4096
    )
    error_message = "redis_order_events_pending_replay_count must be in [1,4096]."
  }
}

variable "redis_order_events_batch_window_ms" {
  description = "Gateway order stream consumer batch processing interval in milliseconds"
  type        = number
  default     = 100

  validation {
    condition     = var.redis_order_events_batch_window_ms >= 0 && var.redis_order_events_batch_window_ms <= 5000
    error_message = "redis_order_events_batch_window_ms must be in [0,5000]."
  }
}

variable "redis_order_events_max_retries_before_fallback" {
  description = "Gateway order stream max retries before fallback to pub/sub"
  type        = number
  default     = 6

  validation {
    condition = (
      var.redis_order_events_max_retries_before_fallback >= 0 &&
      var.redis_order_events_max_retries_before_fallback <= 50
    )
    error_message = "redis_order_events_max_retries_before_fallback must be in [0,50]."
  }
}

variable "redis_order_events_retry_backoff_ms" {
  description = "Gateway order stream retry backoff base in milliseconds"
  type        = number
  default     = 200
}

variable "redis_order_events_retry_backoff_max_ms" {
  description = "Gateway order stream retry backoff max in milliseconds"
  type        = number
  default     = 5000
}

variable "redis_order_events_reclaim_enabled" {
  description = "Enable gateway order stream stale pending reclaim loop"
  type        = bool
  default     = true
}

variable "redis_order_events_reclaim_interval_ms" {
  description = "Gateway order stream reclaim interval in milliseconds"
  type        = number
  default     = 5000
}

variable "redis_order_events_reclaim_idle_ms" {
  description = "Gateway order stream minimum idle time before reclaim in milliseconds"
  type        = number
  default     = 30000
}

variable "redis_order_events_reclaim_batch_size" {
  description = "Gateway order stream reclaim batch size"
  type        = number
  default     = 64

  validation {
    condition = (
      var.redis_order_events_reclaim_batch_size >= 1 &&
      var.redis_order_events_reclaim_batch_size <= 1024
    )
    error_message = "redis_order_events_reclaim_batch_size must be in [1,1024]."
  }
}

variable "redis_order_events_max_delivery_attempts" {
  description = "Gateway order stream max delivery attempts before poison routing"
  type        = number
  default     = 8

  validation {
    condition = (
      var.redis_order_events_max_delivery_attempts >= 1 &&
      var.redis_order_events_max_delivery_attempts <= 100
    )
    error_message = "redis_order_events_max_delivery_attempts must be in [1,100]."
  }
}

variable "redis_order_events_poison_stream_key" {
  description = "Gateway order stream poison stream key"
  type        = string
  default     = "cerberus.order.events.poison"
}

variable "redis_order_events_poison_stream_maxlen" {
  description = "Gateway order stream poison stream maxlen"
  type        = number
  default     = 20000
}

variable "redis_order_events_pending_warn_threshold" {
  description = "Gateway order stream readiness warning threshold for pending backlog"
  type        = number
  default     = 2000
}

variable "redis_order_events_lag_warn_threshold" {
  description = "Gateway order stream readiness warning threshold for lag"
  type        = number
  default     = 2000
}

variable "redis_orderbook_channel" {
  description = "Default orderbook channel"
  type        = string
  default     = "md.orderbook.BTCUSDT"
}

variable "redis_orderbook_channel_prefix" {
  description = "Orderbook channel prefix"
  type        = string
  default     = "md.orderbook"
}

variable "redis_tick_channel_prefix" {
  description = "Tick channel prefix"
  type        = string
  default     = "md.ticks"
}

variable "redis_market_events_stream_enabled" {
  description = "Enable gateway market events stream publishing"
  type        = bool
  default     = true
}

variable "redis_market_events_stream_key" {
  description = "Redis stream key for market events published by gateway"
  type        = string
  default     = "cerberus.market.events"
}

variable "redis_market_events_stream_maxlen" {
  description = "Approximate max length of market events stream"
  type        = number
  default     = 50000
}

variable "redis_market_events_publish_legacy_pubsub" {
  description = "Whether gateway still publishes market data to legacy pubsub channels"
  type        = bool
  default     = true
}

variable "market_stream_enabled" {
  description = "Enable strategy market stream consumer-group ingest path"
  type        = bool
  default     = true
}

variable "market_stream_consumer_group" {
  description = "Strategy market stream consumer group"
  type        = string
  default     = "strategy-market"
}

variable "market_stream_reclaim_enabled" {
  description = "Enable strategy market stream stale pending reclaim loop"
  type        = bool
  default     = true
}

variable "market_stream_reclaim_interval_ms" {
  description = "Strategy market stream reclaim interval in milliseconds"
  type        = number
  default     = 5000
}

variable "market_stream_reclaim_idle_ms" {
  description = "Strategy market stream minimum idle time before reclaim in milliseconds"
  type        = number
  default     = 30000
}

variable "market_stream_reclaim_batch_size" {
  description = "Strategy market stream reclaim batch size"
  type        = number
  default     = 64

  validation {
    condition = (
      var.market_stream_reclaim_batch_size >= 1 &&
      var.market_stream_reclaim_batch_size <= 1024
    )
    error_message = "market_stream_reclaim_batch_size must be in [1,1024]."
  }
}

variable "market_stream_max_delivery_attempts" {
  description = "Strategy market stream max delivery attempts before poison routing"
  type        = number
  default     = 8

  validation {
    condition = (
      var.market_stream_max_delivery_attempts >= 1 &&
      var.market_stream_max_delivery_attempts <= 100
    )
    error_message = "market_stream_max_delivery_attempts must be in [1,100]."
  }
}

variable "market_stream_pending_warn_threshold" {
  description = "Strategy readiness warning threshold for market stream pending backlog"
  type        = number
  default     = 2000
}

variable "market_stream_lag_warn_threshold" {
  description = "Strategy readiness warning threshold for market stream lag"
  type        = number
  default     = 2000
}

variable "market_stream_poison_stream_key" {
  description = "Strategy market stream poison stream key"
  type        = string
  default     = "cerberus.market.events.poison"
}

variable "market_stream_poison_stream_maxlen" {
  description = "Strategy market stream poison stream maxlen"
  type        = number
  default     = 20000
}

variable "market_stream_legacy_pubsub_fallback" {
  description = "Allow strategy to fallback to legacy pubsub when stream loop fails"
  type        = bool
  default     = true
}

variable "matching_execution_stream_limit" {
  description = "Maximum executions returned by matching stream/list query"
  type        = number
  default     = 500

  validation {
    condition     = var.matching_execution_stream_limit >= 1 && var.matching_execution_stream_limit <= 5000
    error_message = "matching_execution_stream_limit must be in [1,5000]."
  }
}

variable "matching_grpc_max_pollers" {
  description = "Matching gRPC sync server max pollers"
  type        = number
  default     = 16

  validation {
    condition     = var.matching_grpc_max_pollers >= 1 && var.matching_grpc_max_pollers <= 256
    error_message = "matching_grpc_max_pollers must be in [1,256]."
  }
}

variable "matching_grpc_min_pollers" {
  description = "Matching gRPC sync server min pollers"
  type        = number
  default     = 4

  validation {
    condition     = var.matching_grpc_min_pollers >= 1 && var.matching_grpc_min_pollers <= 256
    error_message = "matching_grpc_min_pollers must be in [1,256]."
  }
}

variable "matching_grpc_num_cqs" {
  description = "Matching gRPC sync server completion queues"
  type        = number
  default     = 4

  validation {
    condition     = var.matching_grpc_num_cqs >= 1 && var.matching_grpc_num_cqs <= 256
    error_message = "matching_grpc_num_cqs must be in [1,256]."
  }
}

variable "matching_submit_latency_window_size" {
  description = "Rolling sample size for matching submit latency P95"
  type        = number
  default     = 1024

  validation {
    condition = (
      var.matching_submit_latency_window_size >= 16 &&
      var.matching_submit_latency_window_size <= 200000
    )
    error_message = "matching_submit_latency_window_size must be in [16,200000]."
  }
}

variable "matching_max_inflight_requests" {
  description = "Matching gRPC max in-flight request budget before backpressure kicks in"
  type        = number
  default     = 1024

  validation {
    condition = (
      var.matching_max_inflight_requests >= 1 &&
      var.matching_max_inflight_requests <= 100000
    )
    error_message = "matching_max_inflight_requests must be in [1,100000]."
  }
}

variable "matching_inflight_acquire_timeout_ms" {
  description = "Matching gRPC max queue wait time for in-flight budget in milliseconds"
  type        = number
  default     = 30

  validation {
    condition = (
      var.matching_inflight_acquire_timeout_ms >= 1 &&
      var.matching_inflight_acquire_timeout_ms <= 10000
    )
    error_message = "matching_inflight_acquire_timeout_ms must be in [1,10000]."
  }
}

variable "internal_services_ingress" {
  description = "Restrict strategy and matching Cloud Run ingress to internal traffic only"
  type        = bool
  default     = true
}

variable "strategy_public_access" {
  description = "Expose strategy service publicly via allUsers invoker"
  type        = bool
  default     = false
}

variable "matching_public_access" {
  description = "Expose matching service publicly via allUsers invoker"
  type        = bool
  default     = false
}

variable "gateway_public_access" {
  description = "Expose gateway service publicly via allUsers invoker"
  type        = bool
  default     = true
}

variable "cloud_run_gateway" {
  description = "Gateway Cloud Run runtime/capacity profile"
  type = object({
    min_instance_count               = number
    max_instance_count               = number
    max_instance_request_concurrency = number
    timeout_seconds                  = number
    cpu                              = string
    memory                           = string
    cpu_idle                         = bool
    startup_cpu_boost                = bool
  })
  default = {
    min_instance_count               = 1
    max_instance_count               = 30
    max_instance_request_concurrency = 80
    timeout_seconds                  = 900
    cpu                              = "1"
    memory                           = "1Gi"
    cpu_idle                         = false
    startup_cpu_boost                = true
  }

  validation {
    condition     = var.cloud_run_gateway.max_instance_count >= var.cloud_run_gateway.min_instance_count
    error_message = "cloud_run_gateway.max_instance_count must be >= min_instance_count."
  }

  validation {
    condition = (
      var.cloud_run_gateway.max_instance_request_concurrency >= 1 &&
      var.cloud_run_gateway.max_instance_request_concurrency <= 1000 &&
      var.cloud_run_gateway.timeout_seconds >= 1 &&
      var.cloud_run_gateway.timeout_seconds <= 3600
    )
    error_message = "cloud_run_gateway concurrency must be [1,1000] and timeout_seconds must be [1,3600]."
  }
}

variable "cloud_run_strategy" {
  description = "Strategy Cloud Run runtime/capacity profile"
  type = object({
    min_instance_count               = number
    max_instance_count               = number
    max_instance_request_concurrency = number
    timeout_seconds                  = number
    cpu                              = string
    memory                           = string
    cpu_idle                         = bool
    startup_cpu_boost                = bool
  })
  default = {
    min_instance_count               = 1
    max_instance_count               = 20
    max_instance_request_concurrency = 20
    timeout_seconds                  = 300
    cpu                              = "2"
    memory                           = "2Gi"
    cpu_idle                         = false
    startup_cpu_boost                = true
  }

  validation {
    condition     = var.cloud_run_strategy.max_instance_count >= var.cloud_run_strategy.min_instance_count
    error_message = "cloud_run_strategy.max_instance_count must be >= min_instance_count."
  }

  validation {
    condition = (
      var.cloud_run_strategy.max_instance_request_concurrency >= 1 &&
      var.cloud_run_strategy.max_instance_request_concurrency <= 1000 &&
      var.cloud_run_strategy.timeout_seconds >= 1 &&
      var.cloud_run_strategy.timeout_seconds <= 3600
    )
    error_message = "cloud_run_strategy concurrency must be [1,1000] and timeout_seconds must be [1,3600]."
  }
}

variable "cloud_run_matching" {
  description = "Matching Cloud Run runtime/capacity profile"
  type = object({
    min_instance_count               = number
    max_instance_count               = number
    max_instance_request_concurrency = number
    timeout_seconds                  = number
    cpu                              = string
    memory                           = string
    cpu_idle                         = bool
    startup_cpu_boost                = bool
  })
  default = {
    min_instance_count               = 1
    max_instance_count               = 20
    max_instance_request_concurrency = 16
    timeout_seconds                  = 120
    cpu                              = "2"
    memory                           = "2Gi"
    cpu_idle                         = false
    startup_cpu_boost                = true
  }

  validation {
    condition     = var.cloud_run_matching.max_instance_count >= var.cloud_run_matching.min_instance_count
    error_message = "cloud_run_matching.max_instance_count must be >= min_instance_count."
  }

  validation {
    condition = (
      var.cloud_run_matching.max_instance_request_concurrency >= 1 &&
      var.cloud_run_matching.max_instance_request_concurrency <= 1000 &&
      var.cloud_run_matching.timeout_seconds >= 1 &&
      var.cloud_run_matching.timeout_seconds <= 3600
    )
    error_message = "cloud_run_matching concurrency must be [1,1000] and timeout_seconds must be [1,3600]."
  }
}
