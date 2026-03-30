export type LoadState = 'idle' | 'loading' | 'ready' | 'degraded' | 'error'

export type UIState = {
  state: LoadState
  last_update_ms: number | null
  stale: boolean
  reason?: string
  request_id?: string
}

export type AppError = {
  code: string
  message: string
  request_id?: string
}

export type Envelope<T> = {
  ok: boolean
  status_code: number
  url: string
  payload?: T
  error?: string | AppError
}

export type MarketMessage = {
  symbol: string
  bid_price: string
  ask_price: string
  event_time: number
}

export type OrderEvent = {
  channel: string
  payload: Record<string, unknown>
  received_at: number
}

export type OrderTimelineEvent = {
  id: string
  channel: string
  payload: Record<string, unknown>
  received_at: number
  event_time?: string
  event_type: string
  symbol?: string
  account_id?: string
  order_id?: string
  status?: string
  request_id?: string
}

export type Candle = [number, string, string, string, string, string]

export type StrategySignal = {
  status: 'warmup' | 'ready'
  signal: string
  confidence: number
  symbol?: string
}

export type SignalRecord = {
  strategy_id: string
  symbol: string
  signal: string
  confidence: number
  created_at: string
}

export type PersistenceStatus = {
  status: string
  worker: {
    processed_ticks: number
    last_tick_at?: string
    last_error?: string
    has_last_signal: boolean
    tracked_symbols?: string[]
    started?: boolean
    market_loop_running?: boolean
    execution_loop_running?: boolean
    redis_configured?: boolean
  }
  matching?: {
    health?: {
      enabled: boolean
      reachable: boolean
      status: string
      service: string
      version: string
      uptime_seconds: number
      request_id?: string
      reason?: string
    }
    stats?: {
      enabled: boolean
      live_orders: number
      trade_count: number
      tracked_orders: number
      rejected_orders: number
      symbols: number
      best_bid?: number | null
      best_ask?: number | null
      request_id?: string
    }
  }
  stores: {
    supabase_enabled: boolean
    firebase_enabled: boolean
    supabase_table: string
    firebase_collection: string
  }
}

export type MatchingOrderBookLevel = {
  price: number
  total_quantity: number
  order_count: number
}

export type MatchingOrderBook = {
  enabled: boolean
  symbol: string
  depth: number
  bids: MatchingOrderBookLevel[]
  asks: MatchingOrderBookLevel[]
  generated_at_ms: number
  request_id?: string
}

export type InferenceModelDescriptor = {
  model_id: string
  version: string
  source: string
  task: string
  symbols: string[]
  metadata: Record<string, unknown>
}

export type InferenceStatusPayload = {
  enabled: boolean
  ready: boolean
  engine: string
  mode: string
  reason?: string | null
  metadata: Record<string, unknown>
  active_model?: InferenceModelDescriptor | null
}

export type StrategySummaryResponse = {
  request_id: string
  strategy_base_url: string
  symbol: string
  source: string
  recent_limit: number
  orderbook_depth: number
  signal: Envelope<StrategySignal>
  recent_signals: Envelope<{ source: string; count: number; signals: SignalRecord[] }>
  persistence: Envelope<PersistenceStatus>
  matching_orderbook: Envelope<MatchingOrderBook>
  inference_status: Envelope<InferenceStatusPayload>
}

export type TradingPolicy = {
  enforced: boolean
  binance_allowed_symbols: string[]
  alpaca_allowed_symbols: string[]
  max_binance_order_qty?: number | null
  max_binance_order_notional_usd?: number | null
  max_alpaca_order_qty?: number | null
  max_alpaca_limit_notional_usd?: number | null
}

export type BinanceRule = {
  symbol: string
  min_notional?: number | null
  min_qty?: number | null
  step_size?: number | null
  tick_size?: number | null
  refreshed_at: number
}

export const DEFAULT_UI_STATE: UIState = {
  state: 'idle',
  last_update_ms: null,
  stale: true,
}
