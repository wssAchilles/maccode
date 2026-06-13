import { describe, expect, it } from 'vitest';
import { barOption, comparisonHorizontalBarOption, comparisonLineOption, lineOption, normalizeLineRows, pieOption } from '../../lib/chartOptions';

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

    const xAxis = (Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis) as {
      axisLabel?: { formatter?: string | ((value: string, index: number, extra: unknown) => string) };
    };
    const tooltip = option.tooltip as { formatter?: string };

    const formatter = xAxis?.axisLabel?.formatter;

    expect(tooltip.formatter).toContain('日内时间桶横坐标');
    const renderedLabel =
      typeof formatter === 'function'
        ? (formatter as (value: string, index: number, extra: unknown) => string)('2019-11-01 03:00', 1, null)
        : formatter;

    expect(renderedLabel).toBe('03:00');
  });

  it('adds localized trend annotations as markPoint and markLine', () => {
    const option = lineOption(
      [
        { date: '2019-11-01', value: 100 },
        { date: '2019-11-02', value: 120 },
      ],
      '销售额',
      '#f59e0b',
      true,
      [
        { date: '2019-11-02', value: 120, label: '成交峰值', kind: 'point', tone: 'success' },
        { date: '2019-11-02', label: 'Spark 刷新', kind: 'line', tone: 'info' },
      ],
    );
    const series = Array.isArray(option.series) ? option.series[0] : option.series;
    const aria = option.aria as { label?: { description?: string } };

    expect(series).toMatchObject({
      markPoint: { data: [{ name: '成交峰值', coord: ['2019-11-02', 120] }] },
      markLine: { data: [{ name: 'Spark 刷新', xAxis: '2019-11-02' }] },
    });
    expect(aria.label?.description).toContain('算法标注');
  });

  it('builds localized comparison line charts for filtered dashboard slices', () => {
    const option = comparisonLineOption(
      [
        { date: '2020-01-01', value: 100 },
        { date: '2020-01-02', value: 200 },
      ],
      [
        { date: '2020-01-01', value: 20 },
        { date: '2020-01-02', value: 80 },
      ],
      '销售额',
      '#f59e0b',
    );
    const series = Array.isArray(option.series) ? option.series : [option.series];
    const legend = option.legend as { data?: string[] };
    const aria = option.aria as { label?: { description?: string } };

    expect(legend.data).toEqual(['全量销售额', '当前筛选销售额']);
    expect(series).toHaveLength(2);
    expect(series[0]).toMatchObject({ name: '全量销售额', data: [100, 200] });
    expect(series[1]).toMatchObject({ name: '当前筛选销售额', data: [20, 80] });
    expect(aria.label?.description).toContain('全量与当前筛选');
  });

  it('builds localized comparison horizontal bars for filtered category ranking', () => {
    const option = comparisonHorizontalBarOption(
      [
        { name: 'electronics', value: 300 },
        { name: 'apparel', value: 200 },
      ],
      [{ name: 'electronics', value: 40 }],
      '事件量',
      '#7cdaff',
    );
    const series = Array.isArray(option.series) ? option.series : [option.series];
    const legend = option.legend as { data?: string[] };

    expect(legend.data).toEqual(['全量事件量', '当前筛选事件量']);
    expect(series[0]).toMatchObject({ name: '全量事件量' });
    expect(series[1]).toMatchObject({ name: '当前筛选事件量' });
  });

  it('localizes bar chart labels while keeping raw names for filtering', () => {
    const option = barOption([{ name: 'purchase', value: 24 }], 'fallback_rate', '#39d0c8');
    const xAxis = (Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis) as { data?: string[] };
    const series = Array.isArray(option.series) ? option.series[0] : option.series;
    const aria = option.aria as { label?: { description?: string } };

    expect(xAxis?.data).toEqual(['购买']);
    expect(series).toMatchObject({
      name: '兜底推荐占比',
      data: [{ name: '购买', value: 24, rawName: 'purchase' }],
    });
    expect(aria.label?.description).toContain('柱状图');
  });

  it('localizes pie tooltip and preserves raw event codes on data items', () => {
    const option = pieOption([{ name: 'cart', value: 12 }]);
    const series = Array.isArray(option.series) ? option.series[0] : option.series;
    const tooltip = option.tooltip as { formatter?: (params: unknown) => string };

    expect(series).toMatchObject({
      data: [{ name: '加购', value: 12, rawName: 'cart' }],
    });
    expect(tooltip.formatter?.({ marker: '', name: '加购', value: 12, percent: 100, data: { rawName: 'cart' } })).toBe('加购：12（100.0%）');
  });
});
