import type { PrecheckResult } from '../../domain/trading/precheck'
import type { TranslationKey } from '../../i18n/messages'
import type { BinanceRule, TradingPolicy } from '../../types/contracts'
import { AppErrorNotice } from '../common/AppErrorNotice'

import { STAGE_KEY_MAP, type GatewayResponse, type Stage } from './types'

type Props = {
  t: (key: TranslationKey) => string
  selectedSymbol: string
  side: 'BUY' | 'SELL'
  quantity: string
  price: string
  priceHint?: string
  submitting: boolean
  stage: Stage
  precheck: PrecheckResult | null
  result: GatewayResponse | null
  notional: number | null
  rule: BinanceRule | null
  policy: TradingPolicy | null
  onSideChange: (side: 'BUY' | 'SELL') => void
  onQuantityChange: (value: string) => void
  onPriceChange: (value: string) => void
  onRunPrecheck: () => void
  onSubmit: () => void
}

export function BinanceTestPanel({
  t,
  selectedSymbol,
  side,
  quantity,
  price,
  priceHint,
  submitting,
  stage,
  precheck,
  result,
  notional,
  rule,
  policy,
  onSideChange,
  onQuantityChange,
  onPriceChange,
  onRunPrecheck,
  onSubmit,
}: Props) {
  const precheckPass = precheck?.ok ?? false

  return (
    <article className="panel-card">
      <h2 className="panel-title">{t('execution.binanceTest')}</h2>
      <p className="mt-1 text-xs text-slate-400" aria-live="polite">
        {t(STAGE_KEY_MAP[stage])}
      </p>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <label className="field-label">
          Symbol
          <input className="field-input" value={selectedSymbol} disabled />
        </label>
        <label className="field-label">
          Side
          <select
            className="field-input"
            value={side}
            onChange={(event) => onSideChange(event.target.value === 'SELL' ? 'SELL' : 'BUY')}
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </label>
        <label className="field-label">
          Quantity
          <input
            data-testid="binance-quantity-input"
            className="field-input"
            value={quantity}
            onChange={(event) => onQuantityChange(event.target.value)}
          />
        </label>
        <label className="field-label">
          Price
          <input
            data-testid="binance-price-input"
            className="field-input"
            value={price}
            onChange={(event) => onPriceChange(event.target.value)}
            placeholder={priceHint}
          />
        </label>
      </div>

      <div className="mt-3 rounded-xl border border-slate-700/70 bg-slate-950/45 p-2 text-xs text-slate-300">
        <div>notional: {notional === null ? '--' : notional.toFixed(6)}</div>
        <div>min_notional: {rule?.min_notional ?? '--'}</div>
        <div>min_qty: {rule?.min_qty ?? '--'}</div>
        <div>step_size: {rule?.step_size ?? '--'}</div>
        <div>tick_size: {rule?.tick_size ?? '--'}</div>
        <div>policy max qty: {policy?.max_binance_order_qty ?? '--'}</div>
        <div>policy max notional: {policy?.max_binance_order_notional_usd ?? '--'}</div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onRunPrecheck}
          className="action-button action-button-secondary"
          data-testid="run-precheck-button"
        >
          {t('execution.precheckRun')}
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="action-button action-button-primary disabled:opacity-50"
          data-testid="submit-binance-order-button"
        >
          {submitting ? 'Submitting...' : t('execution.submit')}
        </button>
      </div>

      {precheck ? (
        <div
          className="mt-3 rounded-xl border border-slate-700/70 bg-slate-950/45 p-2"
          data-testid="binance-precheck-result"
        >
          <p
            className={`text-xs ${precheckPass ? 'text-gain' : 'text-loss'}`}
            aria-live="polite"
            data-testid="binance-precheck-status"
          >
            {precheckPass ? t('execution.precheckPassed') : t('execution.precheckFailed')}
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-300">
            {precheck.checks.map((item) => (
              <li key={item.id} className="flex items-center gap-2">
                <span
                  className={
                    item.status === 'pass'
                      ? 'status-dot status-dot-pass'
                      : item.status === 'fail'
                        ? 'status-dot status-dot-fail'
                        : 'status-dot status-dot-warn'
                  }
                />
                <span>{item.message}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <h3 className="mt-3 text-xs text-slate-400">{t('execution.response')}</h3>
      {result?.error ? <AppErrorNotice error={result.error} className="mt-2" /> : null}
      <pre
        className="mt-1 max-h-56 overflow-auto rounded-xl border border-slate-700 bg-slate-950 p-2 text-[11px] text-slate-300"
        data-testid="binance-response"
      >
        {JSON.stringify(result, null, 2)}
      </pre>
    </article>
  )
}
