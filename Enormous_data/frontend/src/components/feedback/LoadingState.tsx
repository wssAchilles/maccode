export function LoadingState() {
  return (
    <div className="loading-state" role="status" aria-busy="true" aria-live="polite">
      <span />
      <span />
      <span />
      <p>正在加载数据</p>
    </div>
  );
}
