import type { RawValidation, RawValidationCheck, ValidationCheck, ValidationResult } from '../types'
import { getJson } from './client'

/** Display titles for the check keys the pipeline emits. Unknown keys fall back to the key itself. */
const TITLES: Record<string, string> = {
  duplicate_units: 'Duplicate units',
  invalid_geometry: 'Geometry validity',
  self_intersections: 'Self-intersections',
  zero_negative_volume: 'Zero / negative volume',
  volumetric_overlap: 'Volumetric overlap',
  footprint_overlap: 'Footprint overlap (stacking)',
  vertical_overlap: 'Vertical overlap',
  unexpected_gaps: 'Unexpected gaps',
  building_containment: 'Building containment',
  storey_unit_consistency: 'Storey consistency',
  z_order_consistency: 'Z ordering',
  shared_boundary_consistency: 'Shared boundaries',
  parcel_building_consistency: 'Parcel / building consistency',
  terrain_building_consistency: 'Terrain / building consistency',
  geometry_provenance: 'Geometry provenance',
}

const REMARK_KEYS = ['reason', 'note', 'method', 'footprint_envelope_source', 'z_envelope_source']
const UNIT_ID = /^PU-\d+$/

function humanise(key: string): string {
  const text = key.replace(/_0_6_/, '_0.6_').replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []
}

function toCheck(key: string, raw: RawValidationCheck, required: boolean): ValidationCheck {
  const remarks: string[] = []
  const facts: ValidationCheck['facts'] = []
  const unitIds = new Set<string>()
  for (const [field, value] of Object.entries(raw)) {
    if (field === 'status') continue
    if (REMARK_KEYS.includes(field)) {
      if (typeof value === 'string') remarks.push(value)
      continue
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      facts.push({ label: humanise(field), value: String(value) })
    } else if (Array.isArray(value)) {
      if (value.length === 0) {
        facts.push({ label: humanise(field), value: 'none' })
        continue
      }
      const strings = stringList(value)
      if (strings.length === value.length && strings.every((s) => UNIT_ID.test(s)) && strings.length > 0) {
        strings.forEach((s) => unitIds.add(s))
        facts.push({ label: humanise(field), value: `${strings.length} unit(s)` })
      } else if (value.every((v) => typeof v === 'number')) {
        facts.push({ label: humanise(field), value: (value as number[]).map((n) => n.toFixed(3)).join(' / ') })
      } else if (strings.length === value.length && strings.length > 0) {
        facts.push({ label: humanise(field), value: strings.join(', ') })
      } else {
        facts.push({ label: humanise(field), value: String(value.length) })
      }
    } else if (value && typeof value === 'object') {
      facts.push({ label: humanise(field), value: `${Object.keys(value).length} entr${Object.keys(value).length === 1 ? 'y' : 'ies'}` })
    }
  }
  return { key, title: TITLES[key] ?? humanise(key), status: raw.status, required, remarks, facts, unitIds: [...unitIds] }
}

function numberRecord(value: unknown): Record<string, number> {
  if (!value || typeof value !== 'object') return {}
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === 'number'))
}

/** GET /api/validation */
export async function fetchValidation(): Promise<ValidationResult> {
  const raw = await getJson<RawValidation>('validation')
  const required = new Set(raw.metrics.required_checks)
  const pairs = raw.checks.footprint_overlap?.stacked_pairs
  const provenance = raw.checks.geometry_provenance
  return {
    valid: raw.valid,
    errors: raw.errors,
    warnings: raw.warnings,
    checks: Object.entries(raw.checks).map(([key, check]) => toCheck(key, check, required.has(key))),
    statusCounts: raw.metrics.check_status_counts,
    requiredChecks: raw.metrics.required_checks,
    requiredChecksNotPassed: raw.metrics.required_checks_not_passed,
    validityDefinition: raw.validity_definition,
    totalUnitVolumeM3: raw.metrics.total_unit_volume_m3,
    storeyCoverageRatio: numberRecord(raw.checks.unexpected_gaps?.storey_coverage_ratio),
    stackedPairs: Array.isArray(pairs)
      ? (pairs as Array<{ units: [string, string]; footprint_overlap_m2: number; z_overlap_m: number }>).map((p) => ({
          units: p.units,
          footprintOverlapM2: p.footprint_overlap_m2,
          zOverlapM: p.z_overlap_m,
        }))
      : [],
    fallbackGeometryUnits: stringList(raw.checks.invalid_geometry?.fallback_geometry_units),
    spacesNotFullyCorroborated: stringList(provenance?.spaces_not_fully_corroborated_by_space_boundaries),
    spacesDeviating: stringList(provenance?.spaces_deviating_from_space_boundaries),
  }
}
