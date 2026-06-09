export function formatNumber(value: number | undefined, suffix = '') {
  return `${(value ?? 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}${suffix}`;
}

export function formatCurrency(value: number | undefined) {
  return `¥${(value ?? 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

export function compactDate(value: string | undefined | null) {
  if (!value) return '暂无';
  return value.replace('T', ' ').slice(0, 19);
}
