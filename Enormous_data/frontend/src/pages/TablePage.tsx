import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTable, useTopBrands, useTopCategories } from '../api/hooks';
import { DataTable, type TableSortDirection, type TableSortKey } from '../components/DataTable';
import { ErrorBanner } from '../components/feedback/ErrorBanner';
import { useChartFilter } from '../context/ChartFilterContext';
import {
  FILTER_FIELDS,
  TABLE_FILTER_CHART_ID,
  filterLabel,
  normalizedFilterValue,
  sourceChartLabel,
  type DashboardFilterField,
} from '../features/dashboard/filterUtils';
import { displayValue } from '../i18n/displayText';
import { formatNumber } from '../lib/format';
import type { TableRow } from '../types/api';

function csvCell(value: string | number | null | undefined) {
  const text = String(value ?? '');
  return `"${text.replace(/"/g, '""')}"`;
}

function normalizedEventType(value: string | null | undefined) {
  return normalizedFilterValue('event_type', value);
}

function normalizedText(value: string | null | undefined) {
  return value?.trim() ?? '';
}

function filterFieldName(field: DashboardFilterField) {
  if (field === 'event_type') return '行为';
  if (field === 'category_level1') return '类目';
  return '品牌';
}

export function TablePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeFilters, clearFilter, setFilter } = useChartFilter();
  const categories = useTopCategories();
  const brands = useTopBrands();
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<TableSortKey>('event_time');
  const [sortDirection, setSortDirection] = useState<TableSortDirection>('desc');
  const [selectedRow, setSelectedRow] = useState<TableRow | null>(null);
  const urlEventType = normalizedEventType(searchParams.get('event_type'));
  const contextEventFilter = activeFilters.find((filter) => filter.field === 'event_type');
  const contextEventType = normalizedEventType(contextEventFilter?.value);
  const urlCategory = normalizedText(searchParams.get('category_level1'));
  const contextCategoryFilter = activeFilters.find((filter) => filter.field === 'category_level1');
  const contextCategory = normalizedText(contextCategoryFilter?.value);
  const urlBrand = normalizedText(searchParams.get('brand'));
  const contextBrandFilter = activeFilters.find((filter) => filter.field === 'brand');
  const contextBrand = normalizedText(contextBrandFilter?.value);
  const eventType = urlEventType || contextEventType;
  const categoryLevel1 = urlCategory || contextCategory;
  const brand = urlBrand || contextBrand;
  const source = searchParams.get('source');
  const firstContextSource = contextCategoryFilter?.sourceChartId || contextEventFilter?.sourceChartId || contextBrandFilter?.sourceChartId || '';
  const sourceChart = searchParams.get('sourceChart') || firstContextSource;
  const sourceLabel = source === 'query'
    ? '智能查询结果'
    : source === 'dashboard' || (!urlEventType && !urlCategory && !urlBrand && firstContextSource)
      ? '首页图表筛选'
      : source === 'table'
        ? '表格筛选'
        : '筛选控件';
  const sourceDetail = sourceChartLabel(sourceChart);
  const sourceText = sourceDetail === sourceLabel ? sourceLabel : `${sourceLabel} · ${sourceDetail}`;
  const activeTableFilters = [
    eventType ? { field: 'event_type' as const, value: eventType, label: filterLabel('event_type', eventType) } : null,
    categoryLevel1 ? { field: 'category_level1' as const, value: categoryLevel1, label: filterLabel('category_level1', categoryLevel1) } : null,
    brand ? { field: 'brand' as const, value: brand, label: filterLabel('brand', brand) } : null,
  ].filter((item): item is { field: DashboardFilterField; value: string; label: string } => Boolean(item));
  const rangeLabel = activeTableFilters.length ? activeTableFilters.map((filter) => filter.label).join(' · ') : '全部行为';
  const loadingRange = activeTableFilters.length ? activeTableFilters.map((filter) => filter.label.replace(/^[^：]+：/, '')).join(' · ') : '行为记录';
  const table = useTable({
    page,
    size: pageSize,
    event_type: eventType || undefined,
    category_level1: categoryLevel1 || undefined,
    brand: brand || undefined,
  });
  const tableSourceNote = table.data?.source_dataset === 'cleaned_events'
    ? '本页读取 Spark 清洗后的明细快照，与首页指标使用同一清洗口径。'
    : '当前未检测到 Spark 清洗明细快照，暂用原始 CSV 兼容回退；运行 Spark 刷新后将切换为清洗口径。';
  const filterNote = activeTableFilters.length
    ? `仅展示命中当前组合筛选的明细；${tableSourceNote}首页趋势、漏斗和成交额仍为全量 Spark 聚合口径。`
    : `展示全部明细；选择行为、一级类目或品牌后可追溯构成事件。${tableSourceNote}`;
  const emptyText = activeTableFilters.length
    ? '当前组合筛选下没有行为记录。可清除类目、品牌或行为类型后重试。'
    : '暂无匹配的行为记录。';
  const loadingText = activeTableFilters.length ? `正在加载${loadingRange}明细` : '正在加载行为记录';
  const pageSubtitle = activeTableFilters.length ? '按行为、类目和品牌组合追溯明细。' : '按行为、类目和品牌筛选明细。';

  const exportFileName = useMemo(() => {
    const suffix = [eventType, categoryLevel1, brand].filter(Boolean).join('-') || 'all';
    return `events-${suffix}-page-${page}.csv`;
  }, [brand, categoryLevel1, eventType, page]);

  useEffect(() => {
    setPage(1);
    setSelectedRow(null);
  }, [brand, categoryLevel1, eventType]);

  function updateSearchFilter(field: DashboardFilterField, value: string) {
    setPage(1);
    setSelectedRow(null);
    const nextParams = new URLSearchParams(searchParams);
    if (!value) {
      clearFilter(field);
      nextParams.delete(field);
      const hasRemainingFilter = FILTER_FIELDS.some((currentField) => currentField !== field && Boolean(normalizedText(nextParams.get(currentField))));
      if (!hasRemainingFilter) {
        nextParams.delete('source');
        nextParams.delete('sourceChart');
      }
      setSearchParams(nextParams);
      return;
    }
    const normalizedValue = field === 'event_type' ? normalizedEventType(value) : normalizedText(value);
    if (!normalizedValue) return;
    setFilter({ field, value: normalizedValue, label: filterLabel(field, normalizedValue), sourceChartId: TABLE_FILTER_CHART_ID });
    nextParams.set(field, normalizedValue);
    nextParams.set('source', 'table');
    nextParams.delete('sourceChart');
    setSearchParams(nextParams);
  }

  function clearAllTableFilters() {
    setPage(1);
    setSelectedRow(null);
    FILTER_FIELDS.forEach((field) => clearFilter(field));
    const nextParams = new URLSearchParams(searchParams);
    FILTER_FIELDS.forEach((field) => nextParams.delete(field));
    nextParams.delete('source');
    nextParams.delete('sourceChart');
    setSearchParams(nextParams);
  }

  function onSort(key: TableSortKey) {
    if (sortKey === key) {
      setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  }

  function exportCurrentPage() {
    const rows = table.data?.rows ?? [];
    const header = ['event_time', 'event_type', 'product_id', 'category_code', 'brand', 'price', 'user_id'];
    const csv = [header.join(','), ...rows.map((row) => header.map((key) => csvCell(row[key as keyof TableRow])).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = exportFileName;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">原始行为明细</span>
        <h1>行为明细查询</h1>
        <p>{pageSubtitle}当前页面用于明细行追溯，不替代首页 Spark 聚合指标重算。</p>
      </section>
      <ErrorBanner error={table.error} />
      <section className="drillthrough-bar" aria-label="当前明细范围">
        <div>
          <span>当前明细范围</span>
          <strong>{rangeLabel}</strong>
          <small>{sourceText}</small>
        </div>
        <p>{filterNote}</p>
        {activeTableFilters.length ? (
          <div className="drillthrough-filter-chips" aria-label="当前组合筛选">
            {activeTableFilters.map((filter) => (
              <button type="button" key={filter.field} onClick={() => updateSearchFilter(filter.field, '')}>
                清除{filter.label}
              </button>
            ))}
          </div>
        ) : null}
        <div className="drillthrough-actions">
          <Link className="secondary-action compact" to="/">
            返回驾驶舱
          </Link>
          {activeTableFilters.length ? (
            <button className="secondary-action compact" type="button" onClick={clearAllTableFilters}>
              清除全部筛选
            </button>
          ) : null}
        </div>
      </section>
      <section className="toolbar">
        <div className="toolbar-controls">
          <label>
            <span>行为类型</span>
            <select
              aria-label="行为类型"
              name="event_type"
              value={eventType}
              onChange={(event) => {
                updateSearchFilter('event_type', event.target.value);
              }}
            >
              <option value="">全部行为</option>
              <option value="view">浏览</option>
              <option value="cart">加购</option>
              <option value="remove_from_cart">移出购物车</option>
              <option value="purchase">购买</option>
            </select>
          </label>
          <label>
            <span>一级类目</span>
            <input
              aria-label="一级类目"
              className="text-input"
              list="table-category-options"
              name="category_level1"
              placeholder="全部类目"
              value={categoryLevel1}
              onChange={(event) => updateSearchFilter('category_level1', event.target.value)}
            />
            <datalist id="table-category-options">
              {(categories.data ?? []).map((row) => (
                <option value={row.name} key={row.name}>{row.name}</option>
              ))}
            </datalist>
          </label>
          <label>
            <span>品牌</span>
            <input
              aria-label="品牌"
              className="text-input"
              list="table-brand-options"
              name="brand"
              placeholder="全部品牌"
              value={brand}
              onChange={(event) => updateSearchFilter('brand', event.target.value)}
            />
            <datalist id="table-brand-options">
              {(brands.data ?? []).map((row) => (
                <option value={row.name} key={row.name}>{displayValue(row.name)}</option>
              ))}
            </datalist>
          </label>
          <label>
            <span>每页行数</span>
            <select
              aria-label="每页行数"
              name="page_size"
              value={pageSize}
              onChange={(event) => {
                setPage(1);
                setSelectedRow(null);
                setPageSize(Number(event.target.value));
              }}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </label>
        </div>
        <div className="toolbar-summary">
          <span>{table.isLoading ? '加载中' : `共 ${formatNumber(table.data?.total)} 条`}</span>
          <button className="secondary-action compact" type="button" disabled={!table.data?.rows.length} onClick={exportCurrentPage}>
            导出当前页
          </button>
        </div>
      </section>
      {selectedRow ? (
        <section className="row-inspector" aria-label="选中行为摘要">
          <strong>{displayValue(selectedRow.event_type, 'eventType')}</strong>
          <span>商品 ID {selectedRow.product_id}</span>
          <span>一级类目 {displayValue(selectedRow.category_level1)}</span>
          <span>原始类目 {displayValue(selectedRow.category_code)}</span>
          <span>品牌 {displayValue(selectedRow.brand)}</span>
          <span>价格 {selectedRow.price}</span>
          <span>用户 ID {selectedRow.user_id}</span>
          <span>会话 {selectedRow.user_session}</span>
          <span>{selectedRow.event_time}</span>
          {activeTableFilters.length ? <span>命中：{activeTableFilters.map((filter) => filterFieldName(filter.field)).join('、')}</span> : null}
        </section>
      ) : null}
      <DataTable
        data={table.data ?? null}
        emptyText={emptyText}
        isLoading={table.isLoading}
        loadingText={loadingText}
        onInspectRow={setSelectedRow}
        onSort={onSort}
        sortDirection={sortDirection}
        sortKey={sortKey}
      />
      <div className="pagination">
        <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
        <span>第 {page} 页</span>
        <button type="button" disabled={!!table.data && page * table.data.size >= table.data.total} onClick={() => setPage((value) => value + 1)}>下一页</button>
      </div>
    </>
  );
}
