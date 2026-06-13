import type { ECElementEvent } from 'echarts/core';
import type { DashboardFilter } from '../../context/ChartFilterContext';
import { displayValue } from '../../i18n/displayText';

export const EVENT_CHART_ID = 'dashboard-event-structure';
export const CATEGORY_CHART_ID = 'dashboard-category-ranking';
export const CONTROLLED_QUERY_CHART_ID = 'controlled-query-result';
export const TABLE_FILTER_CHART_ID = 'table-filter';
export const URL_FILTER_CHART_ID = 'url-filter';
export const FILTER_FIELDS = ['event_type', 'category_level1', 'brand'] as const;

const EVENT_TYPES = ['view', 'cart', 'remove_from_cart', 'purchase'] as const;

export type DashboardFilterField = (typeof FILTER_FIELDS)[number];

type BuildFilterOptions = {
  sourceChartId?: string;
  sourceLabel?: string;
  affects?: string[];
};

export function rawChartName(params: ECElementEvent) {
  const data = params.data;
  if (data && typeof data === 'object' && 'rawName' in data) {
    const rawName = (data as { rawName?: unknown }).rawName;
    if (rawName !== undefined && rawName !== null) {
      return String(rawName);
    }
  }
  return params.name ? String(params.name) : '';
}

export function isDashboardFilterField(value: string | null | undefined): value is DashboardFilterField {
  return FILTER_FIELDS.includes(value as DashboardFilterField);
}

export function normalizedFilterValue(field: DashboardFilterField, value: string | null | undefined) {
  const normalized = value?.trim() ?? '';
  if (!normalized) return '';
  if (field === 'event_type' && !EVENT_TYPES.includes(normalized as (typeof EVENT_TYPES)[number])) return '';
  return normalized;
}

export function sourceChartLabel(value: string | null | undefined) {
  if (value === EVENT_CHART_ID) return '行为类型分布';
  if (value === CATEGORY_CHART_ID) return '类目排行';
  if (value === CONTROLLED_QUERY_CHART_ID) return '智能查询结果';
  if (value === TABLE_FILTER_CHART_ID) return '表格筛选';
  if (value === URL_FILTER_CHART_ID) return '地址栏筛选';
  return value ? '图表筛选' : '筛选控件';
}

export function filterLabel(field: string, value: string) {
  if (field === 'event_type') return `行为：${displayValue(value, 'eventType')}`;
  if (field === 'category_level1') return `类目：${displayValue(value)}`;
  if (field === 'brand') return `品牌：${displayValue(value)}`;
  return displayValue(value);
}

export function filterDisplayValue(field: string, value: string) {
  if (field === 'event_type') return displayValue(value, 'eventType');
  return displayValue(value);
}

export function buildDashboardFilter(field: DashboardFilterField, value: string | null | undefined, options: BuildFilterOptions = {}): DashboardFilter | null {
  const normalized = normalizedFilterValue(field, value);
  if (!normalized) return null;
  const sourceChartId = options.sourceChartId ?? URL_FILTER_CHART_ID;
  return {
    field,
    value: normalized,
    label: filterLabel(field, normalized),
    sourceChartId,
    sourceLabel: options.sourceLabel ?? sourceChartLabel(sourceChartId),
    displayValue: filterDisplayValue(field, normalized),
    interactionMode: 'filter',
    clearBehavior: 'show_all',
    scope: 'dashboard',
    affects: options.affects ?? ['图表高亮', '组合明细', '下钻路径'],
  };
}

export function parseFiltersFromSearchParams(searchParams: URLSearchParams) {
  const sourceChartId = searchParams.get('sourceChart') || URL_FILTER_CHART_ID;
  const sourceLabel = sourceChartLabel(sourceChartId);
  const filters: Array<DashboardFilter | null> = FILTER_FIELDS.map((field) => buildDashboardFilter(field, searchParams.get(field), { sourceChartId, sourceLabel }));
  return filters
    .filter((filter): filter is DashboardFilter => Boolean(filter));
}

function firstSourceChartId(filters: DashboardFilter[]) {
  return filters.find((filter) => filter.sourceChartId && filter.sourceChartId !== URL_FILTER_CHART_ID)?.sourceChartId
    ?? filters[0]?.sourceChartId
    ?? '';
}

export function sourceFromFilters(filters: DashboardFilter[], fallback = 'dashboard') {
  const sourceChartId = firstSourceChartId(filters);
  if (sourceChartId === CONTROLLED_QUERY_CHART_ID) return 'query';
  if (sourceChartId === TABLE_FILTER_CHART_ID) return 'table';
  return fallback;
}

export function filtersToSearchParams(filters: DashboardFilter[], current?: URLSearchParams, source?: string) {
  const next = new URLSearchParams(current);
  FILTER_FIELDS.forEach((field) => next.delete(field));
  const supportedFilters = filters.filter((filter) => isDashboardFilterField(filter.field));
  supportedFilters.forEach((filter) => {
    const field = filter.field as DashboardFilterField;
    const normalized = normalizedFilterValue(field, filter.value);
    if (normalized) next.set(field, normalized);
  });
  if (supportedFilters.length) {
    next.set('source', source ?? sourceFromFilters(supportedFilters));
    const sourceChartId = firstSourceChartId(supportedFilters);
    if (sourceChartId) {
      next.set('sourceChart', sourceChartId);
    } else {
      next.delete('sourceChart');
    }
  } else {
    next.delete('source');
    next.delete('sourceChart');
  }
  return next;
}

export function filtersEqual(left: DashboardFilter[], right: DashboardFilter[]) {
  const leftItems = left
    .filter((filter) => isDashboardFilterField(filter.field))
    .map((filter) => `${filter.field}:${filter.value}:${filter.sourceChartId}`)
    .sort();
  const rightItems = right
    .filter((filter) => isDashboardFilterField(filter.field))
    .map((filter) => `${filter.field}:${filter.value}:${filter.sourceChartId}`)
    .sort();
  return leftItems.length === rightItems.length && leftItems.every((item, index) => item === rightItems[index]);
}

export function tableHrefFromFilters(filters: DashboardFilter[], source?: string) {
  const params = filtersToSearchParams(filters, undefined, source);
  return params.size ? `/table?${params.toString()}` : '/table';
}

export function dashboardHrefFromFilters(filters: DashboardFilter[], source = 'query') {
  const params = filtersToSearchParams(filters, undefined, source);
  const query = params.toString();
  return query ? `/?${query}` : '/';
}

export function controlledQueryFilterField(dimension: string | null | undefined): DashboardFilterField | null {
  if (dimension === 'category_level1' || dimension === 'brand' || dimension === 'event_type') return dimension;
  return null;
}
