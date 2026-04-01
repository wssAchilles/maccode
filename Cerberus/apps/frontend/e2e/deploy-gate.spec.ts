import { expect, test, type Page } from '@playwright/test'

import { createDeployGateObserver } from './support/deployGate'

async function ensureAuthenticated(page: Page): Promise<void> {
  const loginPanel = page.getByTestId('auth-login-panel')
  const appShell = page.getByTestId('app-shell')

  await expect(appShell.or(loginPanel)).toBeVisible({ timeout: 20_000 })

  if (await appShell.isVisible().catch(() => false)) {
    return
  }

  const authRequired = await loginPanel.isVisible({ timeout: 10_000 }).catch(() => false)
  if (!authRequired) {
    return
  }

  const email = process.env.E2E_AUTH_EMAIL
  const password = process.env.E2E_AUTH_PASSWORD
  if (!email || !password) {
    throw new Error(
      'deploy gate requires E2E_AUTH_EMAIL and E2E_AUTH_PASSWORD when auth screen is enabled',
    )
  }

  await page.getByTestId('auth-email-input').fill(email)
  await page.getByTestId('auth-password-input').fill(password)
  await page.getByTestId('auth-email-submit').click()

  const authError = page.getByTestId('auth-error')
  await expect(appShell.or(authError)).toBeVisible({ timeout: 30_000 })

  if (await authError.isVisible().catch(() => false)) {
    const message = (await authError.textContent())?.trim()
    throw new Error(`auth failed during deploy gate: ${message ?? 'unknown error'}`)
  }
}

async function assertWorkbenchChrome(page: Page, projectName: string): Promise<void> {
  await expect(page.locator('.wb-header')).toBeVisible()

  const isMobile = projectName.toLowerCase().includes('mobile')
  if (isMobile) {
    await expect(page.locator('.ws-mobile-nav')).toBeVisible()
    return
  }

  await expect(page.locator('.ws-nav')).toBeVisible()
}

async function assertCoreFlowHealthy(page: Page): Promise<void> {
  const criticalSteps = ['market', 'submit', 'feedback', 'cancel']
  for (const step of criticalSteps) {
    const text = (await page.getByTestId(`core-flow-step-${step}`).innerText()).toLowerCase()
    if (/(error|错误|degraded|降级)/.test(text)) {
      throw new Error(`core flow step entered degraded/error state: ${step}`)
    }
  }
}

test.describe('deploy gate', () => {
  test.skip(process.env.E2E_GATE_MODE !== 'true', 'deploy gate only')

  test('core trading chain is release-ready (desktop/mobile)', async ({ page }, testInfo) => {
    test.setTimeout(180_000)
    const observer = createDeployGateObserver()
    observer.attach(page)

    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await ensureAuthenticated(page)
    await expect(page.getByTestId('app-shell')).toBeVisible()
    await assertWorkbenchChrome(page, testInfo.project.name)
    await expect(page.getByTestId('core-flow-panel')).toBeVisible()

    await page.goto('/?workspace=execution', { waitUntil: 'domcontentloaded' })
    await expect(page.getByTestId('app-shell')).toBeVisible()
    await expect(page.getByTestId('matching-orderbook-panel')).toBeVisible()
    await expect(page.getByTestId('execution-timeline-panel')).toBeVisible()

    await page.getByTestId('run-precheck-button').click()
    await expect(page.getByTestId('binance-precheck-status')).toBeVisible()
    const precheckStatus = page.getByTestId('binance-precheck-status')
    const initialStatusText = ((await precheckStatus.textContent()) ?? '').toLowerCase()
    const precheckFailed = initialStatusText.includes('failed') || initialStatusText.includes('失败')
    if (precheckFailed) {
      await page.getByTestId('binance-quantity-input').fill('0.002')
      await page.getByTestId('binance-price-input').fill('70000')
      await page.getByTestId('run-precheck-button').click()
      await expect(precheckStatus).toContainText(/passed|通过/i)
    }

    await page.getByTestId('submit-binance-order-button').click()
    await page.waitForResponse((response) => response.url().includes('/api/v1/binance/order/test'))
    await page.getByTestId('binance-response-drawer').click()
    await expect(page.getByTestId('binance-response')).toContainText('{')

    await page.getByRole('tab', { name: 'Alpaca' }).click()
    await expect(page.getByTestId('submit-alpaca-order-button')).toBeVisible()
    await page.getByTestId('submit-alpaca-order-button').click()
    await page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/alpaca/orders') &&
        !response.url().includes('/cancel') &&
        response.request().method() === 'POST',
    )

    const cancelButton = page.getByTestId('cancel-alpaca-order-button')
    await expect(cancelButton).toBeEnabled({ timeout: 15_000 })
    await cancelButton.click()
    await page.waitForResponse(
      (response) => response.url().includes('/api/v1/alpaca/orders/') && response.url().includes('/cancel'),
    )

    await page.goto('/?workspace=overview', { waitUntil: 'domcontentloaded' })
    await expect(page.getByTestId('core-flow-panel')).toBeVisible()
    await assertCoreFlowHealthy(page)
    observer.assertNoFailures()
  })
})
