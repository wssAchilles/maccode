export function isRealtimeSnapshotStale(
  timestampMs: number | null | undefined,
  thresholdMs: number,
  nowMs = Date.now(),
): boolean {
  if (typeof timestampMs !== 'number' || Number.isNaN(timestampMs)) {
    return true
  }

  return nowMs - timestampMs > thresholdMs
}

export function formatOptionalTimeLabel(timestampMs: number | null | undefined, fallback: string): string {
  if (typeof timestampMs !== 'number' || Number.isNaN(timestampMs)) {
    return fallback
  }

  return new Date(timestampMs).toLocaleTimeString()
}
