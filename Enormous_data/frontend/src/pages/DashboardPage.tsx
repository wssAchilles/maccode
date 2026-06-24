import { useCallback, useEffect, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { RefreshCw, Table2 } from 'lucide-react';
import {
  useAnomalySummary,
  useConversionFunnel,
  useDashboardSlice,
  useDailyEvents,
  useDailySales,
  useEventDistribution,
  useExperimentSummary,
  useForecastingSummary,
  useJob,
  useOptimizationImpact,
  useRecommendationSummary,
  useRefreshJob,
  useSummary,
  useTopCategories,
} from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { MetricCard } from '../components/MetricCard';
import { useChartFilter, type DashboardFilter } from '../context/ChartFilterContext';
import { ErrorBanner } from '../components/feedback/ErrorBanner';
import { AppliedFilterBar } from '../features/dashboard/AppliedFilterBar';
import { ChartActionChips, type ChartActionChip } from '../features/dashboard/ChartActionChips';
import { DashboardStatusBar, type DashboardStatusItem, type DashboardStatusTone } from '../features/dashboard/DashboardStatusBar';
import {
  buildDashboardFilter,
  CATEGORY_CHART_ID,
  EVENT_CHART_ID,
  filterDisplayValue,
  filterLabel,
  filtersEqual,
  filtersToSearchParams,
  parseFiltersFromSearchParams,
  rawChartName,
  sourceChartLabel,
  tableHrefFromFilters,
  type DashboardFilterField,
} from '../features/dashboard/filterUtils';
import {
  comparisonHorizontalBarOption,
  comparisonLineOption,
  horizontalBarOption,
  lineOption,
  pieOption,
  type LineChartAnnotation,
} from '../lib/chartOptions';
import { compactDate, formatCurrency, formatNumber } from '../lib/format';
import { displayValue, label, statusLabel } from '../i18n/displayText';
import type { DashboardSliceEvidence } from '../types/api';
import type { ECElementEvent } from 'echarts/core';

function topNamedValue(rows: Array<{ name: string; value: number }> = []) {
  return rows.reduce<{ name: string; value: number } | null>((best, row) => (!best || row.value > best.value ? row : best), null);
}

function topDateValue(rows: Array<{ date: string; value: number }> = []) {
  return rows.reduce<{ date: string; value: number } | null>((best, row) => (!best || row.value > best.value ? row : best), null);
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function statusTone(status?: string | null): DashboardStatusTone {
  const value = status ?? 'pending';
  if (['passed', 'succeeded', 'success', 'healthy', 'ready', 'optimal'].includes(value)) return 'success';
  if (['running', 'queued'].includes(value)) return 'running';
  if (['failed', 'rejected', 'danger', 'critical', 'blocked_by_srm'].includes(value)) return 'danger';
  return 'warning';
}

function gateStatus(tone: DashboardStatusTone) {
  if (tone === 'success') return '已通过';
  if (tone === 'danger') return '已阻断';
  if (tone === 'running') return '运行中';
  return '需复核';
}

type GateRow = {
  name: string;
  status: string;
  tone: DashboardStatusTone;
  detail: string;
};

export function DashboardPage() {
  const summary = useSummary();
  const funnel = useConversionFunnel();
  const events = useEventDistribution();
  const dailyEvents = useDailyEvents();
  const dailySales = useDailySales();
  const categories = useTopCategories();
  const job = useJob();
  const refresh = useRefreshJob();
  const recommendation = useRecommendationSummary();
  const anomaly = useAnomalySummary();
  const forecasting = useForecastingSummary();
  const experiments = useExperimentSummary();
  const optimizationImpact = useOptimizationImpact();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchKey = searchParams.toString();
  const hydratedFromUrlRef = useRef(false);
  const lastWrittenSearchRef = useRef<string | null>(null);
  const skipNextUrlWriteRef = useRef(false);
  const { activeFilters, applyFilters, toggleFilter, clearFilter } = useChartFilter();
  const activeFiltersRef = useRef<DashboardFilter[]>(activeFilters);
  const eventFilter = activeFilters.find((filter) => filter.field === 'event_type');
  const categoryFilter = activeFilters.find((filter) => filter.field === 'category_level1');
  const brandFilter = activeFilters.find((filter) => filter.field === 'brand');
  const hasTableFilter = Boolean(eventFilter || categoryFilter || brandFilter);
  const dashboardSliceParams = useMemo(
    () => ({
      event_type: eventFilter?.value,
      category_level1: categoryFilter?.value,
      brand: brandFilter?.value,
    }),
    [brandFilter?.value, categoryFilter?.value, eventFilter?.value],
  );
  const dashboardSlice = useDashboardSlice(dashboardSliceParams);
  const sliceData = hasTableFilter ? dashboardSlice.data : undefined;
  const error = summary.error || funnel.error || events.error || dailyEvents.error || dailySales.error || categories.error || dashboardSlice.error;
  const visibleEventRows = sliceData && !eventFilter ? sliceData.event_type_count : events.data;
  const topEvent = topNamedValue(visibleEventRows);
  const peakEvents = topDateValue(sliceData?.daily_events ?? dailyEvents.data);
  const peakSales = topDateValue(sliceData?.daily_sales ?? dailySales.data);
  const topCategory = topNamedValue(sliceData?.top_categories ?? categories.data);
  const tableHref = tableHrefFromFilters(activeFilters);
  const tableLinkLabel = hasTableFilter ? '查看组合明细' : '查看全部明细';

  useEffect(() => {
    activeFiltersRef.current = activeFilters;
  }, [activeFilters]);

  useEffect(() => {
    const parsedFilters = parseFiltersFromSearchParams(searchParams);
    if (!hydratedFromUrlRef.current) {
      hydratedFromUrlRef.current = true;
      if (!filtersEqual(parsedFilters, activeFiltersRef.current)) {
        skipNextUrlWriteRef.current = true;
        applyFilters(parsedFilters);
      }
      return;
    }
    if (lastWrittenSearchRef.current === searchKey) return;
    if (!filtersEqual(parsedFilters, activeFiltersRef.current)) {
      skipNextUrlWriteRef.current = true;
      applyFilters(parsedFilters);
    }
  }, [applyFilters, searchKey, searchParams]);

  useEffect(() => {
    if (!hydratedFromUrlRef.current) return;
    if (skipNextUrlWriteRef.current) {
      skipNextUrlWriteRef.current = false;
      return;
    }
    const nextParams = filtersToSearchParams(activeFilters, searchParams);
    const nextKey = nextParams.toString();
    if (nextKey === searchKey) return;
    lastWrittenSearchRef.current = nextKey;
    setSearchParams(nextParams, { replace: true });
  }, [activeFilters, searchKey, searchParams, setSearchParams]);

  const gateRows = useMemo<GateRow[]>(() => {
    const anomalyTone = anomaly.data?.critical_count
      ? 'danger'
      : anomaly.data?.warning_count
        ? 'warning'
        : statusTone(anomaly.data?.radar_status);
    // 预测窗口门禁状态：以后端质量门禁结果 quality_status 为准，与需求预测页面保持一致
    const forecastTone = statusTone(forecasting.data?.quality_status ?? 'pending');
    return [
      {
        name: 'Spark 作业',
        status: statusLabel(job.data?.status ?? 'pending'),
        tone: statusTone(job.data?.status),
        detail: compactDate(job.data?.finished_at ?? job.data?.started_at),
      },
      {
        name: '数据质量',
        status: statusLabel(job.data?.quality_status ?? (summary.data ? 'passed' : 'pending')),
        tone: statusTone(job.data?.quality_status ?? (summary.data ? 'passed' : 'pending')),
        detail: `${formatNumber(summary.data?.cleaned_rows)} 条有效事件`,
      },
      {
        name: '推荐发布',
        status: statusLabel(recommendation.data?.quality_status ?? 'pending'),
        tone: statusTone(recommendation.data?.quality_status),
        detail: `兜底 ${percent(recommendation.data?.fallback_rate)}`,
      },
      {
        name: '异常雷达',
        status: anomaly.data?.critical_count ? '严重' : anomaly.data?.warning_count ? '警告' : statusLabel(anomaly.data?.radar_status ?? 'pending'),
        tone: anomalyTone,
        detail: `${formatNumber(anomaly.data?.critical_count)} 个严重告警`,
      },
      {
        name: '预测质量',
        status: gateStatus(forecastTone),
        tone: forecastTone,
        detail: `${formatNumber(forecasting.data?.risk_count)} 个预测风险`,
      },
      {
        name: '实验护栏',
        status: statusLabel(experiments.data?.guardrail_status ?? 'pending'),
        tone: statusTone(experiments.data?.guardrail_status),
        detail: `${formatNumber(experiments.data?.assigned_users)} 个已分流用户`,
      },
    ];
  }, [anomaly.data, experiments.data, forecasting.data, job.data, recommendation.data, summary.data]);

  const gatePassCount = gateRows.filter((row) => row.tone === 'success').length;
  const gatePassRate = gateRows.length ? gatePassCount / gateRows.length : 0;
  const latestRun = job.data?.run_id ?? job.data?.job_id ?? '暂无运行';
  const statusItems: DashboardStatusItem[] = [
    {
      label: '最近运行',
      value: statusLabel(job.data?.status ?? 'pending'),
      detail: `${latestRun.slice(0, 18)} · ${compactDate(job.data?.finished_at ?? job.data?.started_at)}`,
      tone: statusTone(job.data?.status),
      href: '/ops',
    },
    {
      label: '数据质量',
      value: statusLabel(job.data?.quality_status ?? (summary.data ? 'passed' : 'pending')),
      detail: `${formatNumber(summary.data?.removed_rows)} 条被清洗剔除`,
      tone: statusTone(job.data?.quality_status ?? (summary.data ? 'passed' : 'pending')),
      href: '/quality',
    },
    {
      label: '推荐发布',
      value: statusLabel(recommendation.data?.quality_status ?? 'pending'),
      detail: `${formatNumber(recommendation.data?.recommendation_count)} 条推荐`,
      tone: statusTone(recommendation.data?.quality_status),
      href: '/recommendations',
    },
    {
      label: '异常雷达',
      value: gateRows[3]?.status ?? '待生成',
      detail: `${formatNumber(anomaly.data?.alert_count)} 个告警`,
      tone: gateRows[3]?.tone ?? 'warning',
      href: '/anomalies',
    },
    {
      label: '预测窗口',
      value: gateStatus(gateRows[4]?.tone ?? 'warning'),
      detail: `${formatNumber(forecasting.data?.forecast_horizon_days)} 天预测`,
      tone: gateRows[4]?.tone ?? 'warning',
      href: '/forecasting',
    },
    {
      label: '实验护栏',
      value: statusLabel(experiments.data?.guardrail_status ?? 'pending'),
      detail: `${formatNumber(experiments.data?.experiment_count)} 个实验`,
      tone: statusTone(experiments.data?.guardrail_status),
      href: '/experiments',
    },
  ];

  const eventChips: ChartActionChip[] = (events.data ?? []).slice(0, 5).map((row) => ({
    field: 'event_type',
    value: row.name,
    label: filterLabel('event_type', row.name),
    sourceChartId: EVENT_CHART_ID,
    sourceLabel: '行为类型分布',
    displayValue: filterDisplayValue('event_type', row.name),
    interactionMode: 'filter',
    affects: ['图表高亮', '组合明细', '下钻路径'],
    count: row.value,
  }));
  const categoryChips: ChartActionChip[] = (categories.data ?? []).slice(0, 5).map((row) => ({
    field: 'category_level1',
    value: row.name,
    label: filterLabel('category_level1', row.name),
    sourceChartId: CATEGORY_CHART_ID,
    sourceLabel: '类目排行',
    displayValue: filterDisplayValue('category_level1', row.name),
    interactionMode: 'filter',
    affects: ['图表高亮', '组合明细', '下钻路径'],
    count: row.value,
  }));
  const funnelRows = (funnel.data?.steps ?? []).map((step) => ({ name: step.step, value: step.sessions }));
  const latestSalesDate = dailySales.data?.[dailySales.data.length - 1]?.date;
  const salesAnnotations = useMemo<LineChartAnnotation[]>(() => {
    const rows: LineChartAnnotation[] = [];
    if (peakSales) {
      rows.push({ date: peakSales.date, value: peakSales.value, label: '成交峰值', kind: 'point', tone: 'success' });
    }
    if (peakSales && (anomaly.data?.critical_count || anomaly.data?.warning_count)) {
      rows.push({
        date: peakSales.date,
        value: peakSales.value,
        label: anomaly.data?.critical_count ? '严重异常' : '异常观察',
        kind: 'point',
        tone: anomaly.data?.critical_count ? 'danger' : 'warning',
      });
    }
    if (latestSalesDate && forecasting.data?.risk_count) {
      rows.push({ date: latestSalesDate, label: '预测风险', kind: 'line', tone: 'warning' });
    }
    if (latestSalesDate && job.data?.run_id) {
      rows.push({ date: latestSalesDate, label: 'Spark 刷新', kind: 'line', tone: 'info' });
    }
    return rows;
  }, [anomaly.data?.critical_count, anomaly.data?.warning_count, forecasting.data?.risk_count, job.data?.run_id, latestSalesDate, peakSales]);
  const salesAnnotationBadges = salesAnnotations.map((item) => ({
    label: item.label,
    value: item.kind === 'point' && typeof item.value === 'number' ? formatCurrency(item.value) : item.date,
    tone: item.tone,
  }));
  const activeFilterNames = activeFilters.map((filter) => filter.label).join('、');
  const recalculatedChartCount = sliceData ? 3 : 0;
  const coverageText = sliceData ? percent(sliceData.evidence.coverage_rate) : '待生成';
  const dashboardFilterNotice = activeFilters.length
    ? dashboardSlice.isFetching
      ? `正在按 ${activeFilterNames} 重新计算核心图表；明细页已继承该筛选。`
      : sliceData
        ? `已按 ${activeFilterNames} 重新计算 ${recalculatedChartCount} 张图；筛选样本覆盖 ${coverageText}，明细页继承该筛选。`
        : `当前筛选：${activeFilterNames}。明细页已继承该筛选，核心图表等待重新计算。`
    : undefined;
  const funnelFilterNotice = activeFilters.length
    ? '行为漏斗暂保留全量会话口径，避免用事件行粗算会话转化。'
    : undefined;
  const eventChartNotice = eventFilter
    ? `已选中${eventFilter.label}；组合明细将带入该行为筛选。`
    : sliceData
      ? `已按 ${activeFilterNames} 重新计算行为结构。`
      : '点击扇区或使用下方按钮筛选行为。';
  const categoryChartNotice = categoryFilter
    ? `已选中${categoryFilter.label}；组合明细将带入该类目筛选。`
    : sliceData
      ? `已按 ${activeFilterNames} 重新计算类目排行。`
      : '点击柱形或使用下方按钮筛选类目。';
  const sliceEvidence = sliceData ? <DashboardSliceEvidencePanel evidence={sliceData.evidence} tableHref={tableHref} /> : undefined;

  const handleChartFilter = useCallback(
    (field: DashboardFilterField, sourceChartId: string) => (params: ECElementEvent) => {
      const selectedName = rawChartName(params);
      if (!selectedName) return;
      const filter = buildDashboardFilter(field, selectedName, {
        sourceChartId,
        sourceLabel: sourceChartLabel(sourceChartId),
      });
      if (filter) toggleFilter(filter);
    },
    [toggleFilter],
  );

  return (
    <>
      <ErrorBanner error={error} />
      <section className="page-heading dashboard-heading">
        <span className="eyebrow">数据驾驶舱</span>
        <h1>电商行为分析驾驶舱</h1>
        <p>先看运行可信度和核心业务走势，再通过图表筛选进入明细与算法模块。</p>
      </section>

      <DashboardStatusBar
        items={statusItems}
        actions={(
          <>
            <button className="primary-action compact" onClick={() => refresh.mutate()} disabled={refresh.isPending} type="button">
              <RefreshCw size={18} className={refresh.isPending ? 'spin' : ''} />
              {refresh.isPending ? '启动中' : '刷新 Spark 计算'}
            </button>
            <Link className="secondary-action compact" to={tableHref}>
              <Table2 size={18} />
              {tableLinkLabel}
            </Link>
          </>
        )}
      />

      <section className="metrics-strip">
        <MetricCard label="成交额" value={formatCurrency(summary.data?.total_sales ?? funnel.data?.totals.revenue)} detail="购买行为金额合计" tone="success" />
        <MetricCard label="会话购买转化率" value={percent(funnel.data?.totals.view_to_purchase_rate)} detail="购买会话 / 浏览会话" tone="warning" />
        <MetricCard label="有效会话" value={formatNumber(funnel.data?.totals.sessions ?? summary.data?.unique_sessions)} detail={`${formatNumber(summary.data?.unique_users)} 个去重用户`} />
        <MetricCard label="智能门禁通过率" value={percent(gatePassRate)} detail={`${gatePassCount}/${gateRows.length} 个门禁通过`} tone={gatePassRate >= 0.8 ? 'success' : gatePassRate >= 0.5 ? 'warning' : 'danger'} />
      </section>

      <AppliedFilterBar
        filters={activeFilters}
        onClear={clearFilter}
        action={
          hasTableFilter ? (
            <Link className="secondary-action compact applied-filter-action" to={tableHref}>
              查看组合明细
            </Link>
          ) : null
        }
      />

      <section className="dashboard-primary-grid">
        <div className="dashboard-main-chart">
          <ChartPanel
            chartId="dashboard-sales-trend"
            title="成交额主趋势"
            subtitle="以销售额为主线观察业务波动，异常与预测信号在右侧门禁区联动"
            option={
              sliceData
                ? comparisonLineOption(dailySales.data ?? [], sliceData.daily_sales, '销售额', '#f59e0b', salesAnnotations)
                : lineOption(dailySales.data ?? [], '销售额', '#f59e0b', true, salesAnnotations)
            }
            filterNotice={dashboardFilterNotice}
            annotations={salesAnnotationBadges}
            evidence={sliceEvidence}
            summary={
              peakSales
                ? `${peakSales.date} 销售额最高，为 ${formatCurrency(peakSales.value)}。${sliceData ? '图中已叠加当前筛选与全量对照。' : eventFilter ? `当前筛选为${eventFilter.label}。` : ''}`
                : '等待每日销售额数据。'
            }
          />
        </div>
        <ChartPanel
          chartId={EVENT_CHART_ID}
          title="行为类型分布"
          subtitle="浏览、加购、移除购物车和购买的结构占比"
          option={pieOption(visibleEventRows ?? [])}
          filterNotice={eventChartNotice}
          summary={topEvent ? `${displayValue(topEvent.name, 'eventType')} 占比最高，共 ${formatNumber(topEvent.value)} 次。` : '等待行为类型数据。'}
          onChartClick={handleChartFilter('event_type', EVENT_CHART_ID)}
          actions={<ChartActionChips label="行为类型键盘筛选" chips={eventChips} activeFilters={activeFilters} onToggle={toggleFilter} />}
        />
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          chartId="dashboard-event-trend"
          title="每日事件趋势"
          subtitle="按日期聚合后的用户行为量，用于观察流量强弱"
          option={
            sliceData
              ? comparisonLineOption(dailyEvents.data ?? [], sliceData.daily_events, '事件量', '#39d0c8')
              : lineOption(dailyEvents.data ?? [], '事件量', '#39d0c8')
          }
          filterNotice={dashboardFilterNotice}
          evidence={sliceEvidence}
          summary={peakEvents ? `${peakEvents.date} 达到事件峰值 ${formatNumber(peakEvents.value)}。` : '等待每日事件趋势数据。'}
        />
        <ChartPanel
          chartId={CATEGORY_CHART_ID}
          title="类目排行"
          subtitle="按一级类目事件量排序，点击或使用按钮进入类目上下文"
          option={
            sliceData
              ? comparisonHorizontalBarOption(categories.data ?? [], sliceData.top_categories, '事件量', '#7cdaff')
              : horizontalBarOption(categories.data ?? [], '事件量', '#7cdaff', true)
          }
          filterNotice={categoryChartNotice}
          evidence={sliceEvidence}
          summary={topCategory ? `${displayValue(topCategory.name)} 是当前最高事件类目，共 ${formatNumber(topCategory.value)} 次。${sliceData ? '图中已叠加当前筛选与全量对照。' : categoryFilter ? `当前筛选为${categoryFilter.label}。` : ''}` : '等待类目排行数据。'}
          onChartClick={handleChartFilter('category_level1', CATEGORY_CHART_ID)}
          actions={<ChartActionChips label="类目键盘筛选" chips={categoryChips} activeFilters={activeFilters} onToggle={toggleFilter} />}
        />
        <ChartPanel
          chartId="dashboard-funnel"
          title="行为漏斗"
          subtitle="用会话口径展示浏览、加购、购买递进"
          option={horizontalBarOption(funnelRows, '会话数', '#56d27b')}
          isEmpty={!funnelRows.length}
          filterNotice={funnelFilterNotice}
          summary={funnel.data ? `浏览到购买转化率 ${percent(funnel.data.totals.view_to_purchase_rate)}，客单价 ${formatCurrency(funnel.data.totals.avg_order_value)}。` : '等待会话漏斗数据。'}
        />
        <AlgorithmGateMatrix rows={gateRows} impactStatus={optimizationImpact.data?.overall_status} />
      </section>
    </>
  );
}

function DashboardSliceEvidencePanel({ evidence, tableHref }: { evidence: DashboardSliceEvidence; tableHref: string }) {
  const cacheHit = evidence.cache_hit === true;
  const cacheLabel = cacheHit ? '物化层命中' : '明细扫描降级';
  const modeLabel = evidence.cache_mode ? displayValue(evidence.cache_mode, 'source') : cacheHit ? '物化指标层' : '明细扫描';
  const fallbackReason = evidence.fallback_reason ? label('reason', evidence.fallback_reason) : null;
  const metricDefinitions = (evidence.metric_definitions ?? []).slice(0, 4);
  const pathSteps = cacheHit
    ? ['清洗后事件', '物化指标层', '接口服务', '图表视图']
    : ['清洗后事件', '明细扫描', '接口服务', '图表视图'];

  return (
    <div className="chart-evidence-content" aria-label="筛选计算证据">
      <div className={`chart-evidence-mode ${cacheHit ? 'is-hit' : 'is-fallback'}`}>
        <strong>{cacheLabel}</strong>
        <span>{modeLabel} · {evidence.metric_grain ?? '明细事件扫描'}</span>
      </div>
      <div className="chart-evidence-path" aria-label="筛选计算链路">
        {pathSteps.map((step) => (
          <span key={step}>{step}</span>
        ))}
      </div>
      <div className="chart-evidence-grid">
        <span>
          <strong>{formatNumber(evidence.filtered_row_count)}</strong>
          <small>筛选样本</small>
        </span>
        <span>
          <strong>{formatNumber(evidence.total_row_count)}</strong>
          <small>全量样本</small>
        </span>
        <span>
          <strong>{percent(evidence.coverage_rate)}</strong>
          <small>样本覆盖</small>
        </span>
        <span>
          <strong>{evidence.query_ms.toFixed(1)} 毫秒</strong>
          <small>查询耗时</small>
        </span>
      </div>
      {metricDefinitions.length ? (
        <div className="chart-evidence-metrics" aria-label="指标口径">
          {metricDefinitions.map((definition) => (
            <span key={definition.metric_name}>
              <strong>{definition.chinese_name ?? displayValue(definition.metric_name, 'metric')}</strong>
              <small>{definition.formula ?? definition.aggregation ?? '统一指标口径'}</small>
            </span>
          ))}
        </div>
      ) : null}
      <div className="chart-evidence-meta">
        <span>计算方式：{cacheLabel}</span>
        <span>数据源：{displayValue(evidence.source_dataset, 'lineage')}</span>
        {fallbackReason ? <span>降级原因：{fallbackReason}</span> : null}
        {typeof evidence.cube_row_count === 'number' ? <span>物化行数：{formatNumber(evidence.cube_row_count)}</span> : null}
        <span>运行批次：{evidence.run_id}</span>
        <span>数据版本：{evidence.dataset_version}</span>
        <span>刷新时间：{compactDate(evidence.refreshed_at ?? evidence.generated_at)}</span>
        {typeof evidence.spark_duration === 'number' ? <span>Spark 耗时：{evidence.spark_duration.toFixed(1)} 秒</span> : null}
        <Link className="secondary-action compact" to={tableHref}>
          查看筛选明细
        </Link>
      </div>
    </div>
  );
}

function AlgorithmGateMatrix({ impactStatus, rows }: { impactStatus?: string; rows: GateRow[] }) {
  return (
    <article className="data-panel dashboard-gate-panel">
      <div className="panel-title">
        <div>
          <h2>智能门禁矩阵</h2>
          <p>汇总数据、推荐、预测、实验、异常和 Spark 运行状态。</p>
        </div>
      </div>
      <div className="dashboard-gate-matrix" role="list" aria-label="智能算法门禁状态">
        {rows.map((row) => (
          <div className={`dashboard-gate-row tone-${row.tone}`} role="listitem" key={row.name}>
            <span>{row.name}</span>
            <strong>{row.status}</strong>
            <small>{row.detail}</small>
          </div>
        ))}
      </div>
      <p className="chart-summary">
        {impactStatus ? `前端优化影响状态：${statusLabel(impactStatus)}。` : '等待优化影响证据。'}
      </p>
    </article>
  );
}
