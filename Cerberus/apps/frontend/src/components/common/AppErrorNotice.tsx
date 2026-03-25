import { formatAppError, toAppError } from '../../lib/http'

type Props = {
  error: unknown
  className?: string
}

export function AppErrorNotice({ error, className }: Props) {
  const normalized = toAppError(error)
  return (
    <div
      className={`rounded-lg border border-rose-300/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-100 ${className ?? ''}`}
      aria-live="polite"
    >
      <p className="font-semibold">{normalized.message}</p>
      <p className="mt-1 text-[11px] text-rose-200/90">{formatAppError(normalized)}</p>
    </div>
  )
}
