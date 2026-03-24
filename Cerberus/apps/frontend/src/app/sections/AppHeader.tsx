import type { HeaderProps } from './types'

export function AppHeader({ t, env, locale, liveAnnouncement, onLocaleChange }: HeaderProps) {
  return (
    <header className="panel-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-cyan-300">{t('app.title')}</h1>
          <p className="mt-1 text-sm text-slate-300">{t('app.subtitle')}</p>
          <p className="mt-1 text-xs text-slate-400">
            {t('env.gateway')}: {env.gateway_base}
          </p>
          <p className="text-xs text-slate-400">
            {t('env.strategy')}: {env.strategy_base}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
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
