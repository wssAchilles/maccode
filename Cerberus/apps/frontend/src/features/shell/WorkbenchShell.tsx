import { lazy, Suspense, startTransition, useEffect, useMemo, useRef, useState, type ComponentType } from 'react'

import { useStrategySummaryResource } from '../../app/bootstrap/useResourceQueries'
import type { FirebaseAuthState } from '../../auth/useFirebaseAuth'
import { useI18n } from '../../i18n/I18nProvider'
import { cn } from '../../lib/cn'
import { useCerberusStore } from '../../store'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  WORKSPACE_GROUPS,
  WORKSPACE_INDEX_BY_ID,
  WORKSPACE_MODEL_BY_ID,
  WORKSPACE_MODELS,
  buildHealthCards,
  getWorkspaceAccent,
} from '../../view-models/workbench'
import { GlassPanel, MotionBackdrop, MotionSurface, RevealGroup, StatusPill } from '../../ui'
import { useRafPresenceTransition } from '../../ui/motion/useRafPresenceTransition'

const LazyOverviewWorkspace = lazy(() =>
  import('../overview/OverviewWorkspace').then((module) => ({ default: module.OverviewWorkspace })),
)
const LazyMarketWorkspace = lazy(() =>
  import('../market/MarketWorkspace').then((module) => ({ default: module.MarketWorkspace })),
)
const LazyBookWorkspace = lazy(() =>
  import('../book/BookWorkspace').then((module) => ({ default: module.BookWorkspace })),
)
const LazyStrategyWorkspace = lazy(() =>
  import('../strategy/StrategyWorkspace').then((module) => ({ default: module.StrategyWorkspace })),
)
const LazyExecutionWorkspace = lazy(() =>
  import('../execution/ExecutionWorkspace').then((module) => ({ default: module.ExecutionWorkspace })),
)
const LazyInferenceWorkspace = lazy(() =>
  import('../inference/InferenceWorkspace').then((module) => ({ default: module.InferenceWorkspace })),
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
  book: LazyBookWorkspace,
  strategy: LazyStrategyWorkspace,
  execution: LazyExecutionWorkspace,
  inference: LazyInferenceWorkspace,
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
  if (workspace && workspace in WORKSPACE_MODEL_BY_ID) {
    return workspace as WorkspaceId
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
  const currentWorkspace = WORKSPACE_MODEL_BY_ID[workspace]
  const workspaceIndex = WORKSPACE_INDEX_BY_ID[workspace]
  const authUserLabel = useMemo(() => {
    if (!auth.user) {
      return undefined
    }
    return auth.user.email ?? auth.user.displayName ?? auth.user.uid
  }, [auth.user])
  const healthCards = buildHealthCards(domainStatus, t)
  const readyCount = healthCards.filter((card) => card.state === 'ready').length
  const attentionCount = healthCards.filter((card) => card.state === 'degraded' || card.state === 'error').length
  const loadingCount = healthCards.filter((card) => card.state === 'loading').length
  const previousWorkspaceIndex = useRef(workspaceIndex)
  const [workspaceDirection, setWorkspaceDirection] = useState<'forward' | 'backward'>('forward')
  const shellPhase = useRafPresenceTransition(`${workspace}:${workspaceDirection}`, 620)
  const shellAccent = getWorkspaceAccent(workspace)

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

  useEffect(() => {
    const previousIndex = previousWorkspaceIndex.current
    if (workspaceIndex === previousIndex) {
      return
    }
    setWorkspaceDirection(workspaceIndex > previousIndex ? 'forward' : 'backward')
    previousWorkspaceIndex.current = workspaceIndex
  }, [workspaceIndex])

  const handleWorkspaceChange = (next: WorkspaceId) => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur()
    }
    startTransition(() => {
      setWorkspace(next)
    })
  }

  return (
    <main className="app-shell" data-testid="app-shell" data-workspace={workspace} data-phase={shellPhase}>
      <GlassPanel className="wb-header" tone="hero">
        <MotionBackdrop accent={shellAccent} intensity="hero" className="wb-backdrop" />
        <div className="wb-header-top">
          <div className="wb-brand">
            <div className="wb-brand-row">
              <p className="wb-eyebrow">{t('app.kicker')}</p>
              <p className="wb-workspace-pill">{currentWorkspace.indexLabel}</p>
            </div>
            <h1>{t('app.title')}</h1>
            <div className="wb-stage-copy">
              <p className="wb-stage-title">{t(currentWorkspace.titleKey)}</p>
              <p className="wb-stage-summary">{t(currentWorkspace.descriptionKey)}</p>
            </div>
          </div>

          <div className="wb-control-stack">
            <GlassPanel className="wb-control-card" tone="subtle">
              <div className="wb-control-head">
                <p className="subtle-label">{t('shell.system')}</p>
              </div>
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
            </GlassPanel>

            <GlassPanel className="wb-control-card wb-control-card-compact" tone="subtle">
              <div className="wb-control-head">
                <p className="subtle-label">{t('shell.session')}</p>
              </div>
              <div className="wb-session-row">
                {authUserLabel ? <span className="account-pill">{authUserLabel}</span> : null}
                <div className="locale-switch">
                  <button
                    type="button"
                    className={locale === 'zh-CN' ? 'chip-button chip-button-active' : 'chip-button'}
                    onClick={() => setLocale('zh-CN')}
                  >
                    {t('lang.zh')}
                  </button>
                  <button
                    type="button"
                    className={locale === 'en-US' ? 'chip-button chip-button-active' : 'chip-button'}
                    onClick={() => setLocale('en-US')}
                  >
                    {t('lang.en')}
                  </button>
                </div>
                {auth.required ? (
                  <button type="button" className="soft-button" onClick={() => void auth.signOutCurrentUser()}>
                    {t('auth.signOut')}
                  </button>
                ) : null}
              </div>
            </GlassPanel>
          </div>
        </div>

        <div className="wb-strip-shell">
          <div className="wb-strip-head">
            <div>
              <p className="subtle-label">{t('shell.status')}</p>
              <p className="wb-strip-summary">
                {readyCount} {t('shell.ready')} · {attentionCount} {t('shell.attention')}
                {loadingCount > 0 ? ` · ${loadingCount} ${t('shell.loading')}` : ''}
              </p>
            </div>
            <p className="wb-stage-active">{t(currentWorkspace.titleKey)}</p>
          </div>
          <div className="wb-status-strip">
            {healthCards.map((card, index) => (
              <RevealGroup key={card.id} revealIndex={index} className="ss-shell">
                <MotionSurface className="ss-surface" mode="panel">
                  <GlassPanel className="ss-card" tone="subtle">
                    <div className="ss-head">
                      <div>
                        <p className="subtle-label">{card.title}</p>
                        <p className="ss-meta">{card.staleLabel}</p>
                      </div>
                      <StatusPill state={card.state} label={card.stateLabel} compact />
                    </div>
                    <p className="ss-updated">{card.updatedAt}</p>
                  </GlassPanel>
                </MotionSurface>
              </RevealGroup>
            ))}
          </div>
        </div>
      </GlassPanel>

      <div className="wb-frame">
        <aside className="ws-rail-shell">
          <GlassPanel className="ws-rail-panel" tone="subtle">
            <div className="ws-nav-head">
              <div>
                <p className="subtle-label">{t('shell.navRail')}</p>
                <p className="wb-strip-summary">
                  {t(currentWorkspace.titleKey)} · {t(currentWorkspace.descriptionKey)}
                </p>
              </div>
            </div>

            <div className="ws-rail-stack">
              {WORKSPACE_GROUPS.map((group, groupIndex) => (
                <section key={group.id} className="ws-rail-group" aria-label={t(group.titleKey)}>
                  <div className="ws-rail-group-head">
                    <p className="subtle-label">{t(group.titleKey)}</p>
                    <p className="ws-rail-group-summary">{t(group.descriptionKey)}</p>
                  </div>

                  <nav className="ws-rail" aria-label={t(group.titleKey)}>
                    {group.items.map((item, itemIndex) => (
                      <RevealGroup
                        key={item.id}
                        revealIndex={groupIndex * 2 + itemIndex}
                        className="ws-rail-shell-item"
                      >
                        <MotionSurface className="ws-rail-surface" mode="button">
                          <button
                            type="button"
                            className={workspace === item.id ? 'ws-rail-item ws-rail-item-active' : 'ws-rail-item'}
                            onClick={() => handleWorkspaceChange(item.id)}
                            aria-current={workspace === item.id ? 'page' : undefined}
                          >
                            <span className="ws-rail-item-index">{item.indexLabel}</span>
                            <span className="ws-rail-item-copy">
                              <span className="ws-rail-item-title">{t(item.titleKey)}</span>
                              <span className="ws-rail-item-description">{t(item.descriptionKey)}</span>
                            </span>
                            <span className="ws-rail-item-pulse" aria-hidden="true" />
                          </button>
                        </MotionSurface>
                      </RevealGroup>
                    ))}
                  </nav>
                </section>
              ))}
            </div>
          </GlassPanel>
        </aside>

        <section className="ws-stage" data-workspace={workspace} data-phase={shellPhase} data-direction={workspaceDirection}>
          <MotionBackdrop accent={shellAccent} intensity="stage" className="ws-stage-backdrop" />
          <div className="ws-stage-stack">
            <Suspense fallback={<GlassPanel className="ws-loading">{t('workspace.loading')}</GlassPanel>}>
              {visited.map((visitedWorkspace) => {
                const WorkspaceComponent = WORKSPACE_COMPONENTS[visitedWorkspace]
                return (
                  <div
                    key={visitedWorkspace}
                    className={cn('ws-host', workspace === visitedWorkspace ? 'ws-host-active' : 'ws-host-hidden')}
                    aria-hidden={workspace !== visitedWorkspace}
                  >
                    <WorkspaceComponent
                      active={workspace === visitedWorkspace}
                      onSelectWorkspace={handleWorkspaceChange}
                    />
                  </div>
                )
              })}
            </Suspense>
          </div>
        </section>
      </div>

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
