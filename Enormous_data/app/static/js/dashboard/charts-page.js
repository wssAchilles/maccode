import { api } from './api.js';
import { renderBar, renderLine } from './charts.js';
import { showError } from './ui.js';

async function loadCharts() {
  const [dailySales, brands, eventTypes] = await Promise.all([
    api.dailySales(),
    api.topBrands(),
    api.eventTypes()
  ]);

  renderLine('daily-sales-line', dailySales.data, '销售额');
  renderBar('brand-bar', brands.data, '销售额');
  renderBar('event-type-bar', eventTypes.data, '事件量');
}

loadCharts().catch((error) => showError('main', error));
