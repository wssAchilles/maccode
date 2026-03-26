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
    startTransition(() => {
      setWorkspace(next)
    })
  }

  return (
    <main className="app-shell" data-testid="app-shell">
      <GlassPanel className="workbench-header" tone="hero">
        <div className="workbench-header-top">
          <div className="workbench-brand">
            <p className="workbench-eyebrow">{t('app.kicker')}</p>
            <h1>{t('app.title')}</h1>
            <p>{t('app.subtitle')}</p>
          </div>
          <div className="workbench-header-actions">
            <div className="env-chip-group">
              <span className="env-chip">{t('env.gateway')}: {env.gateway_base}</span>
              <span className="env-chip">{t('env.strategy')}: {env.strategy_base}</span>
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

        <div className="workbench-status-strip">
          {healthCards.map((card) => (
            <GlassPanel key={card.id} className="status-strip-card" tone="subtle">
              <div className="status-strip-head">
                <div>
                  <p className="subtle-label">{card.title}</p>
                  <p className="status-strip-meta">{card.staleLabel}</p>
                </div>
                <StatusPill state={card.state} label={card.stateLabel} compact />
              </div>
              <p className="status-strip-updated">{card.updatedAt}</p>
            </GlassPanel>
          ))}
        </div>
      </GlassPanel>

      <nav className="workspace-nav" aria-label={t('workspace.nav')}>
        {WORKSPACE_MODELS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={workspace === item.id ? 'workspace-nav-button workspace-nav-button-active' : 'workspace-nav-button'}
            onClick={() => handleWorkspaceChange(item.id)}
          >
            <span className="workspace-nav-title">{t(item.titleKey)}</span>
            <span className="workspace-nav-description">{t(item.descriptionKey)}</span>
          </button>
        ))}
      </nav>

      <section className="workspace-stage">
        <Suspense fallback={<GlassPanel className="workspace-loading">{t('workspace.loading')}</GlassPanel>}>
          {visited.map((visitedWorkspace) => {
            const WorkspaceComponent = WORKSPACE_COMPONENTS[visitedWorkspace]
            return (
              <div
                key={visitedWorkspace}
                className={cn('workspace-host', workspace === visitedWorkspace ? 'workspace-host-active' : 'workspace-host-hidden')}
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

      <nav className="workspace-mobile-nav" aria-label={t('workspace.nav')}>
        {WORKSPACE_MODELS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={workspace === item.id ? 'workspace-mobile-button workspace-mobile-button-active' : 'workspace-mobile-button'}
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
