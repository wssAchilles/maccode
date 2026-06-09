export async function requestJson(url, params = {}, options = {}) {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(query ? `${url}?${query}` : url, options);
  const payload = await response.json();

  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || '请求失败');
  }

  return {
    data: payload.data,
    meta: payload.meta || {}
  };
}

export const api = {
  summary: () => requestJson('/api/summary'),
  eventTypes: () => requestJson('/api/events/distribution'),
  dailyEvents: () => requestJson('/api/trend/daily-events'),
  dailySales: () => requestJson('/api/trend/daily-sales'),
  topCategories: () => requestJson('/api/ranking/categories'),
  topBrands: () => requestJson('/api/ranking/brands'),
  table: (params) => requestJson('/api/table', params),
  refresh: () => requestJson('/api/refresh', {}, { method: 'POST' })
};
