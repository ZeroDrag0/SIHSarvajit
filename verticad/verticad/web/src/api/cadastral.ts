import type { CadastralStatus, RawCadastralModel } from '../types'
import { getJson } from './client'

/** GET /api/cadastral */
export async function fetchCadastral(): Promise<CadastralStatus> {
  const raw = await getJson<RawCadastralModel>('cadastral')
  const parcel = raw.parcels[0]
  const underground = raw.underground_volumetric_entities
  return {
    modelVersion: raw.model_version,
    legalNotice: raw.legal_notice,
    hierarchyOrder: raw.hierarchy_order,
    parcel: {
      id: parcel?.parcel_id ?? null,
      status: parcel?.cadastral_status ?? 'not_available',
      linkBasis: parcel?.link_basis ?? null,
      derivation: parcel?.provenance.derivation_method ?? 'no parcel record in model',
      ownershipStatus: parcel?.ownership_status ?? 'unknown_not_provided',
    },
    bagId: raw.buildings[0]?.bag_id ?? null,
    terrainStatus: raw.terrain.terrain_status,
    underground: {
      status: underground.underground_status,
      entityCount: underground.entities.length,
      supportedTypes: underground.supported_types,
      notes: underground.notes ?? [],
    },
    commonSpaces: raw.common_service_spaces.map((s) => ({
      globalId: s.global_id,
      name: s.name,
      longName: s.long_name,
      classification: s.classification,
      storeyName: s.storey,
    })),
    grouping: {
      spacesInUnits: raw.unit_grouping_summary.spaces_in_units,
      commonOrServiceSpaces: raw.unit_grouping_summary.common_or_service_spaces,
      unassignedPrivateLikeSpaces: raw.unit_grouping_summary.unassigned_private_like_spaces,
      reassignedByGeometry: raw.unit_grouping_summary.reassigned_by_geometry,
      ambiguousSpaceNames: raw.unit_grouping_summary.ambiguous_space_names,
    },
  }
}
