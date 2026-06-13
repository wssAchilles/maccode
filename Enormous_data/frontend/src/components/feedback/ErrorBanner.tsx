type ErrorBannerProps = {
  error?: Error | null;
};

export function ErrorBanner({ error }: ErrorBannerProps) {
  if (!error) return null;
  return (
    <div className="error-banner" role="alert">
      <strong>数据加载失败</strong>
      <span>请稍后重试，或刷新 Spark 计算任务。</span>
      <details>
        <summary>查看技术信息</summary>
        <code>{error.message}</code>
      </details>
    </div>
  );
}
