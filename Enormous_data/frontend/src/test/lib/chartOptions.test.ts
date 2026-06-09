import { describe, expect, it } from 'vitest';
import { lineOption, normalizeLineRows } from '../../lib/chartOptions';

describe('normalizeLineRows', () => {
  it('expands a single date point into an intraday broken-line display series', () => {
    const rows = normalizeLineRows([{ date: '2019-11-01', value: 100 }]);

    expect(rows).toHaveLength(7);
    expect(rows.map((row) => row.date)).toEqual([
      '2019-11-01 00:00',
      '2019-11-01 04:00',
      '2019-11-01 08:00',
      '2019-11-01 12:00',
      '2019-11-01 16:00',
      '2019-11-01 20:00',
      '2019-11-01 24:00',
    ]);
    expect(rows.some((row, index) => index > 0 && row.value < rows[index - 1].value)).toBe(true);
    expect(rows.some((row, index) => index > 0 && row.value > rows[index - 1].value)).toBe(true);
    expect(Math.max(...rows.map((row) => row.value)) - Math.min(...rows.map((row) => row.value))).toBeGreaterThan(100);
  });

  it('keeps multi-point series unchanged', () => {
    const source = [
      { date: '2019-11-01', value: 100 },
      { date: '2019-11-02', value: 120 },
    ];

    expect(normalizeLineRows(source)).toBe(source);
  });

  it('renders line charts as hard broken lines with a focused y-axis range', () => {
    const option = lineOption(
      [
        { date: '2019-11-01', value: 100 },
        { date: '2019-11-02', value: 108 },
        { date: '2019-11-03', value: 102 },
      ],
      '事件量',
      '#39d0c8',
    );

    const series = Array.isArray(option.series) ? option.series[0] : option.series;
    const yAxis = Array.isArray(option.yAxis) ? option.yAxis[0] : option.yAxis;

    expect(series).toMatchObject({ type: 'line', smooth: false });
    expect(yAxis).toMatchObject({ scale: true, min: expect.any(Number), max: expect.any(Number) });
    expect(Number(yAxis?.max) - Number(yAxis?.min)).toBeLessThan(11);
  });

  it('formats intraday axes when backend switches a single day to finer granularity', () => {
    const option = lineOption(
      [
        { date: '2019-11-01 00:00', value: 100 },
        { date: '2019-11-01 03:00', value: 240 },
        { date: '2019-11-01 09:00', value: 80 },
      ],
      '事件量',
      '#39d0c8',
    );

    const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
    const tooltip = option.tooltip as { formatter?: string };

    const formatter = xAxis?.axisLabel?.formatter;

    expect(tooltip.formatter).toContain('日内时间桶横坐标');
    const renderedLabel =
      typeof formatter === 'function'
        ? (formatter as (value: string, index: number, extra: unknown) => string)('2019-11-01 03:00', 1, null)
        : formatter;

    expect(renderedLabel).toBe('03:00');
  });
});
