import type { TranslationKey } from '../../i18n/messages'
import type { TradingPolicy } from '../../types/contracts'
import { DataList, DiagnosticDrawer, GlassPanel } from '../../ui'
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
    <article className="stack">
      <div>
        <p className="subtle-label">{t('execution.alpacaPaper')}</p>
        <p className="panel-caption">{t('workspace.execution.ticketDescription')}</p>
      </div>

      <div className="xf-grid">
        <label className="field-label">
          Symbol
          <input
            id="alpaca-symbol"
            name="alpaca_symbol"
            className="field-input"
            value={symbol}
            onChange={(event) => onSymbolChange(event.target.value)}
          />
        </label>
        <label className="field-label">
          Qty
          <input
            id="alpaca-quantity"
            name="alpaca_quantity"
            className="field-input"
            value={quantity}
            onChange={(event) => onQuantityChange(event.target.value)}
          />
        </label>
        <label className="field-label">
          Side
          <select
            id="alpaca-side"
            name="alpaca_side"
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
            id="alpaca-type"
            name="alpaca_type"
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
            id="alpaca-tif"
            name="alpaca_time_in_force"
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
            <input
              id="alpaca-limit-price"
              name="alpaca_limit_price"
              className="field-input"
              value={limitPrice}
              onChange={(event) => onLimitPriceChange(event.target.value)}
            />
          </label>
        ) : null}
      </div>

      <GlassPanel tone="subtle">
        <DataList
          items={[
            { id: 'policy', label: t('execution.policy'), value: policy?.enforced ? t('common.ready') : t('common.disabled') },
            { id: 'alpacaSymbolAllowance', label: 'Allowed symbols', value: String(policy?.alpaca_allowed_symbols.length ?? 0) },
            { id: 'maxQty', label: 'Max qty', value: String(policy?.max_alpaca_order_qty ?? t('common.na')) },
            { id: 'maxNotional', label: 'Max limit notional', value: String(policy?.max_alpaca_limit_notional_usd ?? t('common.na')) },
          ]}
        />
      </GlassPanel>

      <div className="ws-actions">
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="soft-button sbp"
          data-testid="submit-alpaca-order-button"
        >
          {submitting ? 'Submitting...' : t('execution.submit')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={!canCancel || canceling}
          className="soft-button"
          data-testid="cancel-alpaca-order-button"
        >
          {canceling ? 'Canceling...' : t('execution.cancel')}
        </button>
      </div>

      {result?.error ? <AppErrorNotice error={result.error} className="mt-2" /> : null}
      {account?.error ? <AppErrorNotice error={account.error} className="mt-2" /> : null}

      <DiagnosticDrawer
        title={t('execution.response')}
        summary={result ? String(result.status) : t('common.na')}
        defaultOpen={Boolean(result?.error)}
        testId="alpaca-response-drawer"
      >
        <pre className="diagnostic-pre" data-testid="alpaca-response">{JSON.stringify(result, null, 2)}</pre>
      </DiagnosticDrawer>

      <DiagnosticDrawer title={t('execution.accountSnapshot')} summary={account ? String(account.status) : t('common.na')} defaultOpen={Boolean(account?.error)}>
        <pre className="diagnostic-pre">{JSON.stringify(account, null, 2)}</pre>
      </DiagnosticDrawer>

      <DiagnosticDrawer title={t('execution.policy')} summary={policy?.enforced ? t('common.ready') : t('common.disabled')}>
        <pre className="diagnostic-pre">{JSON.stringify(policy, null, 2)}</pre>
      </DiagnosticDrawer>
    </article>
  )
}
