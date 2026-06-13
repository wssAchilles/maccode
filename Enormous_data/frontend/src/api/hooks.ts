import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { queryKeys } from './queryKeys';

export function useSummary() {
  return useQuery({ queryKey: queryKeys.summary, queryFn: api.summary });
}

export function useEventDistribution() {
  return useQuery({ queryKey: queryKeys.eventDistribution, queryFn: api.eventDistribution });
}

export function useDailyEvents() {
  return useQuery({ queryKey: queryKeys.dailyEvents, queryFn: api.dailyEvents });
}

export function useDailySales() {
  return useQuery({ queryKey: queryKeys.dailySales, queryFn: api.dailySales });
}

export function useTopCategories() {
  return useQuery({ queryKey: queryKeys.topCategories, queryFn: api.topCategories });
}

export function useTopBrands() {
  return useQuery({ queryKey: queryKeys.topBrands, queryFn: api.topBrands });
}

export function useDashboardSlice(params: { event_type?: string; category_level1?: string; brand?: string }) {
  const enabled = Boolean(params.event_type || params.category_level1 || params.brand);
  return useQuery({
    queryKey: queryKeys.dashboardSlice(params),
    queryFn: () => api.dashboardSlice(params),
    enabled,
    retry: false,
  });
}

export function useControlledQuery() {
  return useMutation({
    mutationKey: queryKeys.controlledQuery,
    mutationFn: api.controlledQuery,
  });
}

export function useConversionFunnel() {
  return useQuery({ queryKey: queryKeys.conversionFunnel, queryFn: api.conversionFunnel });
}

export function useConversionDaily() {
  return useQuery({ queryKey: queryKeys.conversionDaily, queryFn: api.conversionDaily });
}

export function useProductConversion(limit = 20) {
  return useQuery({ queryKey: queryKeys.productConversion(limit), queryFn: () => api.productConversion(limit) });
}

export function useJourneySummary() {
  return useQuery({ queryKey: queryKeys.journeySummary, queryFn: api.journeySummary });
}

export function useJourneyPaths(limit = 50) {
  return useQuery({ queryKey: queryKeys.journeyPaths(limit), queryFn: () => api.journeyPaths(limit) });
}

export function useJourneyTransitions(limit = 50) {
  return useQuery({ queryKey: queryKeys.journeyTransitions(limit), queryFn: () => api.journeyTransitions(limit) });
}

export function useJourneyExitEvents(limit = 50) {
  return useQuery({ queryKey: queryKeys.journeyExitEvents(limit), queryFn: () => api.journeyExitEvents(limit) });
}

export function useJourneyPurchasePaths(limit = 50) {
  return useQuery({ queryKey: queryKeys.journeyPurchasePaths(limit), queryFn: () => api.journeyPurchasePaths(limit) });
}

export function useOptimizationSummary() {
  return useQuery({ queryKey: queryKeys.optimizationSummary, queryFn: api.optimizationSummary });
}

export function useOptimizationPlan(limit = 50) {
  return useQuery({ queryKey: queryKeys.optimizationPlan(limit), queryFn: () => api.optimizationPlan(limit) });
}

export function useOptimizationCandidates(limit = 100) {
  return useQuery({
    queryKey: queryKeys.optimizationCandidates(limit),
    queryFn: () => api.optimizationCandidates(limit),
  });
}

export function useOptimizationQuality() {
  return useQuery({ queryKey: queryKeys.optimizationQuality, queryFn: api.optimizationQuality });
}

export function useRecommendationSummary() {
  return useQuery({ queryKey: queryKeys.recommendationSummary, queryFn: api.recommendationSummary });
}

export function useRecommendationItems(limit = 50) {
  return useQuery({
    queryKey: queryKeys.recommendationItems(limit),
    queryFn: () => api.recommendationItems(limit),
  });
}

export function useRecommendationCandidates(params: { source?: string; limit?: number } = {}) {
  return useQuery({
    queryKey: queryKeys.recommendationCandidates(params),
    queryFn: () => api.recommendationCandidates(params),
    retry: false,
  });
}

export function useRecommendationQuality() {
  return useQuery({ queryKey: queryKeys.recommendationQuality, queryFn: api.recommendationQuality });
}

export function useRecommendationEvaluation() {
  return useQuery({ queryKey: queryKeys.recommendationEvaluation, queryFn: api.recommendationEvaluation, retry: false });
}

export function useRecommendationAlerts() {
  return useQuery({ queryKey: queryKeys.recommendationAlerts, queryFn: api.recommendationAlerts });
}

export function useAnomalySummary() {
  return useQuery({ queryKey: queryKeys.anomalySummary, queryFn: api.anomalySummary });
}

export function useAnomalyAlerts(limit = 50) {
  return useQuery({ queryKey: queryKeys.anomalyAlerts(limit), queryFn: () => api.anomalyAlerts(limit) });
}

export function useAnomalyIncidents(limit = 50) {
  return useQuery({ queryKey: queryKeys.anomalyIncidents(limit), queryFn: () => api.anomalyIncidents(limit), retry: false });
}

export function useAnomalyRootCause(params: { incident_id?: string } = {}) {
  return useQuery({
    queryKey: queryKeys.anomalyRootCause(params),
    queryFn: () => api.anomalyRootCause(params),
    enabled: Boolean(params.incident_id),
    retry: false,
  });
}

export function useAnomalyEvaluation() {
  return useQuery({ queryKey: queryKeys.anomalyEvaluation, queryFn: api.anomalyEvaluation, retry: false });
}

export function useAnomalyTimeline() {
  return useQuery({ queryKey: queryKeys.anomalyTimeline, queryFn: api.anomalyTimeline });
}

export function useAnomalyRules() {
  return useQuery({ queryKey: queryKeys.anomalyRules, queryFn: api.anomalyRules });
}

export function useLifecycleSummary() {
  return useQuery({ queryKey: queryKeys.lifecycleSummary, queryFn: api.lifecycleSummary });
}

export function useLifecycleSegments() {
  return useQuery({ queryKey: queryKeys.lifecycleSegments, queryFn: api.lifecycleSegments });
}

export function useLifecycleRiskQueue(limit = 50) {
  return useQuery({ queryKey: queryKeys.lifecycleRiskQueue(limit), queryFn: () => api.lifecycleRiskQueue(limit) });
}

export function useLifecycleCategoryAffinity(limit = 50) {
  return useQuery({
    queryKey: queryKeys.lifecycleCategoryAffinity(limit),
    queryFn: () => api.lifecycleCategoryAffinity(limit),
  });
}

export function useLifecycleRules() {
  return useQuery({ queryKey: queryKeys.lifecycleRules, queryFn: api.lifecycleRules });
}

export function useExperimentSummary() {
  return useQuery({ queryKey: queryKeys.experimentSummary, queryFn: api.experimentSummary });
}

export function useExperimentCatalog() {
  return useQuery({ queryKey: queryKeys.experimentCatalog, queryFn: api.experimentCatalog });
}

export function useExperimentAssignments(limit = 50) {
  return useQuery({ queryKey: queryKeys.experimentAssignments(limit), queryFn: () => api.experimentAssignments(limit) });
}

export function useExperimentSegments() {
  return useQuery({ queryKey: queryKeys.experimentSegments, queryFn: api.experimentSegments });
}

export function useExperimentGuardrails() {
  return useQuery({ queryKey: queryKeys.experimentGuardrails, queryFn: api.experimentGuardrails });
}

export function useExperimentResults(params: { experiment_key?: string } = {}) {
  return useQuery({ queryKey: queryKeys.experimentResults(params), queryFn: () => api.experimentResults(params), retry: false });
}

export function useExperimentUplift(params: { experiment_key?: string } = {}) {
  return useQuery({ queryKey: queryKeys.experimentUplift(params), queryFn: () => api.experimentUplift(params), retry: false });
}

export function useFeatureMartSummary() {
  return useQuery({ queryKey: queryKeys.featureMartSummary, queryFn: api.featureMartSummary });
}

export function useFeatureMartFreshness() {
  return useQuery({ queryKey: queryKeys.featureMartFreshness, queryFn: api.featureMartFreshness });
}

export function useFeatureMartQuality() {
  return useQuery({ queryKey: queryKeys.featureMartQuality, queryFn: api.featureMartQuality });
}

export function useFeatureMartPartitions() {
  return useQuery({ queryKey: queryKeys.featureMartPartitions, queryFn: api.featureMartPartitions });
}

export function useFeatureMartFeatures() {
  return useQuery({ queryKey: queryKeys.featureMartFeatures, queryFn: api.featureMartFeatures, retry: false });
}

export function useFeatureMartReadiness() {
  return useQuery({ queryKey: queryKeys.featureMartReadiness, queryFn: api.featureMartReadiness, retry: false });
}

export function useFeatureMartProducts(limit = 50) {
  return useQuery({ queryKey: queryKeys.featureMartProducts(limit), queryFn: () => api.featureMartProducts(limit) });
}

export function useFeatureMartCategories(limit = 50) {
  return useQuery({ queryKey: queryKeys.featureMartCategories(limit), queryFn: () => api.featureMartCategories(limit) });
}

export function useFeatureMartUsers(limit = 50) {
  return useQuery({ queryKey: queryKeys.featureMartUsers(limit), queryFn: () => api.featureMartUsers(limit) });
}

export function useForecastingSummary() {
  return useQuery({ queryKey: queryKeys.forecastingSummary, queryFn: api.forecastingSummary });
}

export function useForecastingSeries(params: { scope?: string; entity?: string; metric?: string } = {}) {
  return useQuery({ queryKey: queryKeys.forecastingSeries(params), queryFn: () => api.forecastingSeries(params) });
}

export function useForecastingEntities(limit = 50) {
  return useQuery({ queryKey: queryKeys.forecastingEntities(limit), queryFn: () => api.forecastingEntities(limit) });
}

export function useForecastingBacktest(params: { scope?: string; entity?: string } = {}) {
  return useQuery({ queryKey: queryKeys.forecastingBacktest(params), queryFn: () => api.forecastingBacktest(params) });
}

export function useForecastingEvaluation() {
  return useQuery({ queryKey: queryKeys.forecastingEvaluation, queryFn: api.forecastingEvaluation, retry: false });
}

export function useForecastingRisks(params: { severity?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.forecastingRisks(params), queryFn: () => api.forecastingRisks(params) });
}

export function useForecastingQuality() {
  return useQuery({ queryKey: queryKeys.forecastingQuality, queryFn: api.forecastingQuality });
}

export function useAffinitySummary() {
  return useQuery({ queryKey: queryKeys.affinitySummary, queryFn: api.affinitySummary });
}

export function useAffinityNodes(params: { entity_type?: string; q?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.affinityNodes(params), queryFn: () => api.affinityNodes(params) });
}

export function useAffinityEdges(params: { entity_id?: string; relation_type?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.affinityEdges(params), queryFn: () => api.affinityEdges(params) });
}

export function useAffinityCommunities(limit = 50) {
  return useQuery({ queryKey: queryKeys.affinityCommunities(limit), queryFn: () => api.affinityCommunities(limit) });
}

export function useAffinityOpportunities(params: { type?: string; confidence?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: queryKeys.affinityOpportunities(params),
    queryFn: () => api.affinityOpportunities(params),
  });
}

export function useAffinityCentrality(params: { community_id?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.affinityCentrality(params), queryFn: () => api.affinityCentrality(params), retry: false });
}

export function useAffinityQuality() {
  return useQuery({ queryKey: queryKeys.affinityQuality, queryFn: api.affinityQuality });
}

export function useCohortSummary() {
  return useQuery({ queryKey: queryKeys.cohortSummary, queryFn: api.cohortSummary });
}

export function useCohortRetention(params: { cohort?: string; metric?: string } = {}) {
  return useQuery({ queryKey: queryKeys.cohortRetention(params), queryFn: () => api.cohortRetention(params) });
}

export function useCohortValueCurves(params: { cohort?: string } = {}) {
  return useQuery({ queryKey: queryKeys.cohortValueCurves(params), queryFn: () => api.cohortValueCurves(params) });
}

export function useCohortRepurchaseIntervals() {
  return useQuery({ queryKey: queryKeys.cohortRepurchaseIntervals, queryFn: api.cohortRepurchaseIntervals });
}

export function useCohortSegments(params: { category?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.cohortSegments(params), queryFn: () => api.cohortSegments(params) });
}

export function useCohortQuality() {
  return useQuery({ queryKey: queryKeys.cohortQuality, queryFn: api.cohortQuality });
}

export function usePortfolioSummary() {
  return useQuery({ queryKey: queryKeys.portfolioSummary, queryFn: api.portfolioSummary });
}

export function usePortfolioCategories(limit = 50) {
  return useQuery({ queryKey: queryKeys.portfolioCategories(limit), queryFn: () => api.portfolioCategories(limit) });
}

export function usePortfolioBrands(params: { category?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.portfolioBrands(params), queryFn: () => api.portfolioBrands(params) });
}

export function usePortfolioPriceBands(params: { category?: string; price_band?: string } = {}) {
  return useQuery({ queryKey: queryKeys.portfolioPriceBands(params), queryFn: () => api.portfolioPriceBands(params) });
}

export function usePortfolioProducts(params: { category?: string; brand?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.portfolioProducts(params), queryFn: () => api.portfolioProducts(params) });
}

export function usePortfolioConcentration() {
  return useQuery({ queryKey: queryKeys.portfolioConcentration, queryFn: api.portfolioConcentration });
}

export function usePortfolioOpportunities(params: { type?: string; confidence?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: queryKeys.portfolioOpportunities(params),
    queryFn: () => api.portfolioOpportunities(params),
  });
}

export function usePortfolioQuality() {
  return useQuery({ queryKey: queryKeys.portfolioQuality, queryFn: api.portfolioQuality });
}

export function useCartSummary() {
  return useQuery({ queryKey: queryKeys.cartSummary, queryFn: api.cartSummary });
}

export function useCartCategories(limit = 50) {
  return useQuery({ queryKey: queryKeys.cartCategories(limit), queryFn: () => api.cartCategories(limit) });
}

export function useCartProducts(params: { category?: string; brand?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.cartProducts(params), queryFn: () => api.cartProducts(params) });
}

export function useCartRecoveryQueue(params: { action?: string; confidence?: number; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.cartRecoveryQueue(params), queryFn: () => api.cartRecoveryQueue(params) });
}

export function useCartQuality() {
  return useQuery({ queryKey: queryKeys.cartQuality, queryFn: api.cartQuality });
}

export function useAttributionSummary() {
  return useQuery({ queryKey: queryKeys.attributionSummary, queryFn: api.attributionSummary });
}

export function useAttributionModels(params: { entity_type?: string } = {}) {
  return useQuery({ queryKey: queryKeys.attributionModels(params), queryFn: () => api.attributionModels(params) });
}

export function useAttributionEntities(params: { entity_type?: string; model?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.attributionEntities(params), queryFn: () => api.attributionEntities(params) });
}

export function useAttributionPaths(limit = 50) {
  return useQuery({ queryKey: queryKeys.attributionPaths(limit), queryFn: () => api.attributionPaths(limit) });
}

export function useAttributionAssists(params: { entity_type?: string; limit?: number } = {}) {
  return useQuery({ queryKey: queryKeys.attributionAssists(params), queryFn: () => api.attributionAssists(params) });
}

export function useAttributionQuality() {
  return useQuery({ queryKey: queryKeys.attributionQuality, queryFn: api.attributionQuality });
}

export function useJob() {
  return useQuery({ queryKey: queryKeys.job, queryFn: api.job, refetchInterval: 10_000 });
}

export function useJobs(limit = 20) {
  return useQuery({ queryKey: queryKeys.jobs(limit), queryFn: () => api.jobs(limit), refetchInterval: 10_000 });
}

export function useJobDetail(jobId?: string) {
  return useQuery({
    queryKey: queryKeys.jobDetail(jobId ?? ''),
    queryFn: () => api.jobDetail(jobId ?? ''),
    enabled: Boolean(jobId),
    refetchInterval: 10_000,
  });
}

export function useJobLineage(jobId?: string) {
  return useQuery({
    queryKey: queryKeys.jobLineage(jobId ?? ''),
    queryFn: () => api.jobLineage(jobId ?? ''),
    enabled: Boolean(jobId),
    refetchInterval: 10_000,
  });
}

export function useJobQuality(jobId?: string) {
  return useQuery({
    queryKey: queryKeys.jobQuality(jobId ?? ''),
    queryFn: () => api.jobQuality(jobId ?? ''),
    enabled: Boolean(jobId),
    refetchInterval: 10_000,
  });
}

export function useOpsEvidence() {
  return useQuery({ queryKey: queryKeys.opsEvidence, queryFn: api.opsEvidence });
}

export function useOptimizationImpact() {
  return useQuery({ queryKey: queryKeys.optimizationImpact, queryFn: api.optimizationImpact });
}

export function useTable(params: { page: number; size: number; event_type?: string; category_level1?: string; brand?: string }) {
  return useQuery({
    queryKey: queryKeys.table(params),
    queryFn: () => api.table(params),
  });
}

export function useRefreshJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.refresh,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.job });
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}
