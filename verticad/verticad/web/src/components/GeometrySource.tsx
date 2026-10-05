import type { GeometrySourceKind } from '../types'
import { StatusBadge } from './StatusBadge'

const LABEL: Record<GeometrySourceKind, string> = {
  native_body: 'Native IFC Body',
  derived_footprint_box: 'Derived · IFC FootPrint + Box',
  mixed: 'Mixed · Body + derived',
}

/** The native-vs-derived distinction is always shown; fallback geometry is never presented as native. */
const SHORT: Record<GeometrySourceKind, string> = { native_body: 'Native Body', derived_footprint_box: 'Derived', mixed: 'Mixed' }

export function GeometrySourceBadge({ kind, compact }: { kind: GeometrySourceKind; compact?: boolean }) {
  return <StatusBadge tone={kind === 'native_body' ? 'available' : 'derived'} label={compact ? SHORT[kind] : LABEL[kind]} title={LABEL[kind]} />
}
