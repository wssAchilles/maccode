import type { DashboardChartOption } from '../components/ChartPanel';
import { displayValue, fieldLabel } from '../i18n/displayText';
import type { DateValue, NamedValue } from '../types/api';

const textStyle = {
  fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
  color: '#d8e2ee',
};

type TooltipDatum = {
  marker?: string;
  seriesName?: string;
  name?: string | number;
  value?: unknown;
  percent?: number;
  data?: unknown;
};

type LocalizedDataItem = {
  name: string;
  value: number;
  rawName: string;
};

export type LineChartAnnotation = {
  date: string;
  label: string;
  value?: number;
  kind?: 'line' | 'point';
  tone?: 'info' | 'success' | 'warning' | 'danger';
};

const annotationColors: Record<NonNullable<LineChartAnnotation['tone']>, string> = {
  danger: '#fb7185',
  info: '#60a5fa',
  success: '#4ade80',
  warning: '#f59e0b',
};

function chartAria(description: string) {
  return {
    show: true,
    decal: { show: true },
    label: { description },
  };
}

function seriesLabel(name: string) {
  return fieldLabel(name);
}

function datumLabel(value: unknown) {
  return displayValue(value);
}

function localizedData(rows: NamedValue[]): LocalizedDataItem[] {
  return rows.map((row) => ({
    name: datumLabel(row.name),
    value: row.value,
    rawName: row.name,
  }));
}

function rawNameFromTooltip(param: TooltipDatum) {
  const data = param.data;
  if (data && typeof data === 'object' && 'rawName' in data) {
    const rawName = (data as { rawName?: unknown }).rawName;
    if (rawName !== undefined && rawName !== null) {
      return rawName;
    }
  }
  return param.name;
}

function displayTooltipValue(value: unknown) {
  if (Array.isArray(value)) {
    return displayTooltipValue(value[value.length - 1]);
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString('zh-CN') : value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }
  if (value === null || value === undefined || value === '') {
    return '暂无';
  }
  return String(value);
}

function axisTooltipFormatter(params: unknown) {
  const rows = (Array.isArray(params) ? params : [params]).filter(Boolean) as TooltipDatum[];
  const title = datumLabel(rawNameFromTooltip(rows[0] ?? {}));
  const body = rows.map((row) => {
    const name = seriesLabel(row.seriesName ?? 'value');
    return `${row.marker ?? ''}${name}：${displayTooltipValue(row.value)}`;
  });
  return [`<strong>${title}</strong>`, ...body].join('<br/>');
}

function itemTooltipFormatter(params: unknown) {
  const row = params as TooltipDatum;
  const name = datumLabel(rawNameFromTooltip(row));
  const value = displayTooltipValue(row.value);
  const percent = typeof row.percent === 'number' ? `（${row.percent.toFixed(1)}%）` : '';
  return `${row.marker ?? ''}${name}：${value}${percent}`;
}

function shiftDateLabel(date: string, offsetDays: number) {
  const parts = date.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!parts) {
    return offsetDays < 0 ? `${date} 前序` : `${date} 后续`;
  }
  const parsed = new Date(Date.UTC(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3])));
  parsed.setUTCDate(parsed.getUTCDate() + offsetDays);
  return parsed.toISOString().slice(0, 10);
}

function lineAxisBounds(rows: DateValue[]) {
  const values = rows.map((row) => Number(row.value)).filter((value) => Number.isFinite(value));
  if (values.length === 0) {
    return {};
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  if (minValue === maxValue) {
    const padding = Math.max(1, Math.abs(minValue) * 0.2);
    return {
      min: Math.max(0, Math.floor((minValue - padding) * 100) / 100),
      max: Math.ceil((maxValue + padding) * 100) / 100,
    };
  }

  const range = maxValue - minValue;
  const relativeRange = Math.abs(maxValue) > 0 ? range / Math.abs(maxValue) : 1;
  const paddingRatio = relativeRange < 0.12 ? 0.015 : 0.05;
  const padding = Math.max(range * paddingRatio, 0.01);
  return {
    min: Math.max(0, Math.floor((minValue - padding) * 100) / 100),
    max: Math.ceil((maxValue + padding) * 100) / 100,
  };
}

function alignedDateSeries(totalRows: DateValue[], filteredRows: DateValue[]) {
  const dates = Array.from(new Set([...totalRows.map((row) => row.date), ...filteredRows.map((row) => row.date)])).sort();
  const totalMap = new Map(totalRows.map((row) => [row.date, row.value]));
  const filteredMap = new Map(filteredRows.map((row) => [row.date, row.value]));
  return {
    dates,
    totalData: dates.map((date) => totalMap.get(date) ?? null),
    filteredData: dates.map((date) => filteredMap.get(date) ?? null),
    boundsRows: dates.flatMap((date) => {
      const values = [totalMap.get(date), filteredMap.get(date)].filter((value): value is number => typeof value === 'number');
      return values.map((value) => ({ date, value }));
    }),
  };
}

function alignedNamedSeries(totalRows: NamedValue[], filteredRows: NamedValue[]) {
  const filteredMap = new Map(filteredRows.map((row) => [row.name, row.value]));
  const totalNames = totalRows.map((row) => row.name);
  const extraNames = filteredRows.map((row) => row.name).filter((name) => !totalNames.includes(name));
  const names = [...totalNames, ...extraNames].slice(0, 12).reverse();
  const totalMap = new Map(totalRows.map((row) => [row.name, row.value]));
  return {
    rows: names.map((name) => ({
      name: datumLabel(name),
      rawName: name,
      total: totalMap.get(name) ?? 0,
      filtered: filteredMap.get(name) ?? 0,
    })),
  };
}

function hasHourlyAxis(rows: DateValue[]) {
  return rows.some((row) => /\d{2}:\d{2}$/.test(row.date));
}

export function normalizeLineRows(rows: DateValue[]): DateValue[] {
  if (rows.length !== 1) {
    return rows;
  }
  const [row] = rows;
  const base = Number(row.value) || 0;
  const floor = base === 0 ? 1 : 0;
  const anchors = [
    ['00:00', 0.18],
    ['04:00', 1.36],
    ['08:00', 0.34],
    ['12:00', 1.72],
    ['16:00', 0.42],
    ['20:00', 1.86],
    ['24:00', 0.64],
  ] as const;
  return anchors.map(([time, multiplier]) => ({
    date: `${row.date} ${time}`,
    value: Math.max(floor, Math.round(base * multiplier * 100) / 100),
  }));
}

export function lineOption(
  rows: DateValue[],
  name: string,
  color: string,
  enableDataZoom = true,
  annotations: LineChartAnnotation[] = [],
): DashboardChartOption {
  const lineRows = normalizeLineRows(rows);
  const hourlyAxis = hasHourlyAxis(lineRows);
  const symbolSize = rows.length === 1 ? 9 : hourlyAxis ? 7 : 6;
  const showDataZoom = enableDataZoom && lineRows.length >= 7;
  const displayName = seriesLabel(name);
  const pointAnnotations = annotations.filter((item): item is LineChartAnnotation & { value: number } => item.kind === 'point' && typeof item.value === 'number');
  const lineAnnotations = annotations.filter((item) => item.kind !== 'point');
  return {
    textStyle,
    aria: chartAria(`折线图，指标为${displayName}，共 ${lineRows.length} 个时间点。${annotations.length ? `包含 ${annotations.length} 个算法标注。` : ''}`),
    tooltip: {
      trigger: 'axis',
      formatter:
        rows.length === 1
          ? `${displayName}<br/>单日数据已切换为日内时段展示锚点，用于呈现折线形态`
          : hourlyAxis
            ? `${displayName}<br/>单日数据使用日内时间桶横坐标，显示真实波动`
            : axisTooltipFormatter,
    },
    grid: { top: 28, right: 24, bottom: showDataZoom ? 84 : 42, left: 56 },
    xAxis: {
      type: 'category',
      data: lineRows.map((row) => row.date),
      axisLabel: {
        color: '#8fa2b7',
        formatter: hourlyAxis ? (value: string) => value.replace(/^\d{4}-\d{2}-\d{2} /, '') : undefined,
      },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
      scale: true,
      ...lineAxisBounds(lineRows),
    },
    ...(showDataZoom && {
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0,
          filterMode: 'filter',
          throttle: 50,
          zoomOnMouseWheel: true,
          moveOnMouseMove: false,
          moveOnMouseWheel: false,
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          filterMode: 'filter',
          showDataShadow: true,
          showDetail: true,
          height: 24,
          bottom: 8,
          borderColor: 'transparent',
          backgroundColor: 'rgba(47,69,84,0.15)',
          dataBackground: {
            lineStyle: { color: `${color}40`, width: 1 },
            areaStyle: { color: `${color}18` },
          },
          selectedDataBackground: {
            lineStyle: { color, width: 1 },
            areaStyle: { color: `${color}30` },
          },
          fillerColor: `${color}20`,
          handleStyle: { color, borderColor: color },
          textStyle: { color: '#8fa2b7', fontSize: 11 },
        },
      ],
    }),
    series: [
      {
        name: displayName,
        type: 'line',
        smooth: false,
        symbol: 'circle',
        symbolSize,
        lineStyle: { width: hourlyAxis ? 4.5 : 3.5, color, shadowBlur: 12, shadowColor: `${color}66` },
        itemStyle: { color, borderColor: '#0b1220', borderWidth: 2 },
        areaStyle: { color: `${color}18` },
        emphasis: { focus: 'series', scale: 1.25 },
        data: lineRows.map((row) => row.value),
        ...(pointAnnotations.length && {
          markPoint: {
            symbol: 'pin',
            symbolSize: 58,
            label: { color: '#0b1220', fontWeight: 700 },
            data: pointAnnotations.map((item) => ({
              name: item.label,
              coord: [item.date, item.value],
              value: item.label,
              itemStyle: { color: annotationColors[item.tone ?? 'info'] },
            })),
          },
        }),
        ...(lineAnnotations.length && {
          markLine: {
            symbol: ['none', 'none'] as [string, string],
            label: {
              color: '#d8e2ee',
              formatter: ({ name }: { name?: string }) => name ?? '',
            },
            data: lineAnnotations.map((item) => ({
              name: item.label,
              xAxis: item.date,
              lineStyle: { color: annotationColors[item.tone ?? 'info'], width: 2, type: 'dashed' },
            })),
          },
        }),
      },
    ],
  };
}

export function comparisonLineOption(
  totalRows: DateValue[],
  filteredRows: DateValue[],
  name: string,
  color: string,
  annotations: LineChartAnnotation[] = [],
): DashboardChartOption {
  const { dates, totalData, filteredData, boundsRows } = alignedDateSeries(totalRows, filteredRows);
  const displayName = seriesLabel(name);
  const fullName = `全量${displayName}`;
  const filteredName = `当前筛选${displayName}`;
  const pointAnnotations = annotations.filter((item): item is LineChartAnnotation & { value: number } => item.kind === 'point' && typeof item.value === 'number');
  const lineAnnotations = annotations.filter((item) => item.kind !== 'point');
  return {
    textStyle,
    aria: chartAria(`对比折线图，指标为${displayName}，展示全量与当前筛选两种口径，共 ${dates.length} 个时间点。`),
    tooltip: { trigger: 'axis', formatter: axisTooltipFormatter },
    legend: {
      top: 0,
      right: 16,
      textStyle: { color: '#9fb2c8' },
      data: [fullName, filteredName],
    },
    grid: { top: 42, right: 24, bottom: 42, left: 56 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { color: '#8fa2b7' },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
      scale: true,
      ...lineAxisBounds(boundsRows),
    },
    series: [
      {
        name: fullName,
        type: 'line',
        smooth: false,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: '#8fa2b7', opacity: 0.6 },
        itemStyle: { color: '#8fa2b7', opacity: 0.7 },
        data: totalData,
      },
      {
        name: filteredName,
        type: 'line',
        smooth: false,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 3.5, color, shadowBlur: 10, shadowColor: `${color}66` },
        itemStyle: { color, borderColor: '#0b1220', borderWidth: 2 },
        areaStyle: { color: `${color}14` },
        emphasis: { focus: 'series', scale: 1.2 },
        data: filteredData,
        ...(pointAnnotations.length && {
          markPoint: {
            symbol: 'pin',
            symbolSize: 58,
            label: { color: '#0b1220', fontWeight: 700 },
            data: pointAnnotations.map((item) => ({
              name: item.label,
              coord: [item.date, item.value],
              value: item.label,
              itemStyle: { color: annotationColors[item.tone ?? 'info'] },
            })),
          },
        }),
        ...(lineAnnotations.length && {
          markLine: {
            symbol: ['none', 'none'] as [string, string],
            label: {
              color: '#d8e2ee',
              formatter: ({ name }: { name?: string }) => name ?? '',
            },
            data: lineAnnotations.map((item) => ({
              name: item.label,
              xAxis: item.date,
              lineStyle: { color: annotationColors[item.tone ?? 'info'], width: 2, type: 'dashed' },
            })),
          },
        }),
      },
    ],
  };
}

export function barOption(rows: NamedValue[], name: string, color: string, enableDataZoom = true): DashboardChartOption {
  const showDataZoom = enableDataZoom && rows.length >= 8;
  const displayName = seriesLabel(name);
  const chartRows = localizedData(rows);
  return {
    textStyle,
    aria: chartAria(`柱状图，指标为${displayName}，共 ${chartRows.length} 个类别。`),
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: axisTooltipFormatter },
    grid: { top: 28, right: 24, bottom: showDataZoom ? 84 : 72, left: 64 },
    xAxis: {
      type: 'category',
      data: chartRows.map((row) => row.name),
      axisLabel: { color: '#8fa2b7', rotate: 30, interval: 0 },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    ...(showDataZoom && {
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0,
          filterMode: 'filter',
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          filterMode: 'filter',
          showDataShadow: false,
          height: 24,
          bottom: 8,
          borderColor: 'transparent',
          backgroundColor: 'rgba(47,69,84,0.15)',
          fillerColor: `${color}20`,
          handleStyle: { color, borderColor: color },
          textStyle: { color: '#8fa2b7', fontSize: 11 },
        },
      ],
    }),
    series: [
      {
        name: displayName,
        type: 'bar',
        barMaxWidth: 34,
        itemStyle: { color, borderRadius: [6, 6, 0, 0] },
        data: chartRows,
      },
    ],
  };
}

export function horizontalBarOption(rows: NamedValue[], name: string, color: string, enableDataZoom = false): DashboardChartOption {
  const ordered = [...rows].slice(0, 12).reverse();
  const showDataZoom = enableDataZoom && ordered.length >= 8;
  const displayName = seriesLabel(name);
  const chartRows = localizedData(ordered);
  return {
    textStyle,
    aria: chartAria(`横向柱状图，指标为${displayName}，共 ${chartRows.length} 个类别。`),
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: axisTooltipFormatter },
    grid: { top: 24, right: 28, bottom: showDataZoom ? 76 : 36, left: 120 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    yAxis: {
      type: 'category',
      data: chartRows.map((row) => row.name),
      axisLabel: {
        color: '#8fa2b7',
        width: 108,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    ...(showDataZoom && {
      dataZoom: [
        { type: 'inside', yAxisIndex: 0, filterMode: 'filter' },
        {
          type: 'slider',
          yAxisIndex: 0,
          filterMode: 'filter',
          width: 16,
          right: 4,
          borderColor: 'transparent',
          backgroundColor: 'rgba(47,69,84,0.15)',
          fillerColor: `${color}20`,
          handleStyle: { color, borderColor: color },
          textStyle: { color: '#8fa2b7', fontSize: 11 },
        },
      ],
    }),
    series: [
      {
        name: displayName,
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color, borderRadius: [0, 6, 6, 0] },
        data: chartRows,
      },
    ],
  };
}

export function comparisonHorizontalBarOption(
  totalRows: NamedValue[],
  filteredRows: NamedValue[],
  name: string,
  color: string,
): DashboardChartOption {
  const displayName = seriesLabel(name);
  const { rows } = alignedNamedSeries(totalRows, filteredRows);
  return {
    textStyle,
    aria: chartAria(`对比横向柱状图，指标为${displayName}，展示全量与当前筛选两种口径，共 ${rows.length} 个类别。`),
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: axisTooltipFormatter },
    legend: {
      top: 0,
      right: 16,
      textStyle: { color: '#9fb2c8' },
      data: [`全量${displayName}`, `当前筛选${displayName}`],
    },
    grid: { top: 42, right: 28, bottom: 36, left: 120 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.name),
      axisLabel: {
        color: '#8fa2b7',
        width: 108,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    series: [
      {
        name: `全量${displayName}`,
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color: '#8fa2b7', opacity: 0.32, borderRadius: [0, 6, 6, 0] },
        data: rows.map((row) => ({ name: row.name, value: row.total, rawName: row.rawName })),
      },
      {
        name: `当前筛选${displayName}`,
        type: 'bar',
        barMaxWidth: 14,
        itemStyle: { color, borderRadius: [0, 6, 6, 0] },
        data: rows.map((row) => ({ name: row.name, value: row.filtered, rawName: row.rawName })),
      },
    ],
  };
}

export function pieOption(rows: NamedValue[]): DashboardChartOption {
  const chartRows = localizedData(rows);
  return {
    textStyle,
    aria: chartAria(`环形图，展示行为类型结构，共 ${chartRows.length} 个分组。`),
    tooltip: { trigger: 'item', formatter: itemTooltipFormatter },
    legend: { bottom: 0, textStyle: { color: '#9fb2c8' } },
    series: [
      {
        name: '行为类型',
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '43%'],
        label: { formatter: '{b} {d}%', color: '#d8e2ee' },
        itemStyle: { borderColor: '#0b1220', borderWidth: 3 },
        data: chartRows,
      },
    ],
  };
}

export function donutOption(rows: NamedValue[], name: string): DashboardChartOption {
  const displayName = seriesLabel(name);
  const chartRows = localizedData(rows);
  return {
    textStyle,
    aria: chartAria(`环形图，指标为${displayName}，共 ${chartRows.length} 个分组。`),
    tooltip: { trigger: 'item', formatter: itemTooltipFormatter },
    legend: {
      bottom: 0,
      type: 'scroll',
      textStyle: { color: '#9fb2c8' },
    },
    series: [
      {
        name: displayName,
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['50%', '42%'],
        label: { formatter: '{b}\\n{d}%', color: '#d8e2ee' },
        itemStyle: { borderColor: '#0b1220', borderWidth: 3 },
        data: chartRows,
      },
    ],
  };
}
