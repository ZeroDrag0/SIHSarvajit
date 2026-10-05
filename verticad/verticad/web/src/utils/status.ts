import type { StatusTone } from '../types'

export interface StatusDisplay {
  tone: StatusTone
  label: string
}

const EXACT: Record<string, StatusDisplay> = {
  available: { tone: 'available', label: 'Available' },
  live_ifc: { tone: 'available', label: 'Available' },
  derived: { tone: 'derived', label: 'Derived' },
  fallback: { tone: 'derived', label: 'Derived' },
  inferred: { tone: 'inferred', label: 'Inferred' },
  prototype: { tone: 'prototype', label: 'Prototype' },
  validated: { tone: 'validated', label: 'Validated' },
  valid: { tone: 'validated', label: 'Valid' },
  passed: { tone: 'validated', label: 'Passed' },
  corroborated: { tone: 'validated', label: 'Corroborated' },
  partially_corroborated: { tone: 'warning', label: 'Partially corroborated' },
  deviates: { tone: 'warning', label: 'Deviates' },
  warning: { tone: 'warning', label: 'Warning' },
  failed: { tone: 'error', label: 'Failed' },
  error: { tone: 'error', label: 'Error' },
  incomplete: { tone: 'warning', label: 'Incomplete' },
  not_run: { tone: 'not-used', label: 'Not run' },
  not_applicable: { tone: 'neutral', label: 'Not applicable' },
  not_available: { tone: 'unavailable', label: 'Unavailable' },
  unavailable: { tone: 'unavailable', label: 'Unavailable' },
  data_not_available: { tone: 'unavailable', label: 'Unavailable' },
  not_available_and_not_used: { tone: 'not-used', label: 'Unavailable · not used' },
  unresolved: { tone: 'unverified', label: 'Unresolved' },
  'local/unverified': { tone: 'unverified', label: 'Local · unverified' },
  not_validated: { tone: 'unverified', label: 'Not validated' },
  not_performed: { tone: 'not-used', label: 'Not performed' },
  not_evaluated: { tone: 'not-used', label: 'Not evaluated' },
  git_lfs_pointers_only: { tone: 'unavailable', label: 'Pointer stubs only' },
  git_lfs_pointer_not_downloaded: { tone: 'unavailable', label: 'Pointer stub · not downloaded' },
  not_computed_git_lfs_pointer_not_downloaded: { tone: 'not-used', label: 'Not computed' },
  not_computed_registration_unverified: { tone: 'unverified', label: 'Not computed · registration unverified' },
  no_pointcloud_files_processed: { tone: 'not-used', label: 'Not computed' },
  not_a_legal_cadastral_unit: { tone: 'prototype', label: 'Not a legal cadastral unit' },
  not_official_prototype_identifier: { tone: 'prototype', label: 'Prototype · not official' },
  unknown_not_provided: { tone: 'unavailable', label: 'Unknown · not provided' },
  not_trained: { tone: 'neutral', label: 'No trained model' },
  rule_based: { tone: 'neutral', label: 'Rule-based' },
  geometry_based: { tone: 'neutral', label: 'Geometry-based' },
  deterministic_hash: { tone: 'neutral', label: 'Deterministic hash' },
}

export function humanise(token: string): string {
  const text = token.replace(/[_/]+/g, ' ').trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Map a raw pipeline status token onto the UI vocabulary. Unknown tokens stay visible, never green. */
export function statusDisplay(raw: string | null | undefined): StatusDisplay {
  if (raw === null || raw === undefined || raw === '') return { tone: 'unavailable', label: 'Not reported' }
  const key = raw.toLowerCase()
  const exact = EXACT[key]
  if (exact) return exact
  if (key.includes('unverified')) return { tone: 'unverified', label: humanise(raw) }
  if (key.startsWith('not_') || key.startsWith('no_')) return { tone: 'not-used', label: humanise(raw) }
  return { tone: 'neutral', label: humanise(raw) }
}

export const GLYPH: Record<StatusTone, string> = {
  available: '●',
  validated: '✓',
  derived: '◐',
  inferred: '◑',
  prototype: '◇',
  warning: '▲',
  error: '✕',
  unavailable: '○',
  'not-used': '○',
  unverified: '?',
  neutral: '·',
}
