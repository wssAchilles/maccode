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

export type ExecutionLifecyclePhase =
  | 'submit'
  | 'accepted'
  | 'rejected'
  | 'partial_fill'
  | 'fill'
  | 'cancel_requested'
  | 'canceled'

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
  client_order_id?: string
  execution_id?: string
  status?: string
  request_id?: string
  side?: string
  reason?: string
  price?: number
  quantity?: number
  filled_quantity?: number
  lifecycle_phase: ExecutionLifecyclePhase
  correlation_key: string
}

export type Candle = [number, string, string, string, string, string]

export type StrategySignal = {
  status: 'warmup' | 'ready'
  signal: string
  confidence: number
  symbol?: string
  strategy_id?: string
  engine?: string
  decision_source?: string
  dispatch_state?: string
  inference_mode?: string
  signal_id?: string
  strategy_basket?: StrategyDecisionContribution[]
  portfolio?: PortfolioSignalSummary
  strategy_registry?: StrategyRegistrySummary
}

export type StrategyDecisionContribution = {
  strategy_id: string
  label: string
  engine: string
  signal: string
  confidence: number
  weight: number
  priority: number
  role: string
  active: boolean
  source: string
  reason?: string | null
  metadata: Record<string, unknown>
}

export type PortfolioSignalSummary = {
  symbol: string
  dominant_signal: string
  final_signal: string
  final_source: string
  signal_bias: string
  consensus_level: string
  execution_ready: boolean
  execution_gate: string
  execution_gate_reason: string
  lead_strategy_id?: string | null
  lead_strategy_label?: string | null
  aligned_count: number
  contested_count: number
  agreement_ratio?: number | null
  weighted_score: number
  active_strategy_count: number
  tracked_symbols: string[]
  updated_at?: string | null
  latest_price?: number | null
}

export type StrategyRegistryEntry = {
  strategy_id: string
  label: string
  engine: string
  source: string
  role: string
  enabled: boolean
  priority: number
  configured_weight: number
  effective_weight: number
  symbol_coverage: string[]
  conflict_policy: string
  downgrade_policy: string
  metadata: Record<string, unknown>
}

export type StrategyRegistrySummary = {
  symbol: string
  tracked_symbols: string[]
  conflict_policy: string
  downgrade_policy: string
  entries: StrategyRegistryEntry[]
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
    forwarded_executions: number
    last_execution_id: number
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

export type InferenceAuditEvent = {
  event_type: string
  created_at: string
  message: string
  metadata: Record<string, unknown>
}

export type InferenceSymbolComparison = {
  symbol: string
  compared_ticks: number
  agreement_count: number
  divergence_count: number
  agreement_ratio?: number | null
}

export type InferenceComparisonPayload = {
  observed_ticks: number
  compared_ticks: number
  agreement_count: number
  divergence_count: number
  agreement_ratio?: number | null
  rule_signal_counts: Record<string, number>
  inference_signal_counts: Record<string, number>
  symbols: InferenceSymbolComparison[]
}

export type InferenceRolloutPayload = {
  configured_mode: string
  target_mode: string
  effective_mode: string
  override_active: boolean
  auto_promote_enabled: boolean
  force_primary: boolean
  promotion_eligible: boolean
  state_backend?: string | null
  state_restored?: boolean
  last_persisted_at?: string
  blockers: string[]
  required_observe_ticks: number
  compared_ticks: number
  required_agreement_ratio: number
  agreement_ratio?: number | null
  required_macro_f1: number
  current_macro_f1?: number | null
  started_at: string
  last_transition_at: string
}

export type InferenceStatusPayload = {
  enabled: boolean
  ready: boolean
  engine: string
  mode: string
  reason?: string | null
  metadata: Record<string, unknown>
  active_model?: InferenceModelDescriptor | null
  rollout?: InferenceRolloutPayload
  comparison?: InferenceComparisonPayload
  audit?: InferenceAuditEvent[]
}

export type InferenceCatalogResponse = {
  count: number
  active_model?: InferenceModelDescriptor | null
  models: InferenceModelDescriptor[]
}

export type InferenceControlResult = {
  accepted: boolean
  action: string
  message: string
  actor?: string | null
  reason?: string | null
  requested_mode?: string | null
  selected_model?: InferenceModelDescriptor | null
  active_model?: InferenceModelDescriptor | null
  rollout?: InferenceRolloutPayload
  comparison?: InferenceComparisonPayload
  audit?: InferenceAuditEvent[]
  models?: InferenceModelDescriptor[]
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
