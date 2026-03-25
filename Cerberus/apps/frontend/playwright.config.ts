import { defineConfig, devices } from '@playwright/test'

const deployedMode = process.env.E2E_USE_DEPLOYED === 'true'
const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4173'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  webServer: deployedMode
    ? undefined
    : {
        command: 'npm run dev -- --host 127.0.0.1 --port 4173',
        port: 4173,
        reuseExistingServer: true,
        env: {
          VITE_DISABLE_LIVE_STREAM: 'true',
          VITE_AUTH_REQUIRED: 'false',
          VITE_GATEWAY_BASE: 'http://127.0.0.1:8080',
          VITE_STRATEGY_BASE: 'http://127.0.0.1:8001',
        },
      },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 7'] },
    },
  ],
})
