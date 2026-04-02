export type AccentTone = 'teal' | 'cyan' | 'amber'

export function accentVar(accent: AccentTone): string {
  switch (accent) {
    case 'cyan':
      return 'var(--gl-cyan)'
    case 'amber':
      return 'var(--gl-amber)'
    case 'teal':
    default:
      return 'var(--gl-teal)'
  }
}
