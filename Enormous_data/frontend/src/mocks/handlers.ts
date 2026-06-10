import { http, HttpResponse } from 'msw';
import {
  affinityCommunitiesFixture,
  affinityEdgesFixture,
  affinityNodesFixture,
  affinityOpportunitiesFixture,
  affinityQualityFixture,
  affinitySummaryFixture,
  anomalyAlertsFixture,
  anomalyRulesFixture,
  anomalySummaryFixture,
  anomalyTimelineFixture,
  attributionAssistsFixture,
  attributionEntitiesFixture,
  attributionModelsFixture,
  attributionPathsFixture,
  attributionQualityFixture,
  attributionSummaryFixture,
  cartCategoriesFixture,
  cartProductsFixture,
  cartQualityFixture,
  cartRecoveryQueueFixture,
  cartSummaryFixture,
  cohortQualityFixture,
  cohortRepurchaseIntervalsFixture,
  cohortRetentionFixture,
  cohortSegmentsFixture,
  cohortSummaryFixture,
  cohortValueCurvesFixture,
  conversionDailyFixture,
  conversionFunnelFixture,
  dailyEventsFixture,
  dailySalesFixture,
  envelope,
  eventDistributionFixture,
  experimentAssignmentsFixture,
  experimentCatalogFixture,
  experimentGuardrailsFixture,
  experimentSegmentsFixture,
  experimentSummaryFixture,
  featureMartCategoriesFixture,
  featureMartFreshnessFixture,
  featureMartPartitionsFixture,
  featureMartProductsFixture,
  featureMartQualityFixture,
  featureMartSummaryFixture,
  featureMartUsersFixture,
  forecastingBacktestFixture,
  forecastingEntitiesFixture,
  forecastingQualityFixture,
  forecastingRisksFixture,
  forecastingSeriesFixture,
  forecastingSummaryFixture,
  jobFixture,
  jobLineageFixture,
  jobListFixture,
  jobQualityFixture,
  journeyExitEventsFixture,
  journeyPathsFixture,
  journeyPurchasePathsFixture,
  journeySummaryFixture,
  journeyTransitionsFixture,
  lifecycleCategoryAffinityFixture,
  lifecycleRiskQueueFixture,
  lifecycleRulesFixture,
  lifecycleSegmentsFixture,
  lifecycleSummaryFixture,
  optimizationCandidatesFixture,
  optimizationPlanFixture,
  optimizationQualityFixture,
  optimizationSummaryFixture,
  opsEvidenceFixture,
  portfolioBrandsFixture,
  portfolioCategoriesFixture,
  portfolioOpportunitiesFixture,
  portfolioPriceBandsFixture,
  portfolioProductConcentrationFixture,
  portfolioQualityFixture,
  portfolioSummaryFixture,
  productConversionFixture,
  rankingFixture,
  recommendationAlertsFixture,
  recommendationItemsFixture,
  recommendationQualityFixture,
  recommendationSummaryFixture,
  summaryFixture,
  tableFixture,
} from './fixtures';

export const handlers = [
  http.get('/api/v1/summary', () => HttpResponse.json(envelope(summaryFixture))),
  http.get('/api/v1/events/distribution', () => HttpResponse.json(envelope(eventDistributionFixture))),
  http.get('/api/v1/trend/daily-events', () => HttpResponse.json(envelope(dailyEventsFixture))),
  http.get('/api/v1/trend/daily-sales', () => HttpResponse.json(envelope(dailySalesFixture))),
  http.get('/api/v1/ranking/categories', () => HttpResponse.json(envelope(rankingFixture))),
  http.get('/api/v1/ranking/brands', () => HttpResponse.json(envelope(rankingFixture))),
  http.get('/api/v1/conversion/funnel', () => HttpResponse.json(envelope(conversionFunnelFixture))),
  http.get('/api/v1/conversion/daily', () => HttpResponse.json(envelope(conversionDailyFixture))),
  http.get('/api/v1/conversion/products', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 20);
    return HttpResponse.json(envelope(productConversionFixture.slice(0, limit)));
  }),
  http.get('/api/v1/journey/summary', () => HttpResponse.json(envelope(journeySummaryFixture))),
  http.get('/api/v1/journey/paths', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(journeyPathsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/journey/transitions', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(journeyTransitionsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/journey/exit-events', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(journeyExitEventsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/journey/purchase-paths', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(journeyPurchasePathsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/optimization/summary', () => HttpResponse.json(envelope(optimizationSummaryFixture))),
  http.get('/api/v1/optimization/plan', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(optimizationPlanFixture.slice(0, limit)));
  }),
  http.get('/api/v1/optimization/candidates', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 100);
    return HttpResponse.json(envelope(optimizationCandidatesFixture.slice(0, limit)));
  }),
  http.get('/api/v1/optimization/quality', () => HttpResponse.json(envelope(optimizationQualityFixture))),
  http.get('/api/v1/recommendations/summary', () => HttpResponse.json(envelope(recommendationSummaryFixture))),
  http.get('/api/v1/recommendations/items', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(recommendationItemsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/recommendations/quality', () => HttpResponse.json(envelope(recommendationQualityFixture))),
  http.get('/api/v1/recommendations/alerts', () => HttpResponse.json(envelope(recommendationAlertsFixture))),
  http.get('/api/v1/anomalies/summary', () => HttpResponse.json(envelope(anomalySummaryFixture))),
  http.get('/api/v1/anomalies/alerts', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(anomalyAlertsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/anomalies/timeline', () => HttpResponse.json(envelope(anomalyTimelineFixture))),
  http.get('/api/v1/anomalies/rules', () => HttpResponse.json(envelope(anomalyRulesFixture))),
  http.get('/api/v1/lifecycle/summary', () => HttpResponse.json(envelope(lifecycleSummaryFixture))),
  http.get('/api/v1/lifecycle/segments', () => HttpResponse.json(envelope(lifecycleSegmentsFixture))),
  http.get('/api/v1/lifecycle/risk-queue', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(lifecycleRiskQueueFixture.slice(0, limit)));
  }),
  http.get('/api/v1/lifecycle/category-affinity', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(lifecycleCategoryAffinityFixture.slice(0, limit)));
  }),
  http.get('/api/v1/lifecycle/rules', () => HttpResponse.json(envelope(lifecycleRulesFixture))),
  http.get('/api/v1/experiments/summary', () => HttpResponse.json(envelope(experimentSummaryFixture))),
  http.get('/api/v1/experiments/catalog', () => HttpResponse.json(envelope(experimentCatalogFixture))),
  http.get('/api/v1/experiments/assignments', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(experimentAssignmentsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/experiments/segments', () => HttpResponse.json(envelope(experimentSegmentsFixture))),
  http.get('/api/v1/experiments/guardrails', () => HttpResponse.json(envelope(experimentGuardrailsFixture))),
  http.get('/api/v1/feature-mart/summary', () => HttpResponse.json(envelope(featureMartSummaryFixture))),
  http.get('/api/v1/feature-mart/freshness', () => HttpResponse.json(envelope(featureMartFreshnessFixture))),
  http.get('/api/v1/feature-mart/quality', () => HttpResponse.json(envelope(featureMartQualityFixture))),
  http.get('/api/v1/feature-mart/partitions', () => HttpResponse.json(envelope(featureMartPartitionsFixture))),
  http.get('/api/v1/feature-mart/products', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(featureMartProductsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/feature-mart/categories', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(featureMartCategoriesFixture.slice(0, limit)));
  }),
  http.get('/api/v1/feature-mart/users', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(featureMartUsersFixture.slice(0, limit)));
  }),
  http.get('/api/v1/forecasting/summary', () => HttpResponse.json(envelope(forecastingSummaryFixture))),
  http.get('/api/v1/forecasting/series', ({ request }) => {
    const url = new URL(request.url);
    const scope = url.searchParams.get('scope');
    const entity = url.searchParams.get('entity');
    const metric = url.searchParams.get('metric');
    const rows = forecastingSeriesFixture.filter((row) => {
      if (scope && row.scope !== scope) return false;
      if (entity && row.entity_key !== entity) return false;
      if (metric && row.metric !== metric) return false;
      return true;
    });
    return HttpResponse.json(envelope(rows));
  }),
  http.get('/api/v1/forecasting/entities', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(forecastingEntitiesFixture.slice(0, limit)));
  }),
  http.get('/api/v1/forecasting/backtest', ({ request }) => {
    const url = new URL(request.url);
    const scope = url.searchParams.get('scope');
    const entity = url.searchParams.get('entity');
    const rows = forecastingBacktestFixture.filter((row) => {
      if (scope && row.scope !== scope) return false;
      if (entity && row.entity_key !== entity) return false;
      return true;
    });
    return HttpResponse.json(envelope(rows));
  }),
  http.get('/api/v1/forecasting/risks', ({ request }) => {
    const url = new URL(request.url);
    const severity = url.searchParams.get('severity');
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const rows = forecastingRisksFixture.filter((row) => !severity || row.severity === severity);
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/forecasting/quality', () => HttpResponse.json(envelope(forecastingQualityFixture))),
  http.get('/api/v1/affinity/summary', () => HttpResponse.json(envelope(affinitySummaryFixture))),
  http.get('/api/v1/affinity/nodes', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 100);
    const entityType = url.searchParams.get('entity_type');
    const query = url.searchParams.get('q')?.toLowerCase();
    const rows = affinityNodesFixture.filter((row) => {
      if (entityType && row.entity_type !== entityType) return false;
      if (query) {
        return [row.entity_id, row.entity_label, row.brand, row.category_level1].some((value) =>
          value.toLowerCase().includes(query),
        );
      }
      return true;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/affinity/edges', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 100);
    const entityId = url.searchParams.get('entity_id');
    const relationType = url.searchParams.get('relation_type');
    const rows = affinityEdgesFixture.filter((row) => {
      if (entityId && row.source_id !== entityId && row.target_id !== entityId) return false;
      if (relationType && row.relation_type !== relationType) return false;
      return true;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/affinity/communities', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(affinityCommunitiesFixture.slice(0, limit)));
  }),
  http.get('/api/v1/affinity/opportunities', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 100);
    const type = url.searchParams.get('type');
    const confidence = Number(url.searchParams.get('confidence') ?? 0);
    const rows = affinityOpportunitiesFixture.filter((row) => {
      if (type && row.type !== type) return false;
      return row.confidence >= confidence;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/affinity/quality', () => HttpResponse.json(envelope(affinityQualityFixture))),
  http.get('/api/v1/cohorts/summary', () => HttpResponse.json(envelope(cohortSummaryFixture))),
  http.get('/api/v1/cohorts/retention', ({ request }) => {
    const url = new URL(request.url);
    const cohort = url.searchParams.get('cohort');
    const rows = cohortRetentionFixture.filter((row) => !cohort || row.cohort === cohort);
    return HttpResponse.json(envelope(rows));
  }),
  http.get('/api/v1/cohorts/value-curves', ({ request }) => {
    const url = new URL(request.url);
    const cohort = url.searchParams.get('cohort');
    const rows = cohortValueCurvesFixture.filter((row) => !cohort || row.cohort === cohort);
    return HttpResponse.json(envelope(rows));
  }),
  http.get('/api/v1/cohorts/repurchase-intervals', () => HttpResponse.json(envelope(cohortRepurchaseIntervalsFixture))),
  http.get('/api/v1/cohorts/segments', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const category = url.searchParams.get('category')?.toLowerCase();
    const rows = cohortSegmentsFixture.filter((row) => !category || row.category_level1.toLowerCase() === category);
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/cohorts/quality', () => HttpResponse.json(envelope(cohortQualityFixture))),
  http.get('/api/v1/portfolio/summary', () => HttpResponse.json(envelope(portfolioSummaryFixture))),
  http.get('/api/v1/portfolio/categories', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(portfolioCategoriesFixture.slice(0, limit)));
  }),
  http.get('/api/v1/portfolio/brands', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const category = url.searchParams.get('category');
    const rows = portfolioBrandsFixture.filter((row) => !category || row.category_level1 === category);
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/portfolio/price-bands', ({ request }) => {
    const url = new URL(request.url);
    const category = url.searchParams.get('category');
    const band = url.searchParams.get('price_band');
    const rows = portfolioPriceBandsFixture.filter((row) => {
      if (category && row.category_level1 !== category) return false;
      if (band && row.price_band !== band) return false;
      return true;
    });
    return HttpResponse.json(envelope(rows));
  }),
  http.get('/api/v1/portfolio/products', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const category = url.searchParams.get('category');
    const brand = url.searchParams.get('brand');
    const rows = portfolioProductConcentrationFixture.filter((row) => {
      if (category && row.category_level1 !== category) return false;
      if (brand && row.brand !== brand) return false;
      return true;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/portfolio/concentration', () => HttpResponse.json(envelope(portfolioProductConcentrationFixture))),
  http.get('/api/v1/portfolio/opportunities', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const type = url.searchParams.get('type');
    const confidence = Number(url.searchParams.get('confidence') ?? 0);
    const rows = portfolioOpportunitiesFixture.filter((row) => {
      if (type && row.opportunity_type !== type) return false;
      return row.confidence >= confidence;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/portfolio/quality', () => HttpResponse.json(envelope(portfolioQualityFixture))),
  http.get('/api/v1/cart-recovery/summary', () => HttpResponse.json(envelope(cartSummaryFixture))),
  http.get('/api/v1/cart-recovery/categories', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(cartCategoriesFixture.slice(0, limit)));
  }),
  http.get('/api/v1/cart-recovery/products', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const category = url.searchParams.get('category');
    const brand = url.searchParams.get('brand');
    const rows = cartProductsFixture.filter((row) => {
      if (category && row.category_level1 !== category) return false;
      if (brand && row.brand !== brand) return false;
      return true;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/cart-recovery/recovery-queue', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const action = url.searchParams.get('action');
    const confidence = Number(url.searchParams.get('confidence') ?? 0);
    const rows = cartRecoveryQueueFixture.filter((row) => {
      if (action && row.recovery_action !== action) return false;
      return row.confidence >= confidence;
    });
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/cart-recovery/quality', () => HttpResponse.json(envelope(cartQualityFixture))),
  http.get('/api/v1/attribution/summary', () => HttpResponse.json(envelope(attributionSummaryFixture))),
  http.get('/api/v1/attribution/models', ({ request }) => {
    const url = new URL(request.url);
    const entityType = url.searchParams.get('entity_type');
    const rows = attributionModelsFixture.filter((row) => !entityType || row.entity_type === entityType);
    return HttpResponse.json(envelope(rows));
  }),
  http.get('/api/v1/attribution/entities', ({ request }) => {
    const url = new URL(request.url);
    const entityType = url.searchParams.get('entity_type');
    const model = url.searchParams.get('model') ?? 'time_decay';
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const sortKey =
      model === 'first_touch'
        ? 'first_touch_revenue'
        : model === 'last_touch'
          ? 'last_touch_revenue'
          : model === 'linear'
            ? 'linear_assisted_revenue'
            : 'time_decay_assisted_revenue';
    const rows = attributionEntitiesFixture
      .filter((row) => !entityType || row.entity_type === entityType)
      .sort((left, right) => Number(right[sortKey]) - Number(left[sortKey]));
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/attribution/paths', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    return HttpResponse.json(envelope(attributionPathsFixture.slice(0, limit)));
  }),
  http.get('/api/v1/attribution/assists', ({ request }) => {
    const url = new URL(request.url);
    const entityType = url.searchParams.get('entity_type');
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const rows = attributionAssistsFixture.filter((row) => !entityType || row.entity_type === entityType);
    return HttpResponse.json(envelope(rows.slice(0, limit)));
  }),
  http.get('/api/v1/attribution/quality', () => HttpResponse.json(envelope(attributionQualityFixture))),
  http.get('/api/v1/job', () => HttpResponse.json(envelope(jobFixture))),
  http.get('/api/v1/jobs', () => HttpResponse.json(envelope(jobListFixture))),
  http.get('/api/v1/jobs/:jobId', () => HttpResponse.json(envelope(jobFixture))),
  http.get('/api/v1/jobs/:jobId/lineage', () => HttpResponse.json(envelope(jobLineageFixture))),
  http.get('/api/v1/jobs/:jobId/quality', () => HttpResponse.json(envelope(jobQualityFixture))),
  http.get('/api/v1/ops/evidence', () => HttpResponse.json(envelope(opsEvidenceFixture))),
  http.get('/api/v1/table', ({ request }) => {
    const url = new URL(request.url);
    const eventType = url.searchParams.get('event_type');
    const rows = eventType ? tableFixture.rows.filter((row) => row.event_type === eventType) : tableFixture.rows;
    return HttpResponse.json(envelope({ ...tableFixture, total: eventType ? rows.length : 12, rows }));
  }),
  http.post('/api/v1/refresh', () => HttpResponse.json(envelope({ status: 'queued', job_id: 'job-2' }, 'refresh queued'), { status: 202 })),
];
