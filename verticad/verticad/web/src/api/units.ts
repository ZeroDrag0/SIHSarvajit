import type { GeometryMetadata, GeometrySourceKind, PropertyUnit, RawCadastralModel, RawPropertyUnits, RawUnitGeometry } from '../types'
import { getJson } from './client'
import { outerRings } from './shared'

function sourceKind(g: RawUnitGeometry): GeometrySourceKind {
  if (g.body_space_count > 0 && g.fallback_space_count > 0) return 'mixed'
  if (g.is_fallback || g.fallback_space_count > 0) return 'derived_footprint_box'
  return 'native_body'
}

function toGeometry(g: RawUnitGeometry): GeometryMetadata {
  return {
    status: g.geometry_status,
    representation: g.representation,
    unionStatus: g.union_status,
    sourceKind: sourceKind(g),
    sourceText: g.geometry_source,
    isFallback: g.is_fallback,
    fallbackSpaceCount: g.fallback_space_count,
    bodySpaceCount: g.body_space_count,
    fallbackNote: g.fallback_note ?? null,
    volumeM3: g.volume_m3,
    volumeNote: g.volume_note,
    surfaceAreaM2: g.surface_area_m2,
    footprintAreaM2: g.footprint_area_m2,
    footprintNote: g.footprint_note,
    footprint: outerRings(g.footprint),
    heightM: g.height_m,
    zMin: g.z_min,
    zMax: g.z_max,
    centroid: g.centroid,
    watertight: g.watertight,
    meshVertexCount: g.mesh_vertex_count,
    meshFaceCount: g.mesh_face_count,
    confidence: g.confidence,
    confidenceNote: g.confidence_note,
    boundaryCorroboration: g.boundary_corroboration_summary,
    notes: g.notes,
  }
}

/** GET /api/units (room names, warnings and GLB node are joined from GET /api/cadastral). */
export async function fetchUnits(): Promise<PropertyUnit[]> {
  const [raw, model] = await Promise.all([getJson<RawPropertyUnits>('units'), getJson<RawCadastralModel>('cadastral')])
  const modelUnits = new Map(model.property_units.map((u) => [u.unit_id, u]))
  return raw.units.map((u) => {
    const m = modelUnits.get(u.property_unit_id)
    const named = new Map((m?.ifc_spaces ?? []).map((s) => [s.global_id, s]))
    return {
      id: u.property_unit_id,
      label: u.label,
      classification: u.classification,
      status: m?.status ?? 'inferred',
      legalStatus: u.legal_status,
      ownershipStatus: u.ownership_status,
      storeyIds: u.storey_ids,
      storeyNames: u.storey_names,
      spaces: u.source_space_ids.map((globalId, i) => {
        const ref = named.get(globalId)
        return {
          globalId,
          name: ref?.name ?? u.source_space_names[i] ?? globalId,
          longName: ref?.long_name ?? null,
          fn: ref?.function ?? null,
        }
      }),
      groupingEvidence: u.grouping_evidence.map((e) => ({
        signal: e.signal,
        detail: Array.isArray(e.detail) ? e.detail.join(', ') : e.detail,
      })),
      groupingConfidence: u.confidence_of_grouping,
      geometry: toGeometry(u.geometry),
      prototypeUlpin: u.prototype_ulpin,
      validationState: u.validation_state,
      warnings: m?.warnings ?? [],
      glbNode: m?.volume_3d.glb_node ?? u.property_unit_id,
      provenance: {
        derivation: u.provenance.derivation,
        derivationMethod: m?.provenance.derivation_method ?? null,
        methodType: u.provenance.method_type,
        modelStatus: u.provenance.model_status,
        sourceIfc: u.provenance.source_ifc,
        sourceIfcGlobalIds: u.provenance.source_ifc_global_ids,
      },
    }
  })
}
