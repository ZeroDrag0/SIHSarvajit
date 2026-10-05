const DASH = '—'

export function fmt(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH
  return value.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function fmtInt(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH
  return value.toLocaleString('en-GB', { maximumFractionDigits: 0 })
}

export function fmtM(value: number | null | undefined, digits = 2): string {
  const text = fmt(value, digits)
  return text === DASH ? text : `${text} m`
}

export function fmtElevation(value: number | null | undefined): string {
  if (value === null || value === undefined) return DASH
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±'
  return `${sign}${Math.abs(value).toFixed(2)} m`
}

export function fmtRange(min: number | null | undefined, max: number | null | undefined): string {
  if (min === null || min === undefined) return DASH
  if (max === null || max === undefined) return `${fmt(min)} m → not measured`
  return `${fmt(min)} → ${fmt(max)} m`
}

export function fmtBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return DASH
  if (bytes < 1024) return `${bytes} B`
  const units = ['kB', 'MB', 'GB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(1)} ${units[unit]}`
}

export function fmtConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined) return DASH
  return value.toFixed(2)
}

export function shortHash(hash: string, head = 10, tail = 6): string {
  return hash.length <= head + tail + 1 ? hash : `${hash.slice(0, head)}…${hash.slice(-tail)}`
}

export function fmtTimestamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`
}
