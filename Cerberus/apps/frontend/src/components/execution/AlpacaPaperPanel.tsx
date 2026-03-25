import type { TranslationKey } from '../../i18n/messages'
import type { TradingPolicy } from '../../types/contracts'
import { AppErrorNotice } from '../common/AppErrorNotice'

import type { GatewayResponse } from './types'

type Props = {
  t: (key: TranslationKey) => string
  symbol: string
  quantity: string
  side: 'buy' | 'sell'
  orderType: 'market' | 'limit'
  timeInForce: 'day' | 'gtc' | 'ioc' | 'opg' | 'cls'
  limitPrice: string
  submitting: boolean
  canceling: boolean
  canCancel: boolean
  result: GatewayResponse | null
  account: GatewayResponse | null
  policy: TradingPolicy | null
  onSymbolChange: (value: string) => void
  onQuantityChange: (value: string) => void
  onSideChange: (value: 'buy' | 'sell') => void
  onTypeChange: (value: 'market' | 'limit') => void
  onTimeInForceChange: (value: 'day' | 'gtc' | 'ioc' | 'opg' | 'cls') => void
  onLimitPriceChange: (value: string) => void
  onSubmit: () => void
  onCancel: () => void
}

export function AlpacaPaperPanel({
  t,
  symbol,
  quantity,
  side,
  orderType,
  timeInForce,
  limitPrice,
  submitting,
  canceling,
  canCancel,
  result,
  account,
  policy,
  onSymbolChange,
  onQuantityChange,
  onSideChange,
  onTypeChange,
  onTimeInForceChange,
  onLimitPriceChange,
  onSubmit,
  onCancel,
}: Props) {
  return (
    <article className="panel-card">
      <h2 className="panel-title">{t('execution.alpacaPaper')}</h2>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <label className="field-label">
          Symbol
          <input className="field-input" value={symbol} onChange={(event) => onSymbolChange(event.target.value)} />
        </label>
        <label className="field-label">
          Qty
          <input className="field-input" value={quantity} onChange={(event) => onQuantityChange(event.target.value)} />
        </label>
        <label className="field-label">
          Side
          <select
            className="field-input"
            value={side}
            onChange={(event) => onSideChange(event.target.value === 'sell' ? 'sell' : 'buy')}
          >
            <option value="buy">buy</option>
            <option value="sell">sell</option>
          </select>
        </label>
        <label className="field-label">
          Type
          <select
            className="field-input"
            value={orderType}
            onChange={(event) => onTypeChange(event.target.value === 'limit' ? 'limit' : 'market')}
          >
            <option value="market">market</option>
            <option value="limit">limit</option>
          </select>
        </label>
        <label className="field-label">
          Time in force
          <select
            className="field-input"
            value={timeInForce}
            onChange={(event) =>
              onTimeInForceChange((event.target.value as 'day' | 'gtc' | 'ioc' | 'opg' | 'cls') ?? 'day')
            }
          >
            <option value="day">day</option>
            <option value="gtc">gtc</option>
            <option value="ioc">ioc</option>
            <option value="opg">opg</option>
            <option value="cls">cls</option>
          </select>
        </label>
        {orderType === 'limit' ? (
          <label className="field-label">
            Limit price
            <input className="field-input" value={limitPrice} onChange={(event) => onLimitPriceChange(event.target.value)} />
          </label>
        ) : null}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="action-button action-button-success disabled:opacity-50"
          data-testid="submit-alpaca-order-button"
        >
          {submitting ? 'Submitting...' : t('execution.submit')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={!canCancel || canceling}
          className="action-button action-button-warning disabled:opacity-50"
          data-testid="cancel-alpaca-order-button"
        >
          {canceling ? 'Canceling...' : t('execution.cancel')}
        </button>
      </div>

      <h3 className="mt-3 text-xs text-slate-400">{t('execution.response')}</h3>
      {result?.error ? <AppErrorNotice error={result.error} className="mt-2" /> : null}
      <pre className="mt-1 max-h-40 overflow-auto rounded-xl border border-slate-700 bg-slate-950 p-2 text-[11px] text-slate-300">
        {JSON.stringify(result, null, 2)}
      </pre>

      <h3 className="mt-3 text-xs text-slate-400">{t('execution.accountSnapshot')}</h3>
      {account?.error ? <AppErrorNotice error={account.error} className="mt-2" /> : null}
      <pre className="mt-1 max-h-32 overflow-auto rounded-xl border border-slate-700 bg-slate-950 p-2 text-[11px] text-slate-300">
        {JSON.stringify(account, null, 2)}
      </pre>

      <h3 className="mt-3 text-xs text-slate-400">{t('execution.policy')}</h3>
      <pre className="mt-1 max-h-32 overflow-auto rounded-xl border border-slate-700 bg-slate-950 p-2 text-[11px] text-slate-300">
        {JSON.stringify(policy, null, 2)}
      </pre>
    </article>
  )
}
