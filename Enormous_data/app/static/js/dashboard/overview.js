import { api } from './api.js';
import { renderBar, renderLine, renderPie } from './charts.js';
import { formatNumber, setButtonLoading, showError } from './ui.js';

const summaryLabels = {
  raw_rows: '原始行数',
  cleaned_rows: '有效行数',
  removed_rows: '清洗剔除',
  duplicate_rows: '重复行数',
  invalid_price_rows: '异常价格',
  missing_brand_rows: '空品牌',
  unique_users: '用户数',
  unique_sessions: '会话数',
  total_sales: '销售额'
};

function renderCards(summary) {
  document.getElementById('summary-cards').innerHTML = Object.entries(summaryLabels)
    .map(([key, label]) => `
      <div class="metric-card">
        <span>${label}</span>
        <strong>${formatNumber(summary[key])}</strong>
      </div>
    `)
    .join('');
}

async function loadOverview() {
  const [summary, eventTypes, dailyEvents, categories] = await Promise.all([
    api.summary(),
    api.eventTypes(),
    api.dailyEvents(),
    api.topCategories()
  ]);

  renderCards(summary.data);
  renderPie('event-pie', '行为类型', eventTypes.data);
  renderLine('daily-events-line', dailyEvents.data, '事件量');
  renderBar('category-bar', categories.data, '事件量');
}

async function bindRefresh() {
  const button = document.getElementById('refresh-button');
  button.addEventListener('click', async () => {
    try {
      setButtonLoading(button, true, '刷新计算', '刷新中...');
      await api.refresh();
      alert('Spark 刷新任务已启动，稍后刷新页面查看结果。');
    } catch (error) {
      alert(error.message);
    } finally {
      setButtonLoading(button, false, '刷新计算', '刷新中...');
    }
  });
}

loadOverview().catch((error) => showError('#summary-cards', error));
bindRefresh();
