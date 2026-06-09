import type { DashboardChartOption } from '../components/ChartPanel';
import type { DateValue, NamedValue } from '../types/api';

const textStyle = {
  fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
  color: '#d8e2ee',
};

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

export function lineOption(rows: DateValue[], name: string, color: string): DashboardChartOption {
  const lineRows = normalizeLineRows(rows);
  const hourlyAxis = hasHourlyAxis(lineRows);
  const symbolSize = rows.length === 1 ? 9 : hourlyAxis ? 7 : 6;
  return {
    textStyle,
    tooltip: {
      trigger: 'axis',
      formatter:
        rows.length === 1
          ? `${name}<br/>单日数据已切换为日内时段展示锚点，用于呈现折线形态`
          : hourlyAxis
            ? `${name}<br/>单日数据使用日内时间桶横坐标，显示真实波动`
            : undefined,
    },
    grid: { top: 28, right: 24, bottom: 42, left: 56 },
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
    series: [
      {
        name,
        type: 'line',
        smooth: false,
        symbol: 'circle',
        symbolSize,
        lineStyle: { width: hourlyAxis ? 4.5 : 3.5, color, shadowBlur: 12, shadowColor: `${color}66` },
        itemStyle: { color, borderColor: '#0b1220', borderWidth: 2 },
        areaStyle: { color: `${color}18` },
        emphasis: { focus: 'series', scale: 1.25 },
        data: lineRows.map((row) => row.value),
      },
    ],
  };
}

export function barOption(rows: NamedValue[], name: string, color: string): DashboardChartOption {
  return {
    textStyle,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 28, right: 24, bottom: 72, left: 64 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.name),
      axisLabel: { color: '#8fa2b7', rotate: 30, interval: 0 },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    series: [
      {
        name,
        type: 'bar',
        barMaxWidth: 34,
        itemStyle: { color, borderRadius: [6, 6, 0, 0] },
        data: rows.map((row) => row.value),
      },
    ],
  };
}

export function pieOption(rows: NamedValue[]): DashboardChartOption {
  return {
    textStyle,
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#9fb2c8' } },
    series: [
      {
        name: '行为类型',
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '43%'],
        label: { formatter: '{b} {d}%', color: '#d8e2ee' },
        itemStyle: { borderColor: '#0b1220', borderWidth: 3 },
        data: rows,
      },
    ],
  };
}
