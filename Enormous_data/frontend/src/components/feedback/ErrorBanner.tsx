type ErrorBannerProps = {
  error?: Error | null;
};

export function ErrorBanner({ error }: ErrorBannerProps) {
  if (!error) return null;
  return <div className="error-banner">{error.message}</div>;
}
