import { lazy } from 'react'

export const LazyCandlesChart = lazy(() =>
  import('../components/CandlesChart').then((module) => ({
    default: module.CandlesChart,
  })),
)

export const LazyExecutionConsole = lazy(() =>
  import('../components/ExecutionConsole').then((module) => ({
    default: module.ExecutionConsole,
  })),
)

export const LazyExecutionTimelinePanel = lazy(() =>
  import('../components/ExecutionTimelinePanel').then((module) => ({
    default: module.ExecutionTimelinePanel,
  })),
)

export const LazyMatchingOrderBookPanel = lazy(() =>
  import('../components/MatchingOrderBookPanel').then((module) => ({
    default: module.MatchingOrderBookPanel,
  })),
)

export const LazyServiceHealthPanel = lazy(() =>
  import('../components/ServiceHealthPanel').then((module) => ({
    default: module.ServiceHealthPanel,
  })),
)

type SkeletonProps = {
  height: string
}

export function PanelSkeleton({ height }: SkeletonProps) {
  return <div className={`${height} animate-pulse rounded-xl border border-slate-700/60 bg-slate-900/40`} />
}
