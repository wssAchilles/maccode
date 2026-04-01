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

export const LazyCoreFlowPanel = lazy(() =>
  import('../components/CoreFlowPanel').then((module) => ({
    default: module.CoreFlowPanel,
  })),
)

export const LazyExecutionTimelinePanel = lazy(() =>
  import('../components/ExecutionTimelinePanel').then((module) => ({
    default: module.ExecutionTimelinePanel,
  })),
)

export const LazyHealthInferenceOperationsDrawerContent = lazy(() =>
  import('../features/health/HealthInferenceOperationsDrawerContent').then((module) => ({
    default: module.HealthInferenceOperationsDrawerContent,
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

export const LazyExecutionStrategyOperationsDrawerContent = lazy(() =>
  import('../features/execution/components/ExecutionStrategyOperationsDrawerContent').then((module) => ({
    default: module.ExecutionStrategyOperationsDrawerContent,
  })),
)

type SkeletonProps = {
  height: string
}

export function PanelSkeleton({ height }: SkeletonProps) {
  const normalizedHeight =
    height.startsWith('h-[') && height.endsWith(']')
      ? height.slice(3, -1)
      : height

  return <div className="panel-skeleton" style={{ minHeight: normalizedHeight }} />
}
