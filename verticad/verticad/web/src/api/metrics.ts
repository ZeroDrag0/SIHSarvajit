import type { Metrics, RawPipelineReport } from '../types'
import { getJson } from './client'

/** GET /api/metrics */
export async function fetchMetrics(): Promise<Metrics> {
  const raw = await getJson<RawPipelineReport>('metrics')
  return {
    sourceMode: raw.source_mode,
    buildings: raw.buildings,
    storeys: raw.ifc_storeys,
    ifcSpaces: raw.ifc_spaces,
    classifiedSpaces: raw.classified_spaces,
    classCounts: raw.class_counts,
    commonServiceSpaces: raw.common_service_spaces,
    propertyUnits: raw.inferred_property_units,
    prototypeUlpins: raw.prototype_3d_ulpins,
    nativeGeometries: raw.space_geometry.real_body_geometry,
    derivedGeometries: raw.space_geometry.fallback_geometry,
    spaceGeometryByMethod: raw.space_geometry.by_method,
    boundaryCorroboration: raw.space_geometry.boundary_corroboration,
    meanSpaceConfidence: raw.space_geometry.mean_confidence,
    spaceBoundariesInModel: raw.space_geometry.space_boundaries_in_model,
    unitGeometryByStatus: raw.unit_geometry.by_geometry_status,
    unitGeometryByRepresentation: raw.unit_geometry.by_representation,
    unitsWithGeometry: raw.unit_geometry.units_with_geometry,
    unitsGeometryValid: raw.unit_geometry.units_geometry_valid,
    topologyValid: raw.topology_valid,
    checkStatusCounts: raw.topology_check_status_counts,
    declaredCountCheck: {
      declared: raw.declared_count_check.declared_in_ifc_project_name,
      derived: raw.declared_count_check.derived,
      agrees: raw.declared_count_check.agrees,
      note: raw.declared_count_check.note,
    },
    ambiguousSpaceNames: raw.ambiguous_space_names,
    pointcloud: {
      detected: raw.pointcloud_files_detected,
      processed: raw.pointcloud_files_processed,
      lfsPointers: raw.pointcloud_files_git_lfs_pointer,
      inventory: raw.pointcloud_status.inventory,
      alignment: raw.pointcloud_status.alignment,
      comparison: raw.pointcloud_status.ifc_comparison,
    },
    cadastralStatus: raw.cadastral_status,
    terrainStatus: raw.terrain_status,
    droneImagery: raw.drone_imagery,
    undergroundStatus: raw.underground_status,
    gnssCorsControl: raw.crs.gnss_cors_control,
    coordinateStatus: raw.crs.coordinate_status,
  }
}
