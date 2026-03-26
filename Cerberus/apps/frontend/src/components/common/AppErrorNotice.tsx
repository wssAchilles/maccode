import { formatAppError, toAppError } from '../../lib/http'
import { InlineAlert } from '../../ui'

type Props = {
  error: unknown
  className?: string
}

export function AppErrorNotice({ error, className }: Props) {
  const normalized = toAppError(error)
  return (
    <InlineAlert title={normalized.message} tone="danger" className={className}>
      {formatAppError(normalized)}
    </InlineAlert>
  )
}
