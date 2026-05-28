export function formatSpeed(speed: number | null) {
  return speed === null ? "N/A" : `${speed.toFixed(1)} km/h`;
}

export function formatCount(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value);
}
