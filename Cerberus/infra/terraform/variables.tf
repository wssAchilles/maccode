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
}

variable "strategy_internal_auth_metadata_identity_url" {
  description = "Metadata identity endpoint used by gateway to mint internal auth token"
  type        = string
  default     = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
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

variable "market_stream_legacy_pubsub_fallback" {
  description = "Allow strategy to fallback to legacy pubsub when stream loop fails"
  type        = bool
  default     = true
}

variable "matching_execution_stream_limit" {
  description = "Maximum executions returned by matching stream/list query"
  type        = number
  default     = 500
}

variable "matching_grpc_max_pollers" {
  description = "Matching gRPC sync server max pollers"
  type        = number
  default     = 16
}

variable "matching_grpc_min_pollers" {
  description = "Matching gRPC sync server min pollers"
  type        = number
  default     = 4
}

variable "matching_grpc_num_cqs" {
  description = "Matching gRPC sync server completion queues"
  type        = number
  default     = 4
}

variable "matching_submit_latency_window_size" {
  description = "Rolling sample size for matching submit latency P95"
  type        = number
  default     = 1024
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
