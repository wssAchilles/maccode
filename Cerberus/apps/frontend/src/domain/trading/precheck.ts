import type { BinanceRule, TradingPolicy } from '../../types/contracts'

export type PrecheckStatus = 'pass' | 'fail' | 'warn'

export type PrecheckItem = {
  id: string
  status: PrecheckStatus
  message: string
}

export type BinancePrecheckInput = {
  symbol: string
  quantityText: string
  priceText: string
  rule: BinanceRule | null
  policy: TradingPolicy | null
}

export type PrecheckResult = {
  ok: boolean
  quantity: number | null
  price: number | null
  notional: number | null
  checks: PrecheckItem[]
}

function parsePositiveNumber(input: string): number | null {
  const value = Number(input)
  if (!Number.isFinite(value) || value <= 0) {
    return null
  }
  return value
}

function isStepAligned(value: number, step?: number | null): boolean {
  if (!step || step <= 0) {
    return true
  }
  const units = value / step
  return Math.abs(units - Math.round(units)) < 1e-8
}

function makeCheck(id: string, pass: boolean, passMessage: string, failMessage: string): PrecheckItem {
  return {
    id,
    status: pass ? 'pass' : 'fail',
    message: pass ? passMessage : failMessage,
  }
}

export function runBinancePrecheck(input: BinancePrecheckInput): PrecheckResult {
  const quantity = parsePositiveNumber(input.quantityText)
  const price = parsePositiveNumber(input.priceText)
  const checks: PrecheckItem[] = []

  checks.push(
    makeCheck(
      'number-format',
      quantity !== null && price !== null,
      'quantity / price format valid',
      'quantity / price must be positive numbers',
    ),
  )

  if (input.policy?.enforced && input.policy.binance_allowed_symbols.length > 0) {
    const allowed = input.policy.binance_allowed_symbols.includes(input.symbol)
    checks.push(
      makeCheck(
        'policy-symbol',
        allowed,
        `symbol ${input.symbol} allowed by policy`,
        `symbol ${input.symbol} is blocked by policy`,
      ),
    )
  }

  if (quantity !== null && input.rule?.min_qty) {
    checks.push(
      makeCheck(
        'min-qty',
        quantity >= input.rule.min_qty,
        `quantity >= min_qty (${input.rule.min_qty})`,
        `quantity below min_qty (${input.rule.min_qty})`,
      ),
    )
  }

  if (quantity !== null) {
    checks.push(
      makeCheck(
        'step-size',
        isStepAligned(quantity, input.rule?.step_size),
        `quantity aligned to step_size (${input.rule?.step_size ?? 'n/a'})`,
        `quantity must align with step_size (${input.rule?.step_size ?? 'n/a'})`,
      ),
    )
  }

  if (price !== null) {
    checks.push(
      makeCheck(
        'tick-size',
        isStepAligned(price, input.rule?.tick_size),
        `price aligned to tick_size (${input.rule?.tick_size ?? 'n/a'})`,
        `price must align with tick_size (${input.rule?.tick_size ?? 'n/a'})`,
      ),
    )
  }

  let notional: number | null = null
  if (quantity !== null && price !== null) {
    notional = quantity * price

    if (input.rule?.min_notional) {
      checks.push(
        makeCheck(
          'min-notional',
          notional >= input.rule.min_notional,
          `notional >= min_notional (${input.rule.min_notional})`,
          `notional ${notional.toFixed(6)} below min_notional (${input.rule.min_notional})`,
        ),
      )
    }

    if (input.policy?.max_binance_order_notional_usd) {
      checks.push(
        makeCheck(
          'policy-max-notional',
          notional <= input.policy.max_binance_order_notional_usd,
          `notional <= policy max (${input.policy.max_binance_order_notional_usd})`,
          `notional above policy max (${input.policy.max_binance_order_notional_usd})`,
        ),
      )
    }
  }

  if (quantity !== null && input.policy?.max_binance_order_qty) {
    checks.push(
      makeCheck(
        'policy-max-qty',
        quantity <= input.policy.max_binance_order_qty,
        `quantity <= policy max (${input.policy.max_binance_order_qty})`,
        `quantity above policy max (${input.policy.max_binance_order_qty})`,
      ),
    )
  }

  const ok = checks.every((item) => item.status !== 'fail')
  return {
    ok,
    quantity,
    price,
    notional,
    checks,
  }
}
