import type { PrecheckResult } from '../../domain/trading/precheck'
import type { TranslationKey } from '../../i18n/messages'
import type { BinanceRule, TradingPolicy } from '../../types/contracts'
import { DataList, DiagnosticDrawer, GlassPanel } from '../../ui'
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
    <article className="stack">
      <div>
        <p className="subtle-label">{t('execution.binanceTest')}</p>
        <p className="panel-caption" aria-live="polite">
          {t(STAGE_KEY_MAP[stage])}
        </p>
      </div>

      <div className="execution-form-grid">
        <label className="field-label">
          Symbol
          <input id="binance-symbol" name="binance_symbol" className="field-input" value={selectedSymbol} disabled />
        </label>
        <label className="field-label">
          Side
          <select
            id="binance-side"
            name="binance_side"
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
            id="binance-quantity"
            name="binance_quantity"
            data-testid="binance-quantity-input"
            className="field-input"
            value={quantity}
            onChange={(event) => onQuantityChange(event.target.value)}
          />
        </label>
        <label className="field-label">
          Price
          <input
            id="binance-price"
            name="binance_price"
            data-testid="binance-price-input"
            className="field-input"
            value={price}
            onChange={(event) => onPriceChange(event.target.value)}
            placeholder={priceHint}
          />
        </label>
      </div>

      <GlassPanel tone="subtle">
        <DataList
          items={[
            { id: 'notional', label: 'Notional', value: notional === null ? '—' : notional.toFixed(6) },
            { id: 'minNotional', label: 'Min notional', value: String(rule?.min_notional ?? '—') },
            { id: 'minQty', label: 'Min qty', value: String(rule?.min_qty ?? '—') },
            { id: 'stepSize', label: 'Step size', value: String(rule?.step_size ?? '—') },
            { id: 'tickSize', label: 'Tick size', value: String(rule?.tick_size ?? '—') },
            { id: 'policyQty', label: 'Policy max qty', value: String(policy?.max_binance_order_qty ?? '—') },
          ]}
        />
      </GlassPanel>

      <div className="workspace-actions">
        <button
          type="button"
          onClick={onRunPrecheck}
          className="soft-button"
          data-testid="run-precheck-button"
        >
          {t('execution.precheckRun')}
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="soft-button soft-button-primary"
          data-testid="submit-binance-order-button"
        >
          {submitting ? 'Submitting...' : t('execution.submit')}
        </button>
      </div>

      {precheck ? (
        <GlassPanel tone="subtle" data-testid="binance-precheck-result">
          <p
            className={precheckPass ? 'precheck-status precheck-status-pass' : 'precheck-status precheck-status-fail'}
            aria-live="polite"
            data-testid="binance-precheck-status"
          >
            {precheckPass ? t('execution.precheckPassed') : t('execution.precheckFailed')}
          </p>
          <ul className="precheck-list">
            {precheck.checks.map((item) => (
              <li key={item.id} className="precheck-list-item">
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
        </GlassPanel>
      ) : null}

      {result?.error ? <AppErrorNotice error={result.error} className="mt-2" /> : null}

      <DiagnosticDrawer title={t('execution.response')} summary={result ? String(result.status) : '—'} defaultOpen={Boolean(result)}>
        <pre className="diagnostic-pre" data-testid="binance-response">
          {JSON.stringify(result, null, 2)}
        </pre>
      </DiagnosticDrawer>
    </article>
  )
}
