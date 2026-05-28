export function formatSpeed(speed: number | null) {
  return speed === null ? "N/A" : `${speed.toFixed(1)} km/h`;
}

export function formatCount(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value);
}

export function formatPercent(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `${(value * 100).toFixed(0)}%`;
}

export function formatUncertainty(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `±${value.toFixed(1)} km/h`;
}

export function formatMeters(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `${value.toFixed(1)} m`;
}

export function formatMetersPerSecond(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `${value.toFixed(2)} m/s`;
}

export function formatAcceleration(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `${value.toFixed(2)} m/s²`;
}

export function formatDegrees(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `${value.toFixed(0)}°`;
}

export function formatSeconds(value: number | null | undefined) {
  return value === null || value === undefined ? "N/A" : `${value.toFixed(2)} s`;
}

export function formatSpeedInterval(value: [number, number] | null | undefined) {
  return value === null || value === undefined
    ? "N/A"
    : `${value[0].toFixed(1)}-${value[1].toFixed(1)} km/h`;
}
