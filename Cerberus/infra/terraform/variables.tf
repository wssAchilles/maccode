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

variable "firebase_auth_required" {
  description = "Require Firebase ID token verification on protected gateway APIs"
  type        = bool
  default     = true
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
