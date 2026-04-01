import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    sourcemap: true,
    chunkSizeWarningLimit: 380,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/lightweight-charts')) {
            return 'charts'
          }

          if (
            id.includes('node_modules/react/') ||
            id.includes('node_modules/react-dom/') ||
            id.includes('node_modules/zustand/')
          ) {
            return 'react'
          }

          if (id.includes('/src/lib/firebase.ts') || id.includes('node_modules/firebase/')) {
            return 'firebase'
          }

          if (
            id.includes('/src/app/lazyPanels.tsx') ||
            id.includes('/src/components/CandlesChart.tsx') ||
            id.includes('/src/components/ExecutionConsole.tsx') ||
            id.includes('/src/components/execution/') ||
            id.includes('/src/components/MatchingOrderBookPanel.tsx') ||
            id.includes('/src/components/ExecutionTimelinePanel.tsx') ||
            id.includes('/src/features/execution/useExecutionConsoleModel.ts') ||
            id.includes('/src/features/execution/read-models.ts') ||
            id.includes('/src/features/market/view-models.ts')
          ) {
            return 'workspace-panels'
          }

          if (
            id.includes('/src/components/CoreFlowPanel.tsx') ||
            id.includes('/src/components/ServiceHealthPanel.tsx') ||
            id.includes('/src/store/useDormantSelector.ts') ||
            id.includes('/src/ui/DiagnosticDrawer.tsx') ||
            id.includes('/src/view-models/workbench.ts') ||
            id.includes('/src/features/inference-observability/view-models.ts') ||
            id.includes('/src/features/strategy-orchestration/components/StrategyRegistryPanel.tsx') ||
            id.includes('/src/features/strategy-orchestration/components/StrategyOrchestrationAuditTimeline.tsx')
          ) {
            return 'workspace-shared'
          }

          return undefined
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    exclude: ['e2e/**', 'dist/**', 'node_modules/**'],
    coverage: {
      enabled: true,
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.ts', 'src/**/*.tsx'],
      exclude: ['src/gen/**'],
    },
  },
})
