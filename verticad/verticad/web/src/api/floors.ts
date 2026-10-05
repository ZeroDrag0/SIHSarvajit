import type { RawCadastralModel, RawFloors, Storey } from '../types'
import { getJson } from './client'

/** GET /api/floors (unit membership is joined from GET /api/cadastral). */
export async function fetchStoreys(): Promise<Storey[]> {
  const [raw, model] = await Promise.all([getJson<RawFloors>('floors'), getJson<RawCadastralModel>('cadastral')])
  const unitRefs = new Map<string, string[]>()
  for (const building of model.buildings) {
    for (const storey of building.storeys) unitRefs.set(storey.storey_id, storey.property_unit_refs)
  }
  return raw.storeys
    .map((s, index) => ({
      id: s.storey_id,
      name: s.name,
      orderIndex: s.order_index ?? index,
      elevationM: s.elevation_m,
      zMin: s.z_min,
      zMax: s.z_max,
      heightM: s.height_m ?? null,
      nominalHeightM: s.nominal_height_m ?? null,
      zSource: s.z_source,
      spaceCount: s.space_count,
      spaceIds: s.space_ids ?? [],
      spaceClasses: s.space_classes ?? [],
      verticalReference: s.vertical_reference ?? null,
      warnings: s.warnings ?? [],
      unitIds: unitRefs.get(s.storey_id) ?? [],
    }))
    .sort((a, b) => a.orderIndex - b.orderIndex)
}
