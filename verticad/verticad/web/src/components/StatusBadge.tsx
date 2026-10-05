import type { StatusTone } from '../types'
import { GLYPH, statusDisplay } from '../utils/status'

interface StatusBadgeProps {
  /** Raw pipeline status token; mapped onto the UI vocabulary. */
  raw?: string | null
  /** Explicit tone/label, used when the caller has already decided. */
  tone?: StatusTone
  label?: string
  title?: string
}

export function StatusBadge({ raw, tone, label, title }: StatusBadgeProps) {
  const display = tone ? { tone, label: label ?? tone } : statusDisplay(raw)
  const text = label ?? display.label
  return (
    <span className={`badge badge--${display.tone}`} title={title ?? (raw ? `pipeline value: ${raw}` : undefined)}>
      <i aria-hidden="true">{GLYPH[display.tone]}</i>
      {text}
    </span>
  )
}
