import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const allowedHosts = ['lvh.me', '.lvh.me']
const deferredEntryChunks = [
  'WorkbenchShell',
  'OverviewWorkspace',
  'MarketWorkspace',
  'ExecutionWorkspace',
  'HealthWorkspace',
  'workspace-panels',
  'workspace-shared',
  'charts',
]
const publicAppUrl = (process.env.VITE_PUBLIC_APP_URL ?? '').trim().replace(/\/+$/, '')
const resolvedPublicAppUrl = publicAppUrl ? `${publicAppUrl}/` : '/'
const resolvedOgImageUrl = publicAppUrl ? `${publicAppUrl}/og-card.svg` : '/og-card.svg'

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'cerberus-html-runtime-metadata',
      transformIndexHtml(html) {
        return html
          .replaceAll('__APP_PUBLIC_URL__', resolvedPublicAppUrl)
          .replaceAll('__APP_OG_IMAGE_URL__', resolvedOgImageUrl)
      },
    },
  ],
  server: {
    port: 5173,
    host: true,
    allowedHosts,
  },
  preview: {
    host: true,
    allowedHosts,
  },
  build: {
    minify: 'terser',
    cssMinify: 'lightningcss',
    sourcemap: true,
    chunkSizeWarningLimit: 380,
    terserOptions: {
      module: true,
      toplevel: true,
      compress: {
        module: true,
        passes: 3,
        pure_getters: true,
      },
      mangle: {
        module: true,
      },
      format: {
        comments: false,
      },
    },
    modulePreload: {
      resolveDependencies(_filename, deps, context) {
        if (context.hostType !== 'html') {
          return deps
        }
        return deps.filter(
          (dependency) => !deferredEntryChunks.some((chunkName) => dependency.includes(chunkName)),
        )
      },
    },
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
            id.includes('/src/features/execution/components/ExecutionStrategyOperationsDrawerContent.tsx') ||
            id.includes('/src/features/health/HealthInferenceOperationsDrawerContent.tsx') ||
            id.includes('/src/features/execution/useExecutionConsoleModel.ts') ||
            id.includes('/src/features/execution/read-models.ts') ||
            id.includes('/src/features/market/view-models.ts') ||
            id.includes('/src/features/inference-observability/components/InferenceOperationsPanel.tsx') ||
            id.includes('/src/features/inference-observability/useInferenceOperationsModel.ts') ||
            id.includes('/src/features/strategy-orchestration/components/StrategyOrchestrationOperationsPanel.tsx') ||
            id.includes('/src/features/strategy-orchestration/useStrategyOrchestrationOperationsModel.ts')
          ) {
            return 'workspace-panels'
          }

          if (
            id.includes('/src/components/CoreFlowPanel.tsx') ||
            id.includes('/src/components/ServiceHealthPanel.tsx') ||
            id.includes('/src/store/useDormantSelector.ts') ||
            id.includes('/src/ui/DiagnosticDrawer.tsx') ||
            id.includes('/src/view-models/orderbook.ts') ||
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
