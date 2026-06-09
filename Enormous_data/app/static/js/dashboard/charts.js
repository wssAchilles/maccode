const charts = [];

const textStyle = {
  fontFamily: 'Arial, "Microsoft YaHei", sans-serif'
};

function initChart(id) {
  const element = document.getElementById(id);
  if (!element) {
    return null;
  }
  const chart = echarts.init(element);
  charts.push(chart);
  return chart;
}

export function renderPie(id, title, rows) {
  const chart = initChart(id);
  if (!chart) return;
  chart.setOption({
    textStyle,
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        name: title,
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '44%'],
        label: { formatter: '{b}: {d}%' },
        data: rows
      }
    ]
  }, true);
}

export function renderLine(id, rows, name) {
  const chart = initChart(id);
  if (!chart) return;
  chart.setOption({
    textStyle,
    tooltip: { trigger: 'axis' },
    grid: { top: 28, right: 24, bottom: 48, left: 56 },
    xAxis: { type: 'category', data: rows.map((row) => row.date) },
    yAxis: { type: 'value' },
    series: [
      {
        name,
        type: 'line',
        smooth: true,
        symbolSize: 6,
        areaStyle: {},
        data: rows.map((row) => row.value)
      }
    ]
  }, true);
}

export function renderBar(id, rows, name) {
  const chart = initChart(id);
  if (!chart) return;
  chart.setOption({
    textStyle,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 28, right: 24, bottom: 78, left: 64 },
    xAxis: {
      type: 'category',
      axisLabel: { interval: 0, rotate: 30 },
      data: rows.map((row) => row.name)
    },
    yAxis: { type: 'value' },
    series: [
      {
        name,
        type: 'bar',
        barMaxWidth: 36,
        data: rows.map((row) => row.value)
      }
    ]
  }, true);
}

function debounce(fn, wait) {
  let timer = null;
  return () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(fn, wait);
  };
}

window.addEventListener('resize', debounce(() => {
  charts.forEach((chart) => chart.resize());
}, 150));
