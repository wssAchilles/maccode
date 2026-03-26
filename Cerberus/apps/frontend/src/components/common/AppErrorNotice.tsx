import { formatAppError, toAppError } from '../../lib/http'
import { useI18n } from '../../i18n/I18nProvider'
import { InlineAlert } from '../../ui'

type Props = {
  error: unknown
  className?: string
}

export function AppErrorNotice({ error, className }: Props) {
  const { locale } = useI18n()
  const normalized = toAppError(error)
  const title =
    normalized.code === 'network_error'
      ? locale === 'zh-CN'
        ? '网络请求失败'
        : 'Network request failed'
      : normalized.code === 'validation_error'
        ? locale === 'zh-CN'
          ? '提交参数无效'
          : 'Invalid request'
        : normalized.code === 'policy_rejected'
          ? locale === 'zh-CN'
            ? '策略限制阻止提交'
            : 'Blocked by trading policy'
          : normalized.message
  return (
    <InlineAlert title={title} tone="danger" className={className}>
      {formatAppError(normalized)}
    </InlineAlert>
  )
}
