import { api } from './api.js';
import { showError } from './ui.js';

const state = {
  page: 1,
  size: 10,
  eventType: ''
};

const eventTypeLabels = {
  view: '浏览',
  cart: '加购',
  remove_from_cart: '移出购物车',
  purchase: '购买'
};

async function loadTable() {
  const { data } = await api.table({
    page: state.page,
    size: state.size,
    event_type: state.eventType
  });

  document.getElementById('table-body').innerHTML = data.rows.map((row) => `
    <tr>
      <td>${row.event_time}</td>
      <td>${eventTypeLabels[row.event_type] || row.event_type || '未知'}</td>
      <td>${row.product_id}</td>
      <td>${row.category_code}</td>
      <td>${row.brand || '未知'}</td>
      <td>${row.price}</td>
      <td>${row.user_id}</td>
    </tr>
  `).join('');

  document.getElementById('page-info').textContent = `第 ${data.page} 页 / 共 ${data.total} 条`;
  document.getElementById('prev-page').disabled = data.page <= 1;
  document.getElementById('next-page').disabled = data.page * data.size >= data.total;
}

function reload() {
  loadTable().catch((error) => showError('.table-wrap', error));
}

document.getElementById('apply-filter').addEventListener('click', () => {
  state.page = 1;
  state.eventType = document.getElementById('event-type-filter').value;
  reload();
});

document.getElementById('prev-page').addEventListener('click', () => {
  state.page = Math.max(1, state.page - 1);
  reload();
});

document.getElementById('next-page').addEventListener('click', () => {
  state.page += 1;
  reload();
});

reload();
