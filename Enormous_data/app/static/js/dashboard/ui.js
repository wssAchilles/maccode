export function formatNumber(value) {
  if (typeof value !== 'number') {
    return value ?? 0;
  }
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

export function showError(target, error) {
  const element = typeof target === 'string' ? document.querySelector(target) : target;
  if (!element) {
    return;
  }
  element.innerHTML = `<div class="error">数据加载失败：${error.message}</div>`;
}

export function setButtonLoading(button, loading, textWhenIdle, textWhenLoading) {
  if (!button) {
    return;
  }
  button.disabled = loading;
  button.textContent = loading ? textWhenLoading : textWhenIdle;
}
