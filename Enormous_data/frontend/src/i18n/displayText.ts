export type LabelDomain =
  | 'action'
  | 'attributionModel'
  | 'check'
  | 'direction'
  | 'entityType'
  | 'eventType'
  | 'frequency'
  | 'lineage'
  | 'metric'
  | 'model'
  | 'reason'
  | 'relation'
  | 'risk'
  | 'segment'
  | 'source'
  | 'status'
  | 'variant';

type LabelEntry = {
  label: string;
  raw?: string;
};

const dictionaries: Record<LabelDomain, Record<string, LabelEntry>> = {
  action: {
    'add_bundle_or_complete-the-look_slot': { label: '增加组合搭配位' },
    add_bundle_or_complete_the_look_slot: { label: '增加组合搭配位' },
    add_bundle_or_complete: { label: '增加组合搭配' },
    add_cross_sell_slot: { label: '增加交叉销售位' },
    add_substitute_recommendation_guardrail: { label: '增加替代推荐护栏' },
    category_merchandising_review: { label: '品类经营复核' },
    category_recovery_campaign: { label: '品类召回活动' },
    category_watch: { label: '品类观察' },
    concentration_risk: { label: '集中度风险' },
    feature_slot: { label: '推荐位加权' },
    monitor_assist_entity: { label: '监控辅助转化对象' },
    portfolio_watch: { label: '组合观察' },
    price_band_mix: { label: '价格带结构' },
    product_cart_abandonment: { label: '商品购物车流失' },
    promote_cart_assist_path: { label: '强化购物车辅助路径' },
    promo_mid: { label: '中等促销' },
    recovery_offer_or_reminder: { label: '优惠或提醒召回' },
    review_affinity_evidence: { label: '复核亲和关系证据' },
    test_cross_category_recommendation: { label: '测试跨品类推荐' },
    traffic_conversion_gap: { label: '流量转化缺口' },
    watch_cart_followup: { label: '观察跟进' },
  },
  attributionModel: {
    direct: { label: '直接归因' },
    first_touch: { label: '首次触点' },
    last_touch: { label: '末次触点' },
    linear: { label: '线性归因' },
    time_decay: { label: '时间衰减' },
  },
  check: {
    avg_confidence: { label: '平均置信度' },
    cleaned_rows: { label: '清洗后行数' },
    cohort_count: { label: '留存分群数' },
    coverage_rate: { label: '推荐覆盖率' },
    duplicate_event_key_rate: { label: '重复事件键比例' },
    duplicate_recommendation_rate: { label: '重复推荐比例' },
    driver_history_rows: { label: '驱动历史行数' },
    edge_count: { label: '图谱边数量' },
    event_key_deduped: { label: '事件键已去重' },
    eligible_session_count: { label: '有效会话数' },
    als_baseline_available: { label: '矩阵分解基线可用' },
    baseline_points_available: { label: '基线样本充足' },
    fallback_rate: { label: '兜底推荐占比' },
    freshness_lag_minutes: { label: '数据新鲜度延迟' },
    freshness_sla: { label: '新鲜度服务承诺' },
    history_days: { label: '历史天数' },
    incident_budget: { label: '异常事件预算' },
    invalid_price_rows: { label: '异常价格行数' },
    invalid_product_rate: { label: '非法商品比例' },
    insufficient_baseline: { label: '基线样本不足' },
    max_segment_variant_imbalance: { label: '分层实验组不均衡度' },
    min_assignment_users: { label: '最小分流用户数' },
    min_cleaned_rows: { label: '最小清洗行数' },
    min_cohort_users: { label: '最小分群用户数' },
    minimum_history_days: { label: '最小历史天数' },
    pair_rows_per_input_row: { label: '输入行配对膨胀率' },
    pair_rows_per_product_session: { label: '商品会话配对膨胀率' },
    partition_completeness: { label: '分区完整度' },
    partition_present: { label: '分区存在' },
    purchase_rows: { label: '购买行数' },
    ordering_anomaly_ratio: { label: '会话顺序异常比例' },
    purchase_missing_price_ratio: { label: '购买缺价比例' },
    quality_status: { label: '质量状态' },
    quarantined_rate: { label: '隔离数据比例' },
    recall_at_k_available: { label: '召回评估可用' },
    removed_ratio: { label: '清洗剔除比例' },
    site_wape: { label: '全站加权绝对百分比误差' },
    session_fact_rows: { label: '会话事实行数' },
    weekday_baseline_available: { label: '星期季节性基线可用' },
    weekday_seasonal_baseline: { label: '星期季节性基线' },
    zero_after_volume: { label: '有量后归零' },
    category_revenue_spike: { label: '类目成交额突增' },
    category_revenue_drop: { label: '类目成交额下降' },
    category_views_spike: { label: '类目浏览突增' },
    category_views_drop: { label: '类目浏览下降' },
    category_purchases_spike: { label: '类目购买突增' },
    category_purchases_drop: { label: '类目购买下降' },
    category_conversion_rate_spike: { label: '类目转化率突增' },
    category_conversion_rate_drop: { label: '类目转化率下降' },
    demand_drop: { label: '需求下降' },
    product_revenue_spike: { label: '商品成交额突增' },
    product_revenue_drop: { label: '商品成交额下降' },
    product_views_spike: { label: '商品浏览突增' },
    product_views_drop: { label: '商品浏览下降' },
    product_purchases_spike: { label: '商品购买突增' },
    product_purchases_drop: { label: '商品购买下降' },
    product_view_to_purchase_rate_spike: { label: '商品浏览购买转化突增' },
    product_view_to_purchase_rate_drop: { label: '商品浏览购买转化下降' },
    critical_robust_z: { label: '严重稳健分数阈值' },
    warning_robust_z: { label: '警告稳健分数阈值' },
    non_negative: { label: '非负约束' },
    between_0_and_1: { label: '比例范围约束' },
    causal_outcome_available: { label: '因果结果数据可用' },
    min_control_assignments: { label: '最小对照组样本' },
    min_treatment_assignments: { label: '最小实验组样本' },
    recommendation_avg_confidence: { label: '推荐平均置信度' },
  },
  direction: {
    drop: { label: '下降' },
    spike: { label: '突增' },
    increase: { label: '上升' },
    decrease: { label: '下降' },
    stable: { label: '稳定' },
  },
  entityType: {
    brand: { label: '品牌' },
    category: { label: '品类' },
    category_price_band: { label: '品类价格带' },
    product: { label: '商品' },
    site: { label: '全站' },
    user: { label: '用户' },
  },
  eventType: {
    cart: { label: '加购' },
    purchase: { label: '购买' },
    remove_from_cart: { label: '移出购物车' },
    view: { label: '浏览' },
  },
  frequency: {
    daily: { label: '每日刷新' },
    hourly: { label: '每小时刷新' },
    batch: { label: '批量刷新' },
  },
  lineage: {
    raw_events: { label: '原始行为日志' },
    raw_events_compatible_fallback: { label: '原始样本回退' },
    cleaned_events: { label: '清洗后事件' },
    dashboard_metric_cube: { label: '物化指标层' },
    dashboard_cube_total: { label: '物化汇总层' },
    dashboard_cube_daily: { label: '物化日级趋势' },
    daily_product_behavior: { label: '商品日级行为特征' },
    daily_category_behavior: { label: '类目日级行为特征' },
    feature_mart: { label: '特征集市' },
    recommendations_forecasting_anomaly: { label: '推荐、预测、异常算法' },
    clean_and_validate: { label: '清洗校验' },
    aggregate_daily_product: { label: '商品日聚合' },
    aggregate_daily_category: { label: '类目日聚合' },
    serve_downstream_algorithms: { label: '服务下游算法' },
  },
  metric: {
    actual: { label: '实际值' },
    actual_sum: { label: '实际合计' },
    avg_order_value: { label: '客单价' },
    baseline: { label: '基线' },
    bias: { label: '系统性偏差' },
    buyer_count: { label: '购买用户数' },
    carts: { label: '加购数' },
    cart_to_purchase_rate: { label: '加购到购买' },
    catalog_coverage: { label: '目录覆盖率' },
    candidate_count: { label: '候选数量' },
    centrality_score: { label: '中心性得分' },
    calibration_bucket: { label: '校准分层' },
    confidence: { label: '置信度' },
    control_mean: { label: '对照组均值' },
    conversion_rate: { label: '转化率' },
    conversion_score: { label: '转化分数' },
    cumulative_gain: { label: '累计增益' },
    evaluated_sessions: { label: '评估会话数' },
    event_count: { label: '事件量' },
    affinity_score: { label: '亲和分数' },
    fallback_rate: { label: '兜底推荐占比' },
    forecast: { label: '预测值' },
    forecast_sum: { label: '预测合计' },
    forecast_value: { label: '预测值' },
    freshness_lag_minutes: { label: '新鲜度延迟' },
    gmv: { label: '成交额' },
    hit_count: { label: '命中数' },
    incremental_gmv: { label: '增量成交额' },
    insufficient_history: { label: '历史不足' },
    lift: { label: '提升度' },
    lower_bound: { label: '下界' },
    mae: { label: '平均绝对误差' },
    max_absolute_error: { label: '最大绝对误差' },
    avg_absolute_error: { label: '平均绝对误差' },
    ndcg_at_k: { label: '排序增益@K' },
    observed_treatment_ratio: { label: '实验组实际占比' },
    pagerank_score: { label: 'PageRank 得分' },
    precision_at_k: { label: '精确率@K' },
    predicted_items: { label: '预测商品数' },
    purchase_count: { label: '购买数' },
    purchase_rate: { label: '购买率' },
    purchases: { label: '购买数' },
    qini_auc: { label: 'Qini 面积' },
    ranker_score: { label: '排序分数' },
    recall_at_k: { label: '召回率@K' },
    revenue: { label: '营收' },
    rows: { label: '样本行数' },
    score: { label: '评分' },
    sessions: { label: '会话数' },
    source_score: { label: '来源分数' },
    srm_p_value: { label: 'SRM 显著性' },
    support: { label: '支持度' },
    treatment_mean: { label: '实验组均值' },
    total_sales: { label: '成交额' },
    unique_sessions: { label: '去重会话数' },
    unique_users: { label: '去重用户数' },
    upper_bound: { label: '上界' },
    value: { label: '数值' },
    view_to_cart_rate: { label: '浏览到加购' },
    view_to_purchase_rate: { label: '浏览到购买' },
    views: { label: '浏览数' },
    wape: { label: '加权绝对百分比误差' },
  },
  model: {
    als_implicit: { label: '隐式反馈矩阵分解' },
    control_gate: { label: '控制门禁' },
    global_median_mad: { label: '全局中位数稳健基线' },
    rolling_baseline: { label: '滚动基线' },
    rolling_baseline_backtest: { label: '滚动基线回测' },
    rule_recommendation: { label: '规则推荐' },
    interpretable_rule_ranker_v1: { label: '可解释规则排序器' },
    spark_ml_logistic_ranker_v1: { label: 'Spark ML 逻辑回归排序器' },
    spark_ml_gbt_ranker_v1: { label: 'Spark ML 梯度提升树排序器' },
    sparse_baseline_fallback: { label: '稀疏基线回退' },
    weekday_baseline_backtest: { label: '星期季节性基线回测' },
    weekday_median_mad: { label: '星期季节性稳健基线' },
  },
  reason: {
    category_affinity: { label: '品类偏好' },
    cross_category: { label: '跨品类关系' },
    dashboard_cube_missing: { label: '物化指标层缺失' },
    dashboard_cube_unreadable: { label: '物化指标层不可读' },
    fallback_pressure: { label: '兜底压力' },
    high_conversion: { label: '高转化' },
    high_lift: { label: '高提升度' },
    graph_neighbor_recall: { label: '图谱邻居召回' },
    insufficient_history_days: { label: '历史天数不足' },
    low_repeat_purchase_rate: { label: '复购率偏低' },
    optimization_or_global_fallback: { label: '优化计划或全局兜底' },
    price_band_revenue_pool: { label: '价格带收入池' },
    category_cart_abandonment: { label: '品类购物车流失' },
    category_merchandising_review: { label: '品类经营复核' },
    concentration_risk: { label: '集中度风险' },
    contains_remove_signal: { label: '包含移出购物车信号' },
    multi_touch_driver: { label: '多触点驱动' },
    product_cart_abandonment: { label: '商品购物车流失' },
    quality_gate_status: { label: '质量门禁状态' },
    same_category: { label: '同品类关系' },
    sparse_cohort: { label: '稀疏留存分群' },
    traffic_conversion_gap: { label: '流量转化缺口' },
  },
  relation: {
    co_cart: { label: '共同加购' },
    co_purchase: { label: '共同购买' },
    co_view: { label: '共同浏览' },
  },
  risk: {
    active_value: { label: '活跃价值' },
    clear: { label: '无风险' },
    convert_intent: { label: '转化意图' },
    critical: { label: '严重' },
    danger: { label: '危险' },
    high: { label: '高' },
    low: { label: '低' },
    medium: { label: '中' },
    normal: { label: '正常' },
    at_risk: { label: '流失风险' },
    unknown: { label: '未知风险' },
    warning: { label: '警告' },
    watch: { label: '观察' },
  },
  segment: {
    at_risk: { label: '流失风险' },
    buyer: { label: '购买用户' },
    cart_intent: { label: '加购意图' },
    champion: { label: '冠军用户' },
    high_value: { label: '高价值' },
    one_time_buyer: { label: '单次购买' },
    unknown: { label: '未知分层' },
    viewer: { label: '浏览用户' },
  },
  source: {
    als_implicit: { label: '隐式反馈矩阵分解' },
    als_recall: { label: '矩阵分解召回' },
    category_recall: { label: '品类偏好召回' },
    graph_neighbor: { label: '图谱邻居' },
    graph_neighbor_recall: { label: '图谱邻居召回' },
    optimization_fallback: { label: '优化兜底' },
    popular_fallback: { label: '热门兜底召回' },
    personalized_category: { label: '个性化品类' },
    ranked_topk: { label: '已进入前 K' },
    detail_scan: { label: '明细扫描' },
    spark_cube: { label: 'Spark 物化指标层' },
  },
  status: {
    blocked_by_srm: { label: 'SRM 阻断' },
    critical: { label: '严重异常' },
    warning: { label: '警告异常' },
    insufficient_baseline: { label: '基线不足' },
    degraded_previous_snapshot: { label: '已回退到上一快照' },
    failed: { label: '失败' },
    feasible: { label: '可满足' },
    healthy: { label: '健康' },
    loading: { label: '加载中' },
    none: { label: '无' },
    not_configured: { label: '未配置' },
    'not evaluated': { label: '未评估' },
    needs_attention: { label: '需关注' },
    'needs review': { label: '需复核' },
    needs_review: { label: '需复核' },
    needs_more_sample: { label: '样本不足' },
    not_evaluated: { label: '未评估' },
    not_measurable: { label: '暂不可测' },
    not_significant: { label: '未显著' },
    offline_history_replay: { label: '离线历史回放' },
    optimal: { label: '最优' },
    passed: { label: '已通过' },
    pending: { label: '待生成' },
    positive_significant: { label: '正向显著' },
    negative_significant: { label: '负向显著' },
    collected: { label: '已采集' },
    evaluated: { label: '已评估' },
    degraded: { label: '已降级' },
    fresh: { label: '新鲜' },
    missing: { label: '缺失' },
    published: { label: '已发布' },
    queued: { label: '排队中' },
    ready: { label: '就绪' },
    rejected: { label: '已拒绝' },
    rejected_no_previous_snapshot: { label: '已拒绝且无历史快照' },
    running: { label: '运行中' },
    skipped: { label: '已跳过' },
    stale: { label: '已过期' },
    stable: { label: '稳定' },
    success: { label: '已成功' },
    succeeded: { label: '已成功' },
    SUCCEEDED: { label: '已成功' },
    FAILED: { label: '失败' },
    'sparse fallback': { label: '稀疏兜底' },
    'top-k ready': { label: '前 K 就绪' },
    written: { label: '已写入' },
  },
  variant: {
    control: { label: '对照组' },
    treatment: { label: '实验组' },
  },
};

const sentenceLabels: Record<string, string> = {
  'absolute robust z-score exceeds critical threshold': '稳健分数超过严重阈值。',
  'absolute robust z-score exceeds warning threshold': '稳健分数超过警告阈值。',
  'Collect more history or reduce forecast granularity before committing spend.': '先补充历史数据或降低预测粒度，再用于预算决策。',
  'Check checkout funnel, recommendation fallback, and stock or price changes for this entity.':
    '核查结账漏斗、推荐兜底、库存或价格变化。',
  'entity has too few points to alert safely and is placed on watch': '实体样本过少，仅进入观察状态。',
  'Inspect campaign, bot traffic, price promotion, and downstream capacity before scaling exposure.':
    '先核查活动、异常流量、价格促销和下游承载，再扩大曝光。',
  'Monitor the next refresh and verify whether the movement is business-driven.': '观察下一次刷新，并确认波动是否由真实业务驱动。',
  'YARN-only increased scheduling overhead; AQE and algorithm guards made runtime and memory risk controllable.':
    '集群 CSV 基线调度开销较高，自适应执行与算法护栏让耗时和内存风险更可控。',
  'This is sufficient for reproducible course-report evidence while avoiding unnecessary full-dataset runtime and local Docker resource pressure.':
    '该证据足以支撑课程报告复现，同时避免不必要的全量运行耗时和本地容器资源压力。',
  'The experiment intentionally uses representative partial data instead of running the full Oct+Nov dataset.':
    '本阶段采用代表性抽样数据验证，不运行 10 月与 11 月全量数据。',
  'Partial representative evidence is sufficient for the course report.': '代表性抽样证据已满足课程报告说明。',
  'deterministic RFM + engagement segmentation': '最近活跃、频次和价值规则 + 活跃度分层',
  'History event log 汇总失败任务、重试任务、shuffle 和 spill，用于解释前端性能表现。':
    '运行日志汇总失败任务、重试任务、洗牌读写和溢出，用于解释前端性能表现。',
  'median + median absolute deviation across current feature mart window': '在当前特征窗口内使用中位数与稳健离散度作为基线。',
  'metric collapses to zero after a non-trivial baseline': '指标在有明显历史基线后归零。',
  'Open an incident review and compare against raw events plus Feature Mart partitions.':
    '启动异常复核，对照原始事件和特征集市分区。',
  'same weekday baseline is used when seasonal points reach threshold': '同星期样本达到阈值时使用星期季节性基线。',
  'trailing weekday seasonal median + MAD when enough same-weekday points exist, otherwise trailing global median + MAD':
    '同星期历史样本充足时使用滚动星期季节性稳健基线，否则回退到滚动全局稳健基线。',
  'weekday seasonal median + MAD when enough same-weekday points exist, otherwise global median + MAD':
    '同星期样本充足时使用星期季节性稳健基线，否则回退到全局稳健基线。',
  'weekday median + MAD when enough same-weekday history exists, otherwise global median + MAD.':
    '同星期历史充足时使用星期季节性稳健基线，否则回退到全局稳健基线。',
  'Monitor category demand and prepare a constrained promotion or recommendation adjustment.': '持续观察品类需求，准备小范围促销或推荐调整。',
  'Protect experience quality and avoid excessive fallback recommendations.': '保护推荐体验，避免兜底推荐占比过高。',
  'Review merchandising plan, recommendation coverage, and experiment exposure before the forecast window.': '预测窗口开始前复核货品计划、推荐覆盖和实验曝光。',
  'Use as baseline demand for planning.': '可作为计划制定的基线需求。',
  'Use forecast risks as planning signals; do not treat sparse-history forecasts as causal or high-confidence predictions.':
    '将预测风险作为计划信号，不要把稀疏历史预测视为因果结论或高置信结果。',
  'Use high-lift product relationships as cross-sell and bundle candidates; review support before rollout.':
    '优先复核高提升度商品关系，用于组合搭配、替代和跨品类推荐。',
  'Use high-lift product relationships as cross-sell and bundle candidates.':
    '优先复核高提升度商品关系，用于组合搭配、替代和跨品类推荐。',
  'Use community neighbors for category-level cross-sell review.': '使用同社区邻居商品复核品类交叉推荐。',
  'Launch only experiments with sufficient treatment/control balance; keep holdout immutable during measurement.':
    '仅在实验组与对照组样本均衡时启动实验，并在观测期间保持对照组不可变。',
  'Launch only experiments with sufficient treatment/control balance.': '仅在实验组与对照组样本均衡时启动实验。',
  'Offline estimates are planning priors only; production lift requires randomized holdout measurement.':
    '离线估计仅作为规划先验，真实提升必须通过随机对照实验验证。',
  'Offline estimates are planning priors only.': '离线估计仅作为规划先验。',
  'Historical behavior data supports constrained opportunity ranking, not causal ROI claims.':
    '历史行为数据仅支持约束下的机会排序，不代表因果投资回报。',
  'Use cohort retention and repeat purchase curves to prioritize lifecycle and category recovery plays.':
    '结合留存与复购曲线，优先生命周期触达和类目召回策略。',
  'Use this cohort as a repeat-purchase benchmark.': '可作为复购经营的基准分群。',
  '真实 uplift 需要随机曝光、对照组和结果回流后才能判断。': '真实增量提升需要随机曝光、对照组和结果回流后才能判断。',
  'Prioritize cart recovery and compare price or availability friction.': '优先处理购物车召回，并复核价格或库存摩擦。',
  'Reactivate with category-personalized offers and inspect recommendation coverage.': '用个性化品类优惠召回，并复核推荐覆盖。',
  offline_history_replay_not_causal: '当前为离线历史回放结果，不代表真实因果提升。',
  randomized_exposure_and_outcome_required_for_true_uplift: '真实增量提升需要随机曝光、对照组和结果回流后才能判断。',
};

const experimentLabels: Record<string, string> = {
  lifecycle_reactivation: '生命周期再激活策略',
  recommendation_personalization: '推荐个性化策略',
  portfolio_optimization: '组合经营优化策略',
};

const benchmarkVariantLabels: Record<string, string> = {
  baseline_local_csv: '本地 CSV 基线',
  yarn_only_csv: '集群 CSV 基线',
  yarn_aqe_csv: '集群自适应执行',
  yarn_algorithm_csv: '集群算法优化',
  yarn_parquet: '集群 Parquet 物化',
};

const benchmarkSampleLabels: Record<string, string> = {
  '1pct': '1% 抽样',
  '5pct': '5% 抽样',
  full: '全量样本',
  representative: '代表性样本',
};

const moduleLabels: Record<string, string> = {
  affinity: '商品亲和图谱',
  anomaly: '异常检测',
  experimentation: '实验评估',
  feature_mart: '特征集市',
  forecasting: '需求预测',
  recommendation: '推荐系统',
};

const rawValueDomains: LabelDomain[] = ['eventType', 'status', 'risk', 'segment', 'entityType', 'relation', 'source', 'variant', 'direction'];

export function label(domain: LabelDomain, value: unknown, options: { includeRaw?: boolean; fallback?: string } = {}) {
  const raw = normalizeCode(value);
  if (!raw) return options.fallback ?? '暂无';
  const entry = dictionaries[domain][raw];
  if (!entry) return options.fallback ?? raw;
  if (options.includeRaw) {
    return entry.raw ? `${entry.label} ${entry.raw}` : `${entry.label} ${raw}`;
  }
  return entry.label;
}

export function statusLabel(value: unknown, options: { includeRaw?: boolean } = {}) {
  return label('status', value ?? 'pending', { includeRaw: options.includeRaw, fallback: '待生成' });
}

export function fieldLabel(value: unknown) {
  const raw = normalizeCode(value);
  if (!raw) return '字段';
  return label('metric', raw, { fallback: label('check', raw, { fallback: humanizeCode(raw) }) });
}

export function listLabels(domain: LabelDomain, values: unknown[] | undefined | null, options: { includeRaw?: boolean } = {}) {
  if (!values?.length) return '暂无';
  return values.map((value) => label(domain, value, options)).join('、');
}

export function displayValue(value: unknown, domain?: LabelDomain) {
  if (domain) return label(domain, value);
  const raw = normalizeCode(value);
  if (!raw) return '暂无';
  if (raw === 'unknown') return '未知';
  for (const current of rawValueDomains) {
    const entry = dictionaries[current][raw];
    if (entry) return entry.label;
  }
  return raw;
}

export function algorithmCopy(value: unknown) {
  const raw = typeof value === 'string' ? value.trim() : '';
  if (!raw) return '暂无建议';
  return sentenceLabels[raw] ?? raw;
}

export function rawDisplayValue(value: unknown, fallback = '未知') {
  const raw = normalizeCode(value);
  if (!raw || raw === 'unknown') return fallback;
  return displayValue(raw);
}

export function experimentLabel(value: unknown) {
  const raw = normalizeCode(value);
  if (!raw) return '实验';
  return experimentLabels[raw] ?? rawDisplayValue(raw, '未知实验');
}

export function benchmarkVariantLabel(value: unknown) {
  const raw = normalizeCode(value);
  if (!raw) return '基准组';
  return benchmarkVariantLabels[raw] ?? rawDisplayValue(raw, '未知基准组');
}

export function benchmarkSampleLabel(value: unknown) {
  const raw = normalizeCode(value);
  if (!raw) return '样本';
  return benchmarkSampleLabels[raw] ?? rawDisplayValue(raw, '未知样本');
}

export function moduleLabel(value: unknown) {
  const raw = normalizeCode(value);
  if (!raw) return '模块';
  return moduleLabels[raw] ?? rawDisplayValue(raw, '未知模块');
}

export function optionLabel(domain: LabelDomain, value: unknown) {
  const raw = normalizeCode(value);
  return { value: raw, label: label(domain, raw) };
}

function normalizeCode(value: unknown) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function humanizeCode(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
