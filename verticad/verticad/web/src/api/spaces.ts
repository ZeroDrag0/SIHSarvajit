import type { IfcSpace, IfcSpaceGeometry, RawCadastralModel, RawSpaceClassification, RawSpaceGeometry } from '../types'
import { getJson } from './client'

/** GET /api/spaces (unit membership joined from GET /api/cadastral). */
export async function fetchSpaces(): Promise<IfcSpace[]> {
  const [raw, model] = await Promise.all([getJson<RawSpaceClassification>('spaces'), getJson<RawCadastralModel>('cadastral')])
  const owner = new Map<string, string>()
  for (const unit of model.property_units) for (const space of unit.ifc_spaces) owner.set(space.global_id, unit.unit_id)
  return raw.spaces.map((s) => ({
    globalId: s.space_global_id,
    name: s.space_name,
    longName: s.long_name,
    storeyId: s.storey_id,
    storeyName: s.storey_name,
    classification: s.classification,
    fn: s.function,
    groupScope: s.group_scope,
    classificationConfidence: s.confidence,
    unitId: owner.get(s.space_global_id) ?? null,
  }))
}

/** GET /api/spaces/geometry. Loaded lazily, only when a room-level layer is switched on. */
export async function fetchSpaceGeometry(): Promise<IfcSpaceGeometry[]> {
  const raw = await getJson<RawSpaceGeometry>('spaceGeometry')
  return raw.spaces.map((s) => ({
    globalId: s.space_global_id,
    name: s.space_name,
    storeyId: s.storey_global_id,
    method: s.method,
    isFallback: s.is_fallback,
    geometrySource: s.geometry_source,
    confidence: s.confidence,
    confidenceBasis: s.confidence_basis,
    corroboration: s.boundary_corroboration?.status ?? null,
    volumeM3: s.volume_m3,
    footprintAreaM2: s.footprint_area_m2,
    zMin: s.z_min,
    zMax: s.z_max,
    footprint: s.footprint.coordinates[0] ?? [],
  }))
}
