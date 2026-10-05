import type { Building, RawBuilding } from '../types'
import { getJson } from './client'
import { outerRings, toCoordinateReference } from './shared'

/** GET /api/building */
export async function fetchBuilding(): Promise<Building> {
  const raw = await getJson<RawBuilding>('building')
  const extracted = raw.extraction.buildings.find((b) => b.building_id === raw.building_id) ?? raw.extraction.buildings[0]
  return {
    id: raw.building_id,
    name: raw.name,
    storeyCount: raw.storey_count,
    boundsM: raw.space_envelope_bounds_m,
    zMin: raw.z_min,
    zMax: raw.z_max,
    heightM: raw.height_m,
    footprint: extracted ? outerRings(extracted.footprint) : [],
    footprintAreaM2: extracted?.footprint_area_m2 ?? 0,
    footprintNote: extracted?.footprint_note ?? '',
    geometryBasis: raw.geometry_basis,
    status: extracted?.status ?? 'unknown',
    methodType: raw.method_type,
    modelStatus: raw.model_status,
    terrainStatus: raw.terrain_status,
    parcelId: raw.parcel_id,
    parcelStatus: raw.parcel_status,
    crs: toCoordinateReference(raw.coordinate_reference),
  }
}
