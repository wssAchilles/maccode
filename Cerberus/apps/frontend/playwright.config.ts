import os from 'node:os'

import { defineConfig, devices } from '@playwright/test'

const deployedMode = process.env.E2E_USE_DEPLOYED === 'true'
const devBindHost = process.env.E2E_DEV_BIND_HOST ?? '0.0.0.0'
const devPort = Number(process.env.E2E_DEV_PORT ?? '4173')

function resolveDevHost(): string {
  if (process.env.E2E_DEV_HOST) {
    return process.env.E2E_DEV_HOST
  }

  const candidates = Object.values(os.networkInterfaces())
    .flatMap((entries) => entries ?? [])
    .filter((entry) => entry.family === 'IPv4' && !entry.internal)
    .map((entry) => entry.address)

  return candidates[0] ?? devBindHost
}

const devHost = resolveDevHost()
const devOrigin = process.env.E2E_DEV_ORIGIN ?? `http://${devHost}:${devPort}`
const baseURL = process.env.E2E_BASE_URL ?? devOrigin

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
        command: `npm run dev -- --host ${devBindHost} --port ${devPort}`,
        port: devPort,
        reuseExistingServer: true,
        env: {
          VITE_DISABLE_LIVE_STREAM: 'true',
          VITE_AUTH_REQUIRED: 'false',
          VITE_GATEWAY_BASE: '',
          VITE_STRATEGY_BASE: '',
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
