export type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
  meta: Record<string, unknown>;
};

export type Summary = {
  raw_rows: number;
  cleaned_rows: number;
  removed_rows: number;
  duplicate_rows: number;
  invalid_price_rows: number;
  missing_brand_rows: number;
  unique_users: number;
  unique_sessions: number;
  total_sales: number;
};

export type NamedValue = {
  name: string;
  value: number;
  orders?: number;
};

export type DateValue = {
  date: string;
  value: number;
};

export type DashboardSliceFilters = {
  event_type?: string;
  category_level1?: string;
  brand?: string;
};

export type DashboardSliceEvidence = {
  source_dataset: string;
  filtered_row_count: number;
  total_row_count: number;
  coverage_rate: number;
  query_ms: number;
  run_id: string;
  contract_version: string;
  dataset_version: string;
  generated_at: string;
  refreshed_at?: string;
  spark_duration?: number | null;
  cache_mode?: string;
  cache_hit?: boolean;
  fallback_reason?: string | null;
  cube_path?: string | null;
  cube_paths?: Record<string, string> | null;
  cube_row_count?: number | null;
  semantic_version?: string | null;
  metric_grain?: string | null;
  metric_definitions?: MetricDefinition[];
  filters: DashboardSliceFilters;
};

export type MetricDefinition = {
  contract_version?: string;
  run_id?: string;
  metric_name: string;
  chinese_name?: string;
  grain?: string;
  source?: string;
  refresh_frequency?: string;
  aggregation?: string;
  formula?: string;
  quality_assertions?: string[];
};

export type DashboardSlice = {
  summary: {
    event_count: number;
    purchase_count: number;
    total_sales: number;
    unique_users: number;
    unique_sessions: number;
    avg_order_value: number;
  };
  event_type_count: NamedValue[];
  daily_events: DateValue[];
  daily_sales: DateValue[];
  top_categories: NamedValue[];
  evidence: DashboardSliceEvidence;
};

export type ControlledQueryIntent = {
  metric: string;
  metric_label: string;
  dimension: string;
  dimension_label: string;
  aggregation: string;
  chart_type: string;
  limit: number;
  time_grain?: string | null;
  event_type_filter?: string | null;
  event_type_filter_label?: string | null;
};

export type ControlledQueryRow = {
  name: string;
  raw_name?: string | number | null;
  value: number;
  share: number;
};

export type ControlledQueryChart = {
  type: 'line' | 'bar' | 'horizontal_bar' | 'empty' | string;
  title: string;
  x_field: string;
  y_field: string;
  series_name: string;
  dimension_label: string;
  metric_label: string;
};

export type ControlledQueryEvidence = {
  source_dataset: string;
  run_id: string;
  contract_version: string;
  dataset_version: string;
  generated_at?: string | null;
  query_ms: number;
  row_count: number;
  execution_engine: string;
  cache_mode?: string | null;
  cache_hit?: boolean | null;
  semantic_version?: string | null;
  metric_grain?: string | null;
};

export type ControlledQueryResult = {
  contract_version: string;
  query: string;
  status: 'matched' | 'unsupported' | string;
  matched: boolean;
  message: string;
  confidence: number;
  intent: ControlledQueryIntent | null;
  chart: ControlledQueryChart;
  rows: ControlledQueryRow[];
  suggestions: string[];
  insight: string;
  evidence: ControlledQueryEvidence;
};

export type FunnelStep = {
  step: string;
  sessions: number;
  rate_from_previous: number;
};

export type SessionFunnel = {
  totals: {
    sessions: number;
    view_sessions: number;
    cart_sessions: number;
    purchase_sessions: number;
    view_to_cart_rate: number;
    cart_to_purchase_rate: number;
    view_to_purchase_rate: number;
    avg_purchase_latency_minutes: number;
    revenue: number;
    avg_order_value: number;
  };
  steps: FunnelStep[];
};

export type DailyConversion = {
  date: string;
  sessions: number;
  purchase_sessions: number;
  view_to_purchase_rate: number;
  revenue: number;
};

export type ProductConversion = {
  product_id: string;
  brand: string;
  category_level1: string;
  views: number;
  carts: number;
  purchases: number;
  view_to_cart_rate: number;
  cart_to_purchase_rate: number;
  revenue: number;
};

export type JourneySummary = {
  contract_version: string;
  run_id: string;
  sessions: number;
  unique_paths: number;
  purchase_sessions: number;
  cart_sessions: number;
  purchase_path_rate: number;
  cart_path_rate: number;
  revenue: number;
  avg_steps: number;
  avg_duration_seconds: number;
  top_path: JourneyPath | null;
  top_exit_event: JourneyExitEvent | null;
  top_transition: JourneyTransition | null;
  recommended_action: string;
};

export type JourneyPath = {
  path_signature: string;
  sessions: number;
  cart_sessions: number;
  purchase_sessions: number;
  revenue: number;
  avg_steps: number;
  avg_duration_seconds: number;
  conversion_rate: number;
  cart_rate: number;
};

export type JourneyTransition = {
  contract_version: string;
  from_event: string;
  to_event: string;
  transitions: number;
  sessions: number;
  purchase_sessions: number;
  revenue: number;
  conversion_rate: number;
  dropoff_hint: string;
};

export type JourneyExitEvent = {
  last_event: string;
  sessions: number;
  purchase_sessions: number;
  revenue: number;
  avg_steps: number;
  exit_share: number;
  purchase_rate: number;
};

export type JourneyPurchasePath = {
  path_signature: string;
  purchase_sessions: number;
  revenue: number;
  avg_steps: number;
  avg_duration_seconds: number;
};

export type ForecastingSummary = {
  contract_version: string;
  run_id: string;
  input_snapshot: Record<string, unknown>;
  forecast_horizon_days: number;
  training_window_days: number;
  backtest_window_days: number;
  history_days: number;
  driver_history_rows: number;
  max_driver_history_rows: number;
  history_range: {
    min_dt: string | null;
    max_dt: string | null;
  };
  entity_count: number;
  site_forecast_gmv: number;
  site_forecast_purchase_count: number;
  risk_count: number;
  high_risk_count: number;
  quality_status: string;
  top_risk: ForecastingRisk | null;
  recommended_action: string;
};

export type ForecastingSeriesPoint = {
  contract_version: string;
  dt: string;
  scope: string;
  entity_key: string;
  entity_label: string;
  metric: string;
  forecast_value: number;
  lower_bound: number;
  upper_bound: number;
  history_days: number;
  model_name: string;
  fallback_reason: string;
};

export type ForecastingEntity = {
  contract_version: string;
  scope: string;
  entity_key: string;
  entity_label: string;
  forecast_gmv: number;
  forecast_purchase_count: number;
  recent_gmv: number;
  expected_change_rate: number;
  history_days: number;
  risk_level: string;
  risk_score: number;
  model_name: string;
  fallback_reason: string;
  recommended_action: string;
};

export type ForecastingBacktestPoint = {
  contract_version: string;
  dt: string;
  scope: string;
  entity_key: string;
  entity_label: string;
  metric: string;
  actual: number;
  forecast: number;
  absolute_error: number;
  error: number;
  horizon?: number;
  model_name: string;
};

export type ForecastingEvaluationMetric = {
  group?: string;
  window_days?: number;
  rows: number;
  actual_sum?: number;
  forecast_sum?: number;
  wape: number | null;
  bias: number | null;
  mae?: number | null;
};

export type ForecastingEvaluation = {
  contract_version: string;
  run_id: string;
  windows: number[];
  model_metrics: ForecastingEvaluationMetric[];
  horizon_metrics: ForecastingEvaluationMetric[];
  window_metrics: ForecastingEvaluationMetric[];
  error_distribution: {
    max_absolute_error: number;
    avg_absolute_error: number;
    backtest_rows: number;
  };
  quality_gates: QualityCheck[];
};

export type ForecastingRisk = {
  contract_version: string;
  risk_id: string;
  scope: string;
  entity_key: string;
  entity_label: string;
  severity: string;
  risk_type: string;
  metric: string;
  evidence: {
    expected_change_rate?: number;
    history_days?: number;
    forecast_gmv?: number;
    [key: string]: unknown;
  };
  recommended_action: string;
};

export type ForecastingQuality = {
  contract_version: string;
  passed: boolean;
  quality_status: string;
  checks: Array<{
    name: string;
    actual: number | string | boolean | null;
    operator: string;
    expected: number | string | boolean | null;
    passed: boolean;
  }>;
  metrics: {
    site_history_days?: number;
    site_wape?: number | null;
    site_bias?: number | null;
    backtest_rows?: number;
    sparse_history?: boolean;
    [key: string]: unknown;
  };
};

export type AffinitySummary = {
  contract_version: string;
  run_id: string;
  input_snapshot: Record<string, unknown>;
  node_count: number;
  edge_count: number;
  community_count: number;
  opportunity_count: number;
  eligible_session_count: number;
  min_support: number;
  quality_status: string;
  sparse_graph: boolean;
  strongest_edge: AffinityEdge | null;
  top_opportunity: AffinityOpportunity | null;
  recommended_action: string;
};

export type AffinityNode = {
  contract_version: string;
  entity_id: string;
  entity_type: string;
  entity_label: string;
  brand: string;
  category_level1: string;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  degree: number;
  weighted_degree: number;
  community_id: string;
};

export type AffinityEdge = {
  contract_version: string;
  source_id: string;
  target_id: string;
  source_type: string;
  target_type: string;
  source_label: string;
  target_label: string;
  source_brand: string;
  target_brand: string;
  source_category: string;
  target_category: string;
  relation_type: string;
  support: number;
  confidence: number;
  lift: number;
  jaccard: number;
  revenue_overlap: number;
  sample_sessions: number;
  quality_status: string;
};

export type AffinityCommunity = {
  contract_version: string;
  community_id: string;
  category_level1: string;
  node_count: number;
  edge_count: number;
  revenue: number;
  top_entities: string[];
  recommended_action: string;
};

export type AffinityOpportunity = {
  contract_version: string;
  opportunity_id: string;
  type: string;
  primary_entity: string;
  primary_label: string;
  related_entity: string;
  related_label: string;
  reason_codes: string[];
  estimated_revenue_pool: number;
  confidence: number;
  lift: number;
  support: number;
  risk_level: string;
  action: string;
};

export type AffinityCentrality = {
  contract_version: string;
  entity_id: string;
  entity_label: string;
  brand: string;
  category_level1: string;
  community_id: string;
  degree: number;
  weighted_degree: number;
  normalized_weighted_degree: number;
  pagerank_score: number;
  centrality_score: number;
  community_size: number;
  community_revenue: number;
  revenue: number;
  views: number;
  purchases: number;
};

export type AffinityQuality = {
  contract_version: string;
  quality_status: string;
  passed: boolean;
  session_count: number;
  eligible_session_count: number;
  edge_count: number;
  min_support: number;
  sparse_graph: boolean;
  warnings: string[];
  checks: Array<{
    name: string;
    actual: number | string | boolean | null;
    operator: string;
    expected: number | string | boolean | null;
    passed: boolean;
  }>;
};

export type CohortSummary = {
  contract_version: string;
  run_id: string;
  input_snapshot: Record<string, unknown>;
  cohort_unit: string;
  user_count: number;
  purchase_user_count: number;
  repeat_purchase_user_count: number;
  repeat_purchase_rate: number;
  median_days_to_second_purchase: string;
  avg_revenue_per_purchase_user: number;
  cohort_revenue: number;
  high_risk_cohort_count: number;
  quality_status: string;
  sparse_cohorts: string[];
  recommended_action: string;
};

export type CohortRetentionCell = {
  contract_version: string;
  cohort: string;
  period_index: number;
  cohort_users: number;
  active_users: number;
  purchase_users: number;
  retention_rate: number;
  repurchase_rate: number;
  revenue: number;
  quality_status: string;
};

export type CohortRepurchaseInterval = {
  contract_version: string;
  bucket: string;
  users: number;
  share: number;
  avg_revenue: number;
};

export type CohortValueCurve = {
  contract_version: string;
  cohort: string;
  period_index: number;
  revenue: number;
  cumulative_revenue: number;
  revenue_per_purchase_user: number;
  purchase_users: number;
};

export type CohortSegment = {
  contract_version: string;
  segment_id: string;
  cohort: string;
  category_level1: string;
  users: number;
  repeat_purchase_users: number;
  repeat_purchase_rate: number;
  revenue: number;
  risk_level: string;
  reason_codes: string[];
  recommended_action: string;
};

export type CohortQuality = {
  contract_version: string;
  quality_status: string;
  passed: boolean;
  history_days: number;
  cohort_count: number;
  min_cohort_users: number;
  sparse_cohorts: string[];
  warnings: string[];
  checks: Array<{
    name: string;
    actual: number | string | boolean | null;
    operator: string;
    expected: number | string | boolean | null;
    passed: boolean;
  }>;
};

export type PortfolioSummary = {
  contract_version: string;
  run_id: string;
  input_snapshot: Record<string, unknown>;
  quality_status: string;
  total_revenue: number;
  total_purchases: number;
  category_count: number;
  brand_count: number;
  price_band_count: number;
  warnings: string[];
  top_category: PortfolioCategoryMix | null;
  top_product_revenue_share: number;
  product_revenue_hhi: number;
  opportunity_count: number;
  recommended_action: string;
};

export type PortfolioCategoryMix = {
  contract_version: string;
  category_level1: string;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  avg_price: number | null;
  view_to_cart_rate: number | null;
  view_to_purchase_rate: number | null;
  cart_to_purchase_rate: number | null;
  revenue_share: number | null;
  purchase_share: number | null;
};

export type PortfolioBrandMix = {
  contract_version: string;
  category_level1: string;
  brand: string;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  avg_price: number | null;
  view_to_purchase_rate: number | null;
  revenue_share: number | null;
  purchase_share: number | null;
};

export type PortfolioPriceBand = {
  contract_version: string;
  category_level1: string;
  price_band: string;
  purchases: number;
  revenue: number;
  avg_price: number | null;
  revenue_share: number | null;
  purchase_share: number | null;
};

export type PortfolioProductConcentration = {
  contract_version: string;
  rank: number;
  product_id: string;
  category_level1: string;
  brand: string;
  purchases: number;
  revenue: number;
  revenue_share: number;
  purchase_share: number;
  hhi_contribution: number;
};

export type PortfolioOpportunity = {
  contract_version: string;
  opportunity_type: string;
  entity_type: string;
  entity_id: string;
  price_band: string | null;
  impact_score: number;
  confidence: number;
  views: number | null;
  purchases: number;
  revenue: number;
  reason_codes: string[];
};

export type PortfolioQuality = {
  contract_version: string;
  quality_status: string;
  passed: boolean;
  rows: number;
  purchase_rows: number;
  history_days: number;
  category_count: number;
  brand_count: number;
  valid_price_purchase_rate: number;
  price_band_count: number;
  warnings: string[];
  checks: Array<{
    name: string;
    actual: number | string | boolean | null;
    operator: string;
    expected: number | string | boolean | null;
    passed: boolean;
  }>;
};

export type CartSummary = {
  contract_version: string;
  run_id: string;
  quality_status: string;
  configured_input_path: string;
  actual_input_path: string;
  cart_product_sessions: number;
  abandoned_sessions: number;
  recovered_sessions: number;
  explicit_remove_sessions: number;
  cart_value: number;
  abandoned_value: number;
  abandonment_rate: number;
  recovery_rate: number;
  remove_rate: number;
  category_count: number;
  product_count: number;
  queue_count: number;
  warnings: string[];
};

export type CartCategorySegment = {
  contract_version: string;
  category_level1: string;
  cart_product_sessions: number;
  cart_events: number;
  remove_events: number;
  recovered_sessions: number;
  explicit_remove_sessions: number;
  abandoned_sessions: number;
  cart_value: number;
  abandoned_value: number;
  recovery_rate: number | null;
  abandonment_rate: number | null;
  remove_rate: number | null;
};

export type CartProductSegment = {
  contract_version: string;
  rank: number;
  product_id: string;
  category_level1: string;
  brand: string;
  cart_product_sessions: number;
  cart_events: number;
  remove_events: number;
  recovered_sessions: number;
  explicit_remove_sessions: number;
  abandoned_sessions: number;
  avg_price: number | null;
  abandoned_value: number;
  recovery_rate: number | null;
  abandonment_rate: number | null;
  remove_rate: number | null;
  priority_score: number;
};

export type CartRecoveryQueueItem = {
  contract_version: string;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  recovery_action: string;
  priority_score: number;
  confidence: number;
  cart_product_sessions: number;
  abandoned_sessions: number;
  abandoned_value: number;
  abandonment_rate: number | null;
  remove_rate: number | null;
  reason_codes: string[];
};

export type CartQuality = {
  contract_version: string;
  quality_status: string;
  cart_event_rows: number;
  remove_event_rows: number;
  cart_product_sessions: number;
  history_days: number;
  min_cart_sessions: number;
  min_history_days: number;
  warnings: string[];
};

export type AttributionSummary = {
  contract_version: string;
  run_id: string;
  quality_status: string;
  configured_input_path: string;
  actual_input_path: string;
  purchase_rows: number;
  purchase_sessions: number;
  attributable_sessions: number;
  attributable_purchases: number;
  attribution_coverage_rate: number;
  total_purchase_revenue: number;
  assisted_revenue: number;
  avg_touchpoints_before_purchase: number;
  avg_minutes_before_purchase: number;
  multi_touch_purchase_rate: number;
  entity_count: number;
  assist_opportunity_count: number;
  warnings: string[];
};

export type AttributionModel = {
  contract_version: string;
  entity_type: string;
  entity_count: number;
  first_touch_revenue: number;
  last_touch_revenue: number;
  linear_assisted_revenue: number;
  time_decay_assisted_revenue: number;
  direct_revenue: number;
};

export type AttributionEntity = {
  contract_version: string;
  rank: number;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  touch_sessions: number;
  assisted_purchase_sessions: number;
  direct_purchase_sessions: number;
  first_touch_revenue: number;
  last_touch_revenue: number;
  linear_assisted_revenue: number;
  time_decay_assisted_revenue: number;
  direct_revenue: number;
  assist_to_direct_ratio: number | null;
  assist_rate: number | null;
  avg_position_before_purchase: number | null;
  avg_minutes_before_purchase: number | null;
  cart_touchpoints: number;
  view_touchpoints: number;
  remove_negative_signal_count: number;
  confidence: number;
  reason_codes: string[] | null;
};

export type AttributionPath = {
  contract_version: string;
  path_pattern: string;
  sessions: number;
  purchase_sessions: number;
  revenue: number;
  conversion_rate: number | null;
  median_latency_minutes: number | null;
  sample_size: number;
};

export type AttributionAssist = {
  contract_version: string;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  suggested_action: string;
  priority_score: number;
  confidence: number;
  time_decay_assisted_revenue: number;
  linear_assisted_revenue: number;
  direct_revenue: number;
  assist_to_direct_ratio: number | null;
  assisted_purchase_sessions: number;
  touch_sessions: number;
  reason_codes: string[] | null;
};

export type AttributionQuality = {
  contract_version: string;
  quality_status: string;
  purchase_rows: number;
  purchase_sessions: number;
  attributable_sessions: number;
  attribution_coverage_rate: number;
  session_missing_rate: number;
  valid_purchase_price_rate: number;
  history_days: number;
  warnings: string[];
};

export type OptimizationSummary = {
  contract_version: string;
  solver_status: string;
  message?: string;
  objective_value: number;
  runtime_seconds: number;
  optimality_gap: number | null;
  candidate_count: number;
  selected_count: number;
  total_budget: number;
  used_budget: number;
  budget_utilization: number;
  slot_count: number;
  used_slots: number;
  slot_utilization: number;
  expected_incremental_gmv: number;
  expected_incremental_purchases: number;
  average_risk_score: number;
  category_allocation: Record<string, number>;
  action_allocation: Record<string, number>;
  causal_caveat: string;
};

export type OptimizationPlanItem = {
  product_id: string;
  brand: string;
  category_level1: string;
  action: string;
  action_type: string;
  cost: number;
  expected_incremental_gmv: number;
  expected_incremental_purchases: number;
  objective_contribution: number;
  confidence_weight: number;
  risk_score: number;
  views: number;
  purchases: number;
  baseline_gmv: number;
  avg_price: number;
};

export type OptimizationCandidate = {
  product_id: string;
  brand: string;
  category_level1: string;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  avg_price: number;
  purchase_rate_shrunk: number;
  confidence_weight: number;
  risk_score: number;
  baseline_gmv: number;
};

export type OptimizationQuality = {
  contract_version: string;
  candidate_count: number;
  selected_count: number;
  eligible_count: number;
  solver_status: string;
  budget_feasible: boolean;
  slot_feasible: boolean;
  category_cap: number;
  brand_cap: number;
  min_views: number;
  min_confidence: number;
};

export type RecommendationSummary = {
  contract_version: string;
  run_id: string;
  input_snapshot: InputSnapshot;
  feature_window: Record<string, unknown>;
  generated_at: string;
  recommendation_count: number;
  covered_sessions: number;
  coverage_rate: number;
  personalized_rate: number;
  fallback_rate: number;
  avg_confidence: number;
  avg_score: number;
  freshness_lag_minutes: number;
  quality_status: string;
  rollback_ready: boolean;
  active_snapshot_path: string;
  previous_snapshot_path: string;
};

export type RecommendationItem = {
  user_session: string;
  user_id: string;
  rank: number;
  product_id: string;
  brand: string;
  category_level1: string;
  score: number;
  confidence: number;
  reason_codes: string[];
  source: string;
  fallback_used: boolean;
};

export type RecommendationCandidate = {
  candidate_id: string;
  user_session: string;
  user_id: string;
  product_id: string;
  brand: string;
  category_level1: string;
  rank: number;
  candidate_source: string;
  recall_stage: string;
  candidate_stage: string;
  score: number;
  ranker_score: number;
  source_score: number;
  conversion_score: number;
  freshness_score: number;
  affinity_score: number;
  confidence: number;
  ranker_model: string;
  calibration_bucket: string;
  reason_codes: string[];
  fallback_used: boolean;
};

export type RecommendationQuality = {
  contract_version: string;
  recommendation_count: number;
  target_sessions: number;
  covered_sessions: number;
  coverage_rate: number;
  fallback_rate: number;
  personalized_rate: number;
  avg_confidence: number;
  freshness_lag_minutes: number;
  duplicate_recommendation_rate: number;
  invalid_product_rate: number;
  passed: boolean;
  checks: QualityCheck[];
};

export type RecommendationEvaluationMetric = {
  model_name: string;
  status: string;
  caveat?: string;
  evaluated_sessions?: number;
  predicted_items?: number;
  hit_count?: number;
  precision_at_k: number | null;
  recall_at_k: number | null;
  ndcg_at_k: number | null;
  catalog_coverage: number;
  fallback_rate: number;
};

export type RecommendationTopKCell = {
  model_name: string;
  user_session: string;
  rank: number;
  product_id: string;
  hit: boolean;
  source: string;
  score: number;
};

export type RecommendationEvaluation = {
  contract_version: string;
  run_id: string;
  top_k: number;
  split: {
    strategy: string;
    train_rows: number;
    holdout_rows: number;
    evaluated_sessions: number;
  };
  behavior_weights: Record<string, number>;
  model_metrics: RecommendationEvaluationMetric[];
  source_mix: Array<{ source: string; recommendations: number; share: number }>;
  topk_matrix: RecommendationTopKCell[];
  quality_gates: QualityCheck[];
};

export type RecommendationAlert = {
  severity: string;
  alert_code: string;
  metric: string;
  actual: number;
  threshold: number;
  message: string;
  recommended_action: string;
};

export type AnomalyAlert = {
  contract_version: string;
  run_id: string;
  dt: string | null;
  severity: string;
  alert_code: string;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  metric: string;
  actual: number | null;
  baseline: number | null;
  delta: number | null;
  delta_rate: number | null;
  robust_z: number | null;
  direction: string;
  message: string;
  recommended_action: string;
  incident_id?: string | null;
  baseline_mode?: string | null;
};

export type AnomalyIncident = {
  contract_version: string;
  incident_id: string;
  run_id: string;
  dt: string | null;
  severity: string;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  metric: string;
  alert_count: number;
  max_robust_z: number;
  impact_value: number;
  root_cause_contributions: Array<{
    dimension: string;
    value: string;
    metric: string;
    contribution: number;
    contribution_share: number;
    direction: string;
  }>;
  recommended_action: string;
};

export type AnomalyRootCause = {
  contract_version: string;
  incident_id: string;
  dt: string | null;
  severity: string;
  dimension: string;
  value: string;
  metric: string;
  contribution: number;
  contribution_share: number;
  direction: string;
};

export type AnomalyEvaluation = {
  contract_version: string;
  run_id: string;
  baseline: {
    seasonal_signal_count: number;
    seasonal_coverage_rate: number;
    min_seasonal_points: number;
    min_baseline_points: number;
  };
  incidents: {
    incident_count: number;
    critical_incidents: number;
    warning_incidents: number;
  };
  alert_budget: {
    anomaly_signal_count: number;
    signal_count: number;
    anomaly_rate: number;
    max_alerts: number;
  };
  quality_gates: QualityCheck[];
};

export type AnomalySummary = {
  contract_version: string;
  run_id: string;
  radar_status: string;
  alert_count: number;
  critical_count: number;
  warning_count: number;
  watch_count: number;
  signal_count: number;
  monitored_entities: number;
  monitored_days: number;
  critical_signal_count: number;
  warning_signal_count: number;
  watch_signal_count: number;
  max_robust_z: number;
  date_range: { min_dt?: string | null; max_dt?: string | null };
  feature_mart_quality_status: string;
  feature_mart_freshness_status: string;
  top_alert: AnomalyAlert | null;
};

export type AnomalyTimelinePoint = {
  dt: string;
  signal_count: number;
  critical_count: number;
  warning_count: number;
  watch_count: number;
  max_robust_z: number;
};

export type AnomalyRules = {
  contract_version: string;
  baseline: string;
  rules: Array<{ name: string; description?: string; threshold: number }>;
};

export type LifecycleSummary = {
  contract_version: string;
  run_id: string;
  snapshot_dt: string | null;
  user_count: number;
  purchase_count: number;
  revenue: number;
  at_risk_users: number;
  convert_intent_users: number;
  high_value_users: number;
  avg_recency_days: number;
  segment_count: number;
  top_segment: LifecycleSegment | null;
  rules: Record<string, number>;
};

export type LifecycleSegment = {
  lifecycle_segment: string;
  users: number;
  revenue: number;
  purchases: number;
  avg_recency_days: number;
};

export type LifecycleUser = {
  user_id: string;
  lifecycle_segment: string;
  risk_band: string;
  sessions: number;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  recency_days: number;
  preferred_category_level1: string | null;
  recommended_action: string;
};

export type LifecycleCategoryAffinity = {
  category_level1: string | null;
  users: number;
  user_revenue: number;
  user_purchases: number;
  category_revenue?: number | null;
  category_purchases?: number | null;
};

export type LifecycleRules = {
  contract_version: string;
  model: string;
  rules: Array<{ name: string; description?: string; threshold: number }>;
};

export type ExperimentSummary = {
  contract_version: string;
  run_id: string;
  experiment_count: number;
  assignment_rows: number;
  assigned_users: number;
  treatment_assignments: number;
  control_assignments: number;
  treatment_split: number;
  expected_incremental_gmv: number;
  expected_incremental_purchases: number;
  guardrail_status: string;
  recommendation_coverage: {
    recommendations: number;
    covered_sessions: number;
    fallback_items?: number;
    fallback_rate: number;
    avg_confidence: number;
  };
  optimization_selected_count: number;
  experiments: Array<{
    experiment_key: string;
    name: string;
    assigned_users: number;
    treatment_users: number;
    control_users: number;
    expected_incremental_gmv: number;
  }>;
  causal_caveat: string;
};

export type ExperimentCatalogItem = {
  contract_version: string;
  experiment_key: string;
  name: string;
  primary_metric: string;
  secondary_metric: string;
  target_rule: string;
  policy: string;
  expected_uplift_rate: number;
  status: string;
  measurement_window: string;
  guardrail_metrics: string[];
};

export type ExperimentAssignment = {
  contract_version: string;
  source_run_id: string;
  experiment_key: string;
  name: string;
  user_id: string;
  variant: string;
  assignment_bucket: number;
  lifecycle_segment: string;
  risk_band: string;
  preferred_category_level1: string | null;
  sessions: number;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  expected_uplift_rate?: number;
  expected_incremental_purchase_prob: number;
  expected_incremental_gmv: number;
  uplift_score?: number;
  policy: string;
  primary_metric: string;
};

export type ExperimentSegment = {
  experiment_key: string;
  lifecycle_segment: string;
  variant: string;
  users: number;
  observed_revenue: number;
  observed_purchases: number;
  expected_incremental_gmv: number;
  experiment_users: number;
  segment_share: number;
};

export type ExperimentGuardrails = {
  contract_version: string;
  status: string;
  checks: QualityCheck[];
  segment_imbalance: Array<{
    experiment_key: string;
    lifecycle_segment: string;
    treatment_users: number;
    control_users: number;
    imbalance: number;
  }>;
  recommended_action: string;
};

export type ExperimentResult = {
  contract_version: string;
  run_id: string;
  experiment_key: string;
  name: string;
  primary_metric: string;
  measurement_status: string;
  oec_metric: string;
  treatment_users: number;
  control_users: number;
  expected_treatment_ratio: number;
  observed_treatment_ratio: number;
  srm_chi_square: number;
  srm_p_value: number;
  srm_status: string;
  control_mean: number;
  treatment_mean: number;
  absolute_lift: number;
  relative_lift: number | null;
  standard_error: number | null;
  ci_low: number | null;
  ci_high: number | null;
  p_value: number | null;
  decision: string;
  variant_rows: Array<{
    variant: string;
    users: number;
    conversions: number;
    conversion_rate: number;
    purchases: number;
    views: number;
    carts: number;
    revenue: number;
    expected_incremental_gmv: number;
    avg_uplift_score: number;
  }>;
  causal_caveat: string;
};

export type ExperimentUplift = {
  contract_version: string;
  run_id: string;
  measurement_status: string;
  causal_valid: boolean;
  causal_caveat: string;
  summary: Array<{ experiment_key: string; auuc: number; qini_auc: number; decile_count: number }>;
  deciles: Array<{
    experiment_key: string;
    decile: number;
    treatment_users: number;
    control_users: number;
    treatment_conversion_rate: number;
    control_conversion_rate: number;
    uplift: number;
    cumulative_gain: number;
    avg_uplift_score: number;
  }>;
  quality_gates: QualityCheck[];
};

export type FeatureMartSummary = {
  contract_version: string;
  run_id: string;
  input_snapshot: InputSnapshot;
  date_range: { min_dt?: string | null; max_dt?: string | null };
  partitions: { expected: number; written: number; missing: string[] };
  freshness: {
    max_event_time?: string | null;
    freshness_lag_hours?: number | null;
    sla_status: string;
  };
  quality_status: string;
  raw_rows: number;
  cleaned_rows: number;
  deduped_event_rows: number;
};

export type FeatureMartFreshness = {
  contract_version: string;
  run_id: string;
  generated_at: string;
  min_event_time: string | null;
  max_event_time: string | null;
  watermark_time: string | null;
  late_rows: number;
  late_rate: number;
  affected_dates: string[];
  freshness_lag_hours: number | null;
  max_freshness_lag_hours: number;
  sla_status: string;
};

export type FeatureMartQuality = {
  contract_version: string;
  run_id: string;
  raw_rows: number;
  cleaned_rows: number;
  deduped_event_rows: number;
  duplicate_event_keys: number;
  duplicate_event_key_rate: number;
  invalid_event_type_rows: number;
  missing_user_rows: number;
  missing_product_rows: number;
  purchase_missing_or_invalid_price_rows: number;
  null_session_rows: number;
  quarantined_rows: number;
  quarantined_rate: number;
  quality_status: string;
  checks: QualityCheck[];
};

export type FeatureMartPartitionReport = {
  contract_version: string;
  run_id: string;
  expected: number;
  written: number;
  missing: string[];
  min_dt: string | null;
  max_dt: string | null;
  partitions: Array<{ dt: string; rows: number; status: string }>;
};

export type FeatureMartFeature = {
  contract_version: string;
  run_id: string;
  feature_name: string;
  chinese_name: string;
  grain: string;
  source: string;
  refresh_frequency: string;
  quality_assertions: string[];
  owner: string;
};

export type FeatureMartReadiness = {
  contract_version: string;
  run_id: string;
  status: string;
  ready_features: number;
  total_features: number;
  checks: QualityCheck[];
  features: Array<{
    feature_name: string;
    chinese_name: string;
    grain: string;
    status: string;
    failed_rules: string[];
    source: string;
  }>;
  lineage: Array<{ from: string; to: string; relation: string }>;
};

export type FeatureMartProduct = {
  dt: string;
  product_id: string;
  brand: string;
  category_level1: string;
  views: number;
  carts: number;
  purchases: number;
  unique_users: number;
  unique_sessions: number;
  revenue: number;
  avg_price: number | null;
  view_to_cart_rate: number | null;
  cart_to_purchase_rate: number | null;
  view_to_purchase_rate: number | null;
};

export type FeatureMartCategory = {
  dt: string;
  category_level1: string;
  views: number;
  carts: number;
  purchases: number;
  unique_users: number;
  revenue: number;
  avg_price: number | null;
  conversion_rate: number | null;
};

export type FeatureMartUser = {
  dt: string;
  user_id: string;
  sessions: number;
  views: number;
  carts: number;
  purchases: number;
  revenue: number;
  active_minutes: number | null;
  distinct_products: number;
  distinct_categories: number;
  preferred_category_level1: string | null;
};

export type TableRow = {
  event_time: string;
  event_type: string;
  product_id: string;
  category_id: string;
  category_code: string;
  category_level1: string;
  brand: string;
  price: string;
  user_id: string;
  user_session: string;
  source_dataset: string;
};

export type TableResult = {
  page: number;
  size: number;
  total: number;
  source_dataset: string;
  rows: TableRow[];
};

export type LiveWeatherCurrent = {
  city: string;
  latitude: number;
  longitude: number;
  timezone: string;
  fetched_at: string;
  source_status: string;
  current: {
    time?: string;
    temperature_2m?: number | null;
    relative_humidity_2m?: number | null;
    precipitation?: number | null;
    rain?: number | null;
    weather_code?: number | null;
    wind_speed_10m?: number | null;
  };
  current_units?: Record<string, string>;
};

export type LiveWeatherHourlyForecastRow = {
  time: string;
  temperature_2m?: number | null;
  relative_humidity_2m?: number | null;
  precipitation?: number | null;
  rain?: number | null;
  weather_code?: number | null;
  wind_speed_10m?: number | null;
};

export type LiveWeatherForecast = {
  city: string;
  latitude: number;
  longitude: number;
  timezone: string;
  fetched_at: string;
  source_status: string;
  horizon_hours: number;
  forecast_window_start?: string | null;
  forecast_window_end?: string | null;
  hourly: LiveWeatherHourlyForecastRow[];
  hourly_units?: Record<string, string>;
};

export type LiveWeatherSummary = {
  contract_version: string;
  run_id: string;
  city: string;
  time_grain: string;
  quality_status: string;
  source_status: string;
  weather_rows: number;
  ecommerce_agg_rows: number;
  joined_rows: number;
  join_coverage_rate: number;
  missing_weather_rate: number;
  ecommerce_date_range: { min: string | null; max: string | null };
  weather_date_range: { min: string | null; max: string | null };
  current_weather_used_for_training: boolean;
  warnings: string[];
  generated_at: string;
};

export type LiveTrainingStatus = {
  run_id: string;
  job_type: string;
  status: string;
  quality_status?: string;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  elapsed_seconds?: number | null;
  message?: string;
};

export type LiveTrainingMetricRow = {
  model_name: string;
  rows: number;
  wape: number | null;
  mae: number | null;
  actual_sum: number;
  absolute_error_sum: number;
};

export type LiveTrainingMetrics = {
  contract_version: string;
  run_id: string;
  generated_at: string;
  comparison_status: string;
  interpretation: string;
  model_metrics: LiveTrainingMetricRow[];
  lift: {
    wape_reduction: number | null;
    mae_reduction: number | null;
    improved: boolean;
  };
  quality_gates: QualityCheck[];
};

export type LiveWeatherImpactItem = {
  scope: string;
  entity_key: string;
  entity_label: string;
  impact_score: number;
  demand_multiplier: number;
  recommendation_weight: number;
  direction: string;
  reason: string;
};

export type LiveWeatherImpact = {
  contract_version: string;
  run_id: string;
  city: string;
  source_status: string;
  current_weather_time?: string;
  training_uses_current_weather: boolean;
  comparison_status?: string;
  current_weather: Record<string, number | null>;
  generated_at: string;
  items: LiveWeatherImpactItem[];
};

export type LiveWeatherForecastImpactCategory = {
  entity_key: string;
  entity_label: string;
  impact_score: number;
  demand_multiplier: number;
  direction: string;
  impact_components?: Record<string, number>;
  reason: string;
};

export type LiveWeatherForecastImpactRow = LiveWeatherHourlyForecastRow & {
  avg_impact_score: number;
  strongest_category?: string | null;
  strongest_impact_score?: number | null;
  category_impacts: LiveWeatherForecastImpactCategory[];
};

export type LiveWeatherForecastImpact = {
  contract_version: string;
  run_id: string;
  city: string;
  source_status: string;
  horizon_hours: number;
  generated_at: string;
  training_uses_forecast_weather: boolean;
  forecast_weather_time_range: { min: string | null; max: string | null };
  summary: {
    max_negative_hour?: string | null;
    max_negative_avg_impact_score?: number | null;
    max_positive_hour?: string | null;
    max_positive_avg_impact_score?: number | null;
    peak_abs_hour?: string | null;
    peak_abs_category?: string | null;
    peak_abs_impact_score?: number | null;
    dominant_driver?: string | null;
  };
  items: LiveWeatherForecastImpactRow[];
};

export type InputSnapshot = {
  configured_input_path?: string;
  actual_input_path?: string;
  input_format?: string;
  storage_mode?: string;
  file_count?: number;
  files?: string[];
};

export type QualityCheck = {
  name: string;
  actual: number | string | boolean | null;
  operator: string;
  expected: number | string | boolean | null;
  passed: boolean;
};

export type QualityReport = {
  metrics?: Record<string, number>;
  gate?: {
    status: 'passed' | 'failed' | 'not_evaluated';
    checks: QualityCheck[];
    thresholds: Record<string, number>;
  };
};

export type OutputArtifacts = {
  metrics_dir?: string;
  processed_dir?: string | null;
  manifest_path?: string;
  run_manifest_path?: string;
};

export type SparkHistoryMetrics = {
  spark_application_id?: string;
  spark_application_status?: string;
  failed_task_count?: number;
  retried_task_count?: number;
  shuffle_read_bytes?: number;
  shuffle_write_bytes?: number;
  memory_spill_bytes?: number;
  disk_spill_bytes?: number;
  executor_count?: number;
  executor_peak_memory_mb?: number;
  driver_peak_memory_mb?: number;
  [key: string]: string | number | null | undefined;
};

export type JobGovernanceStage = {
  stage: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
};

export type JobGovernanceArtifact = {
  artifact_id: string;
  artifact_type: string;
  path: string;
  exists: boolean;
  status: string;
  updated_at?: string | null;
  age_minutes?: number | null;
  size_bytes?: number | null;
  freshness_sla_minutes?: number;
  freshness_warning_minutes?: number;
};

export type JobGovernance = {
  contract_version: string;
  run_id: string;
  status: string;
  active_stage: string;
  completion_ratio: number;
  freshness_sla_minutes: number;
  freshness_warning_minutes: number;
  stage_counts: Record<string, number>;
  artifact_counts: Record<string, number>;
  stages: JobGovernanceStage[];
  artifacts: JobGovernanceArtifact[];
  spark_summary: SparkHistoryMetrics & {
    application_id?: string | null;
    application_status?: string | null;
    history_metrics_status?: string | null;
  };
  quality_summary: {
    status?: string | null;
    check_count?: number;
    passed_check_count?: number;
    failure_stage?: string | null;
  };
};

export type JobStatus = {
  job_id?: string;
  job_type?: string;
  status?: string;
  config_path?: string;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  message?: string;
  error?: string | null;
  elapsed_seconds?: number;
  input_path?: string;
  storage_mode?: string;
  run_id?: string | null;
  contract_version?: string | null;
  config_hash?: string | null;
  spark_application_id?: string | null;
  spark_application_status?: string | null;
  spark_history_metrics_status?: string | null;
  spark_history_metrics_error?: string | null;
  spark_history_metrics?: SparkHistoryMetrics | null;
  input_snapshot?: InputSnapshot | null;
  quality_status?: 'passed' | 'failed' | 'needs_review' | 'not_evaluated' | null;
  quality_report?: QualityReport | null;
  output_artifacts?: OutputArtifacts | null;
  failure_stage?: string | null;
  governance?: JobGovernance;
};

export type JobList = {
  total: number;
  rows: JobStatus[];
};

export type JobLineage = {
  job_id: string;
  run_id?: string | null;
  contract_version?: string | null;
  config_hash?: string | null;
  spark_application_id?: string | null;
  spark_application_status?: string | null;
  spark_history_metrics_status?: string | null;
  spark_history_metrics_error?: string | null;
  spark_history_metrics?: SparkHistoryMetrics | null;
  input_snapshot?: InputSnapshot | null;
  output_artifacts?: OutputArtifacts | null;
  governance?: JobGovernance;
};

export type JobQuality = {
  job_id: string;
  run_id?: string | null;
  spark_application_id?: string | null;
  spark_application_status?: string | null;
  spark_history_metrics_status?: string | null;
  spark_history_metrics_error?: string | null;
  spark_history_metrics?: SparkHistoryMetrics | null;
  quality_status?: 'passed' | 'failed' | 'needs_review' | 'not_evaluated' | null;
  quality_report?: QualityReport | null;
  failure_stage?: string | null;
  governance?: JobGovernance;
};

export type BenchmarkRun = {
  sample: string;
  variant: string;
  status: string;
  spark_application_id?: string | null;
  spark_application_status?: string | null;
  input_path?: string | null;
  input_rows?: number | null;
  output_rows?: number | null;
  elapsed_seconds?: number | null;
  rows_per_second?: number | null;
  quality_status?: string | null;
  driver_peak_memory_mb?: number | null;
  spark_history_metrics_status?: string | null;
  history_metrics?: SparkHistoryMetrics | null;
  task_count?: number | null;
  failed_task_count?: number | null;
  retried_task_count?: number | null;
  shuffle_read_bytes?: number | null;
  shuffle_write_bytes?: number | null;
  memory_spill_bytes?: number | null;
  disk_spill_bytes?: number | null;
  result_path: string;
};

export type ModuleBenchmarkRun = {
  profile?: string | null;
  task_name?: string | null;
  input_rows?: number | null;
  output_rows?: number | null;
  elapsed_seconds?: number | null;
  duration_seconds?: number | null;
  success?: boolean;
  spark_application_id?: string | null;
  driver_peak_memory_mb?: number | null;
  result_path: string;
};

export type EvidencePath = {
  sample?: string;
  name?: string;
  path: string;
  role?: string;
  size_bytes?: number;
  size_label?: string;
};

export type OpsEvidence = {
  benchmark_runs: BenchmarkRun[];
  module_benchmark_runs?: ModuleBenchmarkRun[];
  benchmark_summary: {
    one_pct_run_count?: number;
    five_pct_run_count?: number;
    fastest_1pct_variant?: string | null;
    yarn_only_to_aqe_speedup?: number | null;
    yarn_only_to_algorithm_speedup?: number | null;
    five_pct_algorithm_elapsed_seconds?: number | null;
    five_pct_parquet_elapsed_seconds?: number | null;
    interpretation?: string;
    [key: string]: string | number | null | undefined;
  };
  history_summary?: {
    collected_run_count?: number;
    failed_task_count?: number;
    retried_task_count?: number;
    shuffle_read_bytes?: number;
    shuffle_write_bytes?: number;
    memory_spill_bytes?: number;
    disk_spill_bytes?: number;
    collector?: string;
    [key: string]: string | number | undefined;
  };
  scale_boundary?: {
    policy?: string;
    full_oct_nov_status?: string;
    reason?: string;
    conclusion?: string;
    [key: string]: unknown;
  };
  cluster_mode?: {
    status?: string;
    deploy_mode?: string;
    config_path?: string;
    submit_script?: string;
    default_refresh_mode?: string;
    reason?: string;
    [key: string]: string | undefined;
  };
  hdfs_inputs: EvidencePath[];
  local_samples: EvidencePath[];
  cleanup_policy: {
    raw_data_preserved?: boolean;
    kept_benchmark_dirs?: string[];
    kept_spark_history_app_ids?: string[];
    [key: string]: string | boolean | string[] | undefined;
  };
};

export type OptimizationImpactTone = 'success' | 'warning' | 'danger' | 'running';

export type OptimizationImpactCard = {
  id: string;
  title: string;
  status: string;
  tone: OptimizationImpactTone;
  metric: string;
  detail: string;
  action: string;
};

export type OptimizationFrontendSection = {
  id: string;
  page: string;
  route: string;
  tone: OptimizationImpactTone;
  status: string;
  visible_result: string;
  source_cards: string;
};

export type OptimizationImpact = {
  generated_at: string;
  overall_status: string;
  overall_tone: OptimizationImpactTone;
  headline: string;
  summary: {
    success_count?: number;
    warning_count?: number;
    danger_count?: number;
    visible_page_count?: number;
    evidence_count?: number;
    primary_action?: string;
    [key: string]: string | number | undefined;
  };
  data_layers: OptimizationImpactCard[];
  quality_gates: OptimizationImpactCard[];
  model_cards: OptimizationImpactCard[];
  performance_cards: OptimizationImpactCard[];
  frontend_sections: OptimizationFrontendSection[];
};
