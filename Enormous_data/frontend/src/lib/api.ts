import type {
  AffinityCommunity,
  AffinityEdge,
  AffinityNode,
  AffinityOpportunity,
  AffinityQuality,
  AffinitySummary,
  ApiEnvelope,
  CohortQuality,
  CohortRepurchaseInterval,
  CohortRetentionCell,
  CohortSegment,
  CohortSummary,
  CohortValueCurve,
  CartCategorySegment,
  CartProductSegment,
  CartQuality,
  CartRecoveryQueueItem,
  CartSummary,
  AnomalyAlert,
  AnomalyRules,
  AnomalySummary,
  AnomalyTimelinePoint,
  AttributionAssist,
  AttributionEntity,
  AttributionModel,
  AttributionPath,
  AttributionQuality,
  AttributionSummary,
  DateValue,
  DailyConversion,
  ExperimentAssignment,
  ExperimentCatalogItem,
  ExperimentGuardrails,
  ExperimentSegment,
  ExperimentSummary,
  FeatureMartCategory,
  FeatureMartFreshness,
  FeatureMartPartitionReport,
  FeatureMartProduct,
  FeatureMartQuality,
  FeatureMartSummary,
  FeatureMartUser,
  ForecastingBacktestPoint,
  ForecastingEntity,
  ForecastingQuality,
  ForecastingRisk,
  ForecastingSeriesPoint,
  ForecastingSummary,
  JobLineage,
  JobList,
  JobQuality,
  JobStatus,
  JourneyExitEvent,
  JourneyPath,
  JourneyPurchasePath,
  JourneySummary,
  JourneyTransition,
  LifecycleCategoryAffinity,
  LifecycleRules,
  LifecycleSegment,
  LifecycleSummary,
  LifecycleUser,
  NamedValue,
  OptimizationCandidate,
  OptimizationPlanItem,
  OptimizationQuality,
  OptimizationSummary,
  OpsEvidence,
  PortfolioBrandMix,
  PortfolioCategoryMix,
  PortfolioOpportunity,
  PortfolioPriceBand,
  PortfolioProductConcentration,
  PortfolioQuality,
  PortfolioSummary,
  ProductConversion,
  RecommendationAlert,
  RecommendationItem,
  RecommendationQuality,
  RecommendationSummary,
  SessionFunnel,
  Summary,
  TableResult,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || '请求失败');
  }
  return payload.data;
}

function withQuery(path: string, params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      query.set(key, String(value));
    }
  });
  return query.size ? `${path}?${query.toString()}` : path;
}

export const api = {
  summary: () => request<Summary>('/summary'),
  eventDistribution: () => request<NamedValue[]>('/events/distribution'),
  dailyEvents: () => request<DateValue[]>('/trend/daily-events'),
  dailySales: () => request<DateValue[]>('/trend/daily-sales'),
  topCategories: () => request<NamedValue[]>('/ranking/categories'),
  topBrands: () => request<NamedValue[]>('/ranking/brands'),
  conversionFunnel: () => request<SessionFunnel>('/conversion/funnel'),
  conversionDaily: () => request<DailyConversion[]>('/conversion/daily'),
  productConversion: (limit = 20) => request<ProductConversion[]>(withQuery('/conversion/products', { limit })),
  journeySummary: () => request<JourneySummary>('/journey/summary'),
  journeyPaths: (limit = 50) => request<JourneyPath[]>(withQuery('/journey/paths', { limit })),
  journeyTransitions: (limit = 50) => request<JourneyTransition[]>(withQuery('/journey/transitions', { limit })),
  journeyExitEvents: (limit = 50) => request<JourneyExitEvent[]>(withQuery('/journey/exit-events', { limit })),
  journeyPurchasePaths: (limit = 50) => request<JourneyPurchasePath[]>(withQuery('/journey/purchase-paths', { limit })),
  optimizationSummary: () => request<OptimizationSummary>('/optimization/summary'),
  optimizationPlan: (limit = 50) => request<OptimizationPlanItem[]>(withQuery('/optimization/plan', { limit })),
  optimizationCandidates: (limit = 100) =>
    request<OptimizationCandidate[]>(withQuery('/optimization/candidates', { limit })),
  optimizationQuality: () => request<OptimizationQuality>('/optimization/quality'),
  recommendationSummary: () => request<RecommendationSummary>('/recommendations/summary'),
  recommendationItems: (limit = 50) => request<RecommendationItem[]>(withQuery('/recommendations/items', { limit })),
  recommendationQuality: () => request<RecommendationQuality>('/recommendations/quality'),
  recommendationAlerts: () => request<RecommendationAlert[]>('/recommendations/alerts'),
  anomalySummary: () => request<AnomalySummary>('/anomalies/summary'),
  anomalyAlerts: (limit = 50) => request<AnomalyAlert[]>(withQuery('/anomalies/alerts', { limit })),
  anomalyTimeline: () => request<AnomalyTimelinePoint[]>('/anomalies/timeline'),
  anomalyRules: () => request<AnomalyRules>('/anomalies/rules'),
  lifecycleSummary: () => request<LifecycleSummary>('/lifecycle/summary'),
  lifecycleSegments: () => request<LifecycleSegment[]>('/lifecycle/segments'),
  lifecycleRiskQueue: (limit = 50) => request<LifecycleUser[]>(withQuery('/lifecycle/risk-queue', { limit })),
  lifecycleCategoryAffinity: (limit = 50) =>
    request<LifecycleCategoryAffinity[]>(withQuery('/lifecycle/category-affinity', { limit })),
  lifecycleRules: () => request<LifecycleRules>('/lifecycle/rules'),
  experimentSummary: () => request<ExperimentSummary>('/experiments/summary'),
  experimentCatalog: () => request<ExperimentCatalogItem[]>('/experiments/catalog'),
  experimentAssignments: (limit = 50) =>
    request<ExperimentAssignment[]>(withQuery('/experiments/assignments', { limit })),
  experimentSegments: () => request<ExperimentSegment[]>('/experiments/segments'),
  experimentGuardrails: () => request<ExperimentGuardrails>('/experiments/guardrails'),
  featureMartSummary: () => request<FeatureMartSummary>('/feature-mart/summary'),
  featureMartFreshness: () => request<FeatureMartFreshness>('/feature-mart/freshness'),
  featureMartQuality: () => request<FeatureMartQuality>('/feature-mart/quality'),
  featureMartPartitions: () => request<FeatureMartPartitionReport>('/feature-mart/partitions'),
  featureMartProducts: (limit = 50) => request<FeatureMartProduct[]>(withQuery('/feature-mart/products', { limit })),
  featureMartCategories: (limit = 50) =>
    request<FeatureMartCategory[]>(withQuery('/feature-mart/categories', { limit })),
  featureMartUsers: (limit = 50) => request<FeatureMartUser[]>(withQuery('/feature-mart/users', { limit })),
  forecastingSummary: () => request<ForecastingSummary>('/forecasting/summary'),
  forecastingSeries: (params: { scope?: string; entity?: string; metric?: string } = {}) =>
    request<ForecastingSeriesPoint[]>(withQuery('/forecasting/series', params)),
  forecastingEntities: (limit = 50) => request<ForecastingEntity[]>(withQuery('/forecasting/entities', { limit })),
  forecastingBacktest: (params: { scope?: string; entity?: string } = {}) =>
    request<ForecastingBacktestPoint[]>(withQuery('/forecasting/backtest', params)),
  forecastingRisks: (params: { severity?: string; limit?: number } = {}) =>
    request<ForecastingRisk[]>(withQuery('/forecasting/risks', params)),
  forecastingQuality: () => request<ForecastingQuality>('/forecasting/quality'),
  affinitySummary: () => request<AffinitySummary>('/affinity/summary'),
  affinityNodes: (params: { entity_type?: string; q?: string; limit?: number } = {}) =>
    request<AffinityNode[]>(withQuery('/affinity/nodes', params)),
  affinityEdges: (params: { entity_id?: string; relation_type?: string; limit?: number } = {}) =>
    request<AffinityEdge[]>(withQuery('/affinity/edges', params)),
  affinityCommunities: (limit = 50) => request<AffinityCommunity[]>(withQuery('/affinity/communities', { limit })),
  affinityOpportunities: (params: { type?: string; confidence?: number; limit?: number } = {}) =>
    request<AffinityOpportunity[]>(withQuery('/affinity/opportunities', params)),
  affinityQuality: () => request<AffinityQuality>('/affinity/quality'),
  cohortSummary: () => request<CohortSummary>('/cohorts/summary'),
  cohortRetention: (params: { cohort?: string; metric?: string } = {}) =>
    request<CohortRetentionCell[]>(withQuery('/cohorts/retention', params)),
  cohortValueCurves: (params: { cohort?: string } = {}) =>
    request<CohortValueCurve[]>(withQuery('/cohorts/value-curves', params)),
  cohortRepurchaseIntervals: () => request<CohortRepurchaseInterval[]>('/cohorts/repurchase-intervals'),
  cohortSegments: (params: { category?: string; limit?: number } = {}) =>
    request<CohortSegment[]>(withQuery('/cohorts/segments', params)),
  cohortQuality: () => request<CohortQuality>('/cohorts/quality'),
  portfolioSummary: () => request<PortfolioSummary>('/portfolio/summary'),
  portfolioCategories: (limit = 50) => request<PortfolioCategoryMix[]>(withQuery('/portfolio/categories', { limit })),
  portfolioBrands: (params: { category?: string; limit?: number } = {}) =>
    request<PortfolioBrandMix[]>(withQuery('/portfolio/brands', params)),
  portfolioPriceBands: (params: { category?: string; price_band?: string } = {}) =>
    request<PortfolioPriceBand[]>(withQuery('/portfolio/price-bands', params)),
  portfolioProducts: (params: { category?: string; brand?: string; limit?: number } = {}) =>
    request<PortfolioProductConcentration[]>(withQuery('/portfolio/products', params)),
  portfolioConcentration: () => request<PortfolioProductConcentration[]>('/portfolio/concentration'),
  portfolioOpportunities: (params: { type?: string; confidence?: number; limit?: number } = {}) =>
    request<PortfolioOpportunity[]>(withQuery('/portfolio/opportunities', params)),
  portfolioQuality: () => request<PortfolioQuality>('/portfolio/quality'),
  cartSummary: () => request<CartSummary>('/cart-recovery/summary'),
  cartCategories: (limit = 50) => request<CartCategorySegment[]>(withQuery('/cart-recovery/categories', { limit })),
  cartProducts: (params: { category?: string; brand?: string; limit?: number } = {}) =>
    request<CartProductSegment[]>(withQuery('/cart-recovery/products', params)),
  cartRecoveryQueue: (params: { action?: string; confidence?: number; limit?: number } = {}) =>
    request<CartRecoveryQueueItem[]>(withQuery('/cart-recovery/recovery-queue', params)),
  cartQuality: () => request<CartQuality>('/cart-recovery/quality'),
  attributionSummary: () => request<AttributionSummary>('/attribution/summary'),
  attributionModels: (params: { entity_type?: string } = {}) =>
    request<AttributionModel[]>(withQuery('/attribution/models', params)),
  attributionEntities: (params: { entity_type?: string; model?: string; limit?: number } = {}) =>
    request<AttributionEntity[]>(withQuery('/attribution/entities', params)),
  attributionPaths: (limit = 50) => request<AttributionPath[]>(withQuery('/attribution/paths', { limit })),
  attributionAssists: (params: { entity_type?: string; limit?: number } = {}) =>
    request<AttributionAssist[]>(withQuery('/attribution/assists', params)),
  attributionQuality: () => request<AttributionQuality>('/attribution/quality'),
  job: () => request<JobStatus>('/job'),
  jobs: (limit = 20) => request<JobList>(withQuery('/jobs', { limit })),
  jobDetail: (jobId: string) => request<JobStatus>(`/jobs/${jobId}`),
  jobLineage: (jobId: string) => request<JobLineage>(`/jobs/${jobId}/lineage`),
  jobQuality: (jobId: string) => request<JobQuality>(`/jobs/${jobId}/quality`),
  opsEvidence: () => request<OpsEvidence>('/ops/evidence'),
  refresh: () => request<{ status: string; job_id: string }>('/refresh', { method: 'POST' }),
  table: (params: { page: number; size: number; event_type?: string }) =>
    request<TableResult>(withQuery('/table', params)),
};
