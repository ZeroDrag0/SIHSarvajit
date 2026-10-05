import type { RawUlpins, UlpinRegistry } from '../types'
import { getJson } from './client'

/** GET /api/ulpins */
export async function fetchUlpins(): Promise<UlpinRegistry> {
  const raw = await getJson<RawUlpins>('ulpins')
  return {
    scheme: raw.scheme,
    disclaimer: raw.disclaimer,
    count: raw.count,
    records: raw.records.map((r) => ({
      code: r.prototype_ulpin,
      scheme: r.identity.scheme,
      dataset: r.identity.dataset,
      identifierClass: r.identifier_class,
      isOfficial: r.is_official_ulpin,
      issuer: r.issuer,
      parcelId: r.parcel_id,
      buildingId: r.building_id,
      unitId: r.property_unit_id,
      storeyIds: r.storey_ids,
      storeyNames: r.storey_names,
      verticalExtentM: r.identity.vertical_extent_m,
      geometryVersion: r.geometry_version,
      sourceIds: r.source_ids,
      validationStatus: r.validation_status,
      legalStatus: r.legal_status,
      ownershipStatus: r.ownership_status,
      cadastralStatus: r.cadastral_status,
      dataStatus: r.data_status,
      derivationMethod: r.provenance.derivation_method,
      unitStatus: r.provenance.unit_status,
      unitConfidence: r.provenance.unit_confidence,
      geometryConfidence: r.geometry.geometry_confidence,
      disclaimer: r.provenance.disclaimer,
    })),
  }
}
