import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Search, SendHorizontal } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useControlledQuery } from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { useChartFilter, type DashboardFilter } from '../context/ChartFilterContext';
import {
  buildDashboardFilter,
  controlledQueryFilterField,
  CONTROLLED_QUERY_CHART_ID,
  dashboardHrefFromFilters,
  tableHrefFromFilters,
} from '../features/dashboard/filterUtils';
import { horizontalBarOption, lineOption } from '../lib/chartOptions';
import { compactDate, formatNumber } from '../lib/format';
import type { ControlledQueryResult, ControlledQueryRow, NamedValue } from '../types/api';

const DEFAULT_QUERY = '按月份统计销售额';
const DEFAULT_SUGGESTIONS = ['按月份统计销售额', '按日期统计事件量', '按类目统计购买数', '按品牌统计销售额', '按行为类型统计事件量'];

function queryChartOption(result: ControlledQueryResult | undefined): DashboardChartOption {
  if (!result?.matched || !result.rows.length) {
    return horizontalBarOption([], '结果', '#28d7c2', false);
  }
  if (result.chart.type === 'line') {
    return lineOption(
      result.rows.map((row) => ({ date: row.name, value: row.value })),
      result.chart.series_name,
      '#28d7c2',
      result.rows.length >= 7,
    );
  }
  return horizontalBarOption(
    result.rows.map((row): NamedValue => ({ name: row.name, value: row.value })),
    result.chart.series_name,
    '#f59e0b',
    result.rows.length >= 8,
  );
}

function sourceLabel(value: string | undefined | null) {
  const labels: Record<string, string> = {
    dashboard_metric_cube: '物化指标层',
    cleaned_events: '清洗后事件',
    raw_events_compatible_fallback: '原始样本回退',
    metric_cache: '指标缓存',
    not_executed: '未执行',
  };
  return labels[value ?? ''] ?? '指标缓存';
}

function engineLabel(value: string | undefined | null) {
  const labels: Record<string, string> = {
    dashboard_slice_cache: '指标切片缓存',
    top_brand_metric_cache: '品牌指标缓存',
    not_executed: '未执行',
  };
  return labels[value ?? ''] ?? '指标缓存';
}

function contractLabel(value: string | undefined | null) {
  if (value === 'controlled-natural-query/v1') return '受控查询契约 v1';
  if (value === 'dashboard-slice/v1') return '驾驶舱指标切片 v1';
  if (value === 'dashboard-metric-cube/v1') return '物化指标契约 v1';
  return value ? '数据服务契约' : '暂无契约';
}

function statusLabel(result: ControlledQueryResult | undefined, isPending: boolean) {
  if (isPending) return '识别中';
  if (!result) return '待查询';
  return result.matched ? '已识别' : '暂不支持';
}

function formatPercent(value: number | undefined) {
  return `${((value ?? 0) * 100).toLocaleString('zh-CN', { maximumFractionDigits: 1 })}%`;
}

function resultRows(result: ControlledQueryResult | undefined): ControlledQueryRow[] {
  return result?.rows ?? [];
}

type QueryFilterAction = {
  row: ControlledQueryRow;
  filter: DashboardFilter;
};

function resultFilterActions(result: ControlledQueryResult | undefined): QueryFilterAction[] {
  const field = controlledQueryFilterField(result?.intent?.dimension);
  if (!result?.matched || !field) return [];
  return resultRows(result).slice(0, 3).reduce<QueryFilterAction[]>((actions, row) => {
    const filter = buildDashboardFilter(field, String(row.raw_name ?? row.name), {
      sourceChartId: CONTROLLED_QUERY_CHART_ID,
      sourceLabel: '智能查询结果',
      affects: ['图表高亮', '组合明细', '下钻路径'],
    });
    if (filter) actions.push({ row, filter });
    return actions;
  }, []);
}

export function ControlledQueryPage() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [activeResult, setActiveResult] = useState<ControlledQueryResult>();
  const [queryError, setQueryError] = useState<Error | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const initialSubmittedRef = useRef(false);
  const controlledQuery = useControlledQuery();
  const navigate = useNavigate();
  const { setFilter } = useChartFilter();
  const result = activeResult;
  const suggestions = result?.suggestions?.length ? result.suggestions : DEFAULT_SUGGESTIONS;
  const option = useMemo(() => queryChartOption(result), [result]);
  const rows = resultRows(result);
  const filterActions = useMemo(() => resultFilterActions(result), [result]);
  const panelEmpty = Boolean(result && (!result.matched || rows.length === 0));

  const submitQuery = useCallback(async (nextQuery = query) => {
    const normalized = nextQuery.trim();
    if (!normalized) return;
    setQuery(normalized);
    setIsSubmitting(true);
    setQueryError(null);
    try {
      const data = await controlledQuery.mutateAsync(normalized);
      setActiveResult(data);
    } catch (error) {
      setQueryError(error instanceof Error ? error : new Error('查询失败'));
    } finally {
      setIsSubmitting(false);
    }
  }, [controlledQuery, query]);

  useEffect(() => {
    if (initialSubmittedRef.current) return;
    initialSubmittedRef.current = true;
    void submitQuery(DEFAULT_QUERY);
  }, [submitQuery]);

  const applyToDashboard = useCallback((filter: DashboardFilter) => {
    setFilter(filter);
    navigate(dashboardHrefFromFilters([filter], 'query'));
  }, [navigate, setFilter]);

  return (
    <>
      <section className="page-heading query-heading">
        <span className="eyebrow">智能查询</span>
        <h1>中文受控查询工作台</h1>
        <p>用中文问题触发白名单指标查询，结果优先以图表展示。</p>
      </section>

      <section className="query-console" aria-label="智能查询输入区">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submitQuery();
          }}
        >
          <label htmlFor="controlled-query-input">中文问题</label>
          <div className="query-input-row">
            <Search size={18} aria-hidden="true" />
            <input
              id="controlled-query-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：按月份统计销售额"
            />
            <button type="submit" disabled={isSubmitting || !query.trim()}>
              <SendHorizontal size={16} aria-hidden="true" />
              查询
            </button>
          </div>
        </form>
        <div className="query-suggestion-chips" aria-label="建议问题">
          {suggestions.map((item) => (
            <button type="button" key={item} onClick={() => submitQuery(item)}>
              {item}
            </button>
          ))}
        </div>
      </section>

      <section className="metrics-strip query-metrics" aria-label="查询识别摘要">
        <article className="metric-card">
          <span>识别状态</span>
          <strong>{statusLabel(result, isSubmitting)}</strong>
          <small>{result?.message ?? '正在使用默认问题生成首张图。'}</small>
        </article>
        <article className="metric-card">
          <span>指标</span>
          <strong>{result?.intent?.metric_label ?? '待识别'}</strong>
          <small>{result?.intent?.aggregation === 'sum' ? '求和聚合' : result?.intent ? '计数聚合' : '提交后显示'}</small>
        </article>
        <article className="metric-card">
          <span>维度</span>
          <strong>{result?.intent?.dimension_label ?? '待识别'}</strong>
          <small>{result?.intent?.event_type_filter_label ? `筛选：${result.intent.event_type_filter_label}` : '无额外筛选'}</small>
        </article>
        <article className="metric-card">
          <span>执行来源</span>
          <strong>{engineLabel(result?.evidence.execution_engine)}</strong>
          <small>{sourceLabel(result?.evidence.source_dataset)}</small>
        </article>
      </section>

      <section className="query-result-grid">
        <ChartPanel
          title={result?.chart.title ?? '查询结果图'}
          subtitle={result?.matched ? `${result.chart.dimension_label} × ${result.chart.metric_label}` : '选择建议问题或输入中文问题'}
          option={option}
          summary={result?.insight}
          chartId="controlled-query-result"
          annotations={[
            { label: '状态', value: statusLabel(result, isSubmitting), tone: result?.matched ? 'success' : result ? 'warning' : 'info' },
            { label: '来源', value: engineLabel(result?.evidence.execution_engine), tone: 'info' },
          ]}
          evidence={result ? <QueryEvidence result={result} /> : null}
          isLoading={isSubmitting && !result}
          error={queryError}
          isEmpty={panelEmpty}
          emptyText={result?.message ?? '暂无查询结果。'}
          actionHint="请从建议问题中选择一个受控查询。"
        />
        <section className="data-panel query-side-panel" aria-label="查询结果明细">
          <div className="panel-title">
            <div>
              <h2>结果明细</h2>
              <p>图表同源数据，列名已中文化。</p>
            </div>
          </div>
          {filterActions.length ? (
            <div className="query-drill-actions" aria-label="查询联动操作">
              <span>联动分析</span>
              {filterActions.map(({ filter, row }) => (
                <div key={`${filter.field}-${filter.value}`}>
                  <button type="button" onClick={() => applyToDashboard(filter)}>
                    应用{filter.displayValue ?? row.name}到驾驶舱
                  </button>
                  <Link to={tableHrefFromFilters([filter], 'query')}>
                    查看{filter.displayValue ?? row.name}明细
                  </Link>
                </div>
              ))}
            </div>
          ) : null}
          {rows.length ? (
            <table className="query-result-table">
              <thead>
                <tr>
                  <th>{result?.chart.dimension_label ?? '维度'}</th>
                  <th>{result?.chart.metric_label ?? '指标'}</th>
                  <th>占比</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${row.name}-${row.value}`}>
                    <td>{row.name}</td>
                    <td>{formatNumber(row.value)}</td>
                    <td>{formatPercent(row.share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="query-empty-list">
              <strong>{result?.matched === false ? '暂不支持该问法' : '暂无明细'}</strong>
              <span>{result?.message ?? '提交一个中文问题后展示结果。'}</span>
            </div>
          )}
        </section>
      </section>
    </>
  );
}

function QueryEvidence({ result }: { result: ControlledQueryResult }) {
  return (
    <dl className="query-evidence-list">
      <div>
        <dt>查询契约</dt>
        <dd>{contractLabel(result.contract_version)}</dd>
      </div>
      <div>
        <dt>数据契约</dt>
        <dd>{contractLabel(result.evidence.contract_version)}</dd>
      </div>
      <div>
        <dt>数据版本</dt>
        <dd>{result.evidence.dataset_version}</dd>
      </div>
      <div>
        <dt>生成时间</dt>
        <dd>{compactDate(result.evidence.generated_at)}</dd>
      </div>
      <div>
        <dt>耗时</dt>
        <dd>{formatNumber(result.evidence.query_ms, ' 毫秒')}</dd>
      </div>
      <div>
        <dt>结果行数</dt>
        <dd>{formatNumber(result.evidence.row_count)}</dd>
      </div>
    </dl>
  );
}
