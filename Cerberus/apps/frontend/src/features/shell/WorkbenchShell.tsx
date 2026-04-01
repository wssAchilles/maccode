import { lazy, Suspense, startTransition, useEffect, useMemo, useState, type ComponentType } from 'react'

import { useStrategySummaryResource } from '../../app/bootstrap/useResourceQueries'
import type { FirebaseAuthState } from '../../auth/useFirebaseAuth'
import { useI18n } from '../../i18n/I18nProvider'
import { cn } from '../../lib/cn'
import { useCerberusStore } from '../../store'
import type { WorkspaceId } from '../../store/slices/shared'
import { WORKSPACE_MODELS, buildHealthCards } from '../../view-models/workbench'
import { GlassPanel, StatusPill } from '../../ui'

const LazyOverviewWorkspace = lazy(() =>
  import('../overview/OverviewWorkspace').then((module) => ({ default: module.OverviewWorkspace })),
)
const LazyMarketWorkspace = lazy(() =>
  import('../market/MarketWorkspace').then((module) => ({ default: module.MarketWorkspace })),
)
const LazyExecutionWorkspace = lazy(() =>
  import('../execution/ExecutionWorkspace').then((module) => ({ default: module.ExecutionWorkspace })),
)
const LazyHealthWorkspace = lazy(() =>
  import('../health/HealthWorkspace').then((module) => ({ default: module.HealthWorkspace })),
)

type Props = {
  auth: FirebaseAuthState
}

const WORKSPACE_COMPONENTS: Record<WorkspaceId, ComponentType<any>> = {
  overview: LazyOverviewWorkspace,
  market: LazyMarketWorkspace,
  execution: LazyExecutionWorkspace,
  health: LazyHealthWorkspace,
}

function formatEndpointChip(url: string): string {
  if (!url.trim().length) {
    return 'same-origin'
  }
  try {
    return new URL(url).host
  } catch {
    return url
  }
}

function nextWorkspaceFromUrl(): WorkspaceId {
  const params = new URLSearchParams(window.location.search)
  const workspace = params.get('workspace')
  if (workspace === 'market' || workspace === 'execution' || workspace === 'health') {
    return workspace
  }
  return 'overview'
}

export function WorkbenchShell({ auth }: Props) {
  const { t } = useI18n()
  const env = useCerberusStore((state) => state.env)
  const locale = useCerberusStore((state) => state.uiState.locale)
  const liveAnnouncement = useCerberusStore((state) => state.uiState.live_announcement)
  const workspace = useCerberusStore((state) => state.uiState.shell_navigation.workspace)
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)
  const setLocale = useCerberusStore((state) => state.uiActions.setLocale)
  const setWorkspace = useCerberusStore((state) => state.uiActions.setWorkspace)

  useStrategySummaryResource(true)

  const [visited, setVisited] = useState<Array<WorkspaceId>>([workspace])
  const authUserLabel = useMemo(() => {
    if (!auth.user) {
      return undefined
    }
    return auth.user.email ?? auth.user.displayName ?? auth.user.uid
  }, [auth.user])
  const healthCards = buildHealthCards(domainStatus, t)

  useEffect(() => {
    setVisited((current) => (current.includes(workspace) ? current : [...current, workspace]))
    const params = new URLSearchParams(window.location.search)
    if (params.get('workspace') === workspace) {
      return
    }
    params.set('workspace', workspace)
    const nextUrl = `${window.location.pathname}?${params.toString()}${window.location.hash}`
    window.history.replaceState({}, '', nextUrl)
  }, [workspace])

  useEffect(() => {
    const handlePopState = () => {
      setWorkspace(nextWorkspaceFromUrl())
    }
    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [setWorkspace])

  const handleWorkspaceChange = (next: WorkspaceId) => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur()
    }
    startTransition(() => {
      setWorkspace(next)
    })
  }

  return (
    <main className="app-shell" data-testid="app-shell">
      <GlassPanel className="wb-header" tone="hero">
        <div className="wb-header-top">
          <div className="wb-brand">
            <p className="wb-eyebrow">{t('app.kicker')}</p>
            <h1>{t('app.title')}</h1>
            <p>{t('app.subtitle')}</p>
          </div>
          <div className="wb-header-actions">
            <div className="env-chip-group">
              <span className="env-chip">
                {t('env.gateway')}: {formatEndpointChip(env.gateway_base)}
              </span>
              {env.strategy_base ? (
                <span className="env-chip">
                  {t('env.strategy')}: {formatEndpointChip(env.strategy_base)}
                </span>
              ) : null}
            </div>
            {authUserLabel ? <span className="account-pill">{authUserLabel}</span> : null}
            {auth.required ? (
              <button type="button" className="soft-button" onClick={() => void auth.signOutCurrentUser()}>
                {t('auth.signOut')}
              </button>
            ) : null}
            <div className="locale-switch">
              <button type="button" className={locale === 'zh-CN' ? 'chip-button chip-button-active' : 'chip-button'} onClick={() => setLocale('zh-CN')}>
                {t('lang.zh')}
              </button>
              <button type="button" className={locale === 'en-US' ? 'chip-button chip-button-active' : 'chip-button'} onClick={() => setLocale('en-US')}>
                {t('lang.en')}
              </button>
            </div>
          </div>
        </div>

        <div className="wb-status-strip">
          {healthCards.map((card) => (
            <GlassPanel key={card.id} className="ss-card" tone="subtle">
              <div className="ss-head">
                <div>
                  <p className="subtle-label">{card.title}</p>
                  <p className="ss-meta">{card.staleLabel}</p>
                </div>
                <StatusPill state={card.state} label={card.stateLabel} compact />
              </div>
              <p className="ss-updated">{card.updatedAt}</p>
            </GlassPanel>
          ))}
        </div>
      </GlassPanel>

      <nav className="ws-nav" aria-label={t('workspace.nav')}>
        {WORKSPACE_MODELS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={workspace === item.id ? 'ws-nav-button ws-nav-button-active' : 'ws-nav-button'}
            onClick={() => handleWorkspaceChange(item.id)}
          >
            <span className="ws-nav-title">{t(item.titleKey)}</span>
            <span className="ws-nav-description">{t(item.descriptionKey)}</span>
          </button>
        ))}
      </nav>

      <section className="ws-stage">
        <Suspense fallback={<GlassPanel className="ws-loading">{t('workspace.loading')}</GlassPanel>}>
          {visited.map((visitedWorkspace) => {
            const WorkspaceComponent = WORKSPACE_COMPONENTS[visitedWorkspace]
            return (
              <div
                key={visitedWorkspace}
                className={cn('ws-host', workspace === visitedWorkspace ? 'ws-host-active' : 'ws-host-hidden')}
                aria-hidden={workspace !== visitedWorkspace}
              >
                {visitedWorkspace === 'overview' ? (
                  <WorkspaceComponent
                    active={workspace === visitedWorkspace}
                    onSelectWorkspace={handleWorkspaceChange}
                  />
                ) : (
                  <WorkspaceComponent active={workspace === visitedWorkspace} />
                )}
              </div>
            )
          })}
        </Suspense>
      </section>

      <nav className="ws-mobile-nav" aria-label={t('workspace.nav')}>
        {WORKSPACE_MODELS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={workspace === item.id ? 'ws-mobile-button ws-mobile-button-active' : 'ws-mobile-button'}
            onClick={() => handleWorkspaceChange(item.id)}
          >
            {t(item.titleKey)}
          </button>
        ))}
      </nav>

      <p className="sr-only" aria-live="polite">
        {liveAnnouncement}
      </p>
    </main>
  )
}
