import type { HeaderProps } from './types'

function displayEndpoint(url: string): string {
  return url.trim().length ? url : 'same-origin'
}

export function AppHeader({
  t,
  env,
  locale,
  liveAnnouncement,
  authUserLabel,
  onSignOut,
  onLocaleChange,
}: HeaderProps) {
  return (
    <header className="panel-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-cyan-300">{t('app.title')}</h1>
          <p className="mt-1 text-sm text-slate-300">{t('app.subtitle')}</p>
          <p className="mt-1 text-xs text-slate-400">
            {t('env.gateway')}: {displayEndpoint(env.gateway_base)}
          </p>
          {env.strategy_base ? (
            <p className="text-xs text-slate-400">
              {t('env.strategy')}: {displayEndpoint(env.strategy_base)}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2 text-xs">
          {authUserLabel ? (
            <span className="rounded-lg border border-slate-600 bg-slate-900/50 px-2 py-1 text-slate-200">
              {authUserLabel}
            </span>
          ) : null}
          {onSignOut ? (
            <button type="button" className="lang-button" onClick={onSignOut}>
              {t('auth.signOut')}
            </button>
          ) : null}
          <button
            type="button"
            className={`lang-button ${locale === 'zh-CN' ? 'lang-button-active' : ''}`}
            onClick={() => onLocaleChange('zh-CN')}
          >
            {t('lang.zh')}
          </button>
          <button
            type="button"
            className={`lang-button ${locale === 'en-US' ? 'lang-button-active' : ''}`}
            onClick={() => onLocaleChange('en-US')}
          >
            {t('lang.en')}
          </button>
        </div>
      </div>
      <p className="sr-only" aria-live="polite">
        {liveAnnouncement}
      </p>
    </header>
  )
}
