import { create } from 'zustand'

import { createExecutionTradingSlice } from './slices/execution-trading'
import { createMarketStreamSlice } from './slices/market-stream'
import type { RootStore } from './slices/shared'
import { createStrategySummarySlice } from './slices/strategy-summary'
import { createUIStateSlice } from './slices/ui-state'

export const useCerberusStore = create<RootStore>()((...args) => ({
  ...createUIStateSlice(...args),
  ...createMarketStreamSlice(...args),
  ...createStrategySummarySlice(...args),
  ...createExecutionTradingSlice(...args),
}))

export type { RootStore } from './slices/shared'
