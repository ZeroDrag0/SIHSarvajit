/**
 * Raw shapes of the Schependomlaan pipeline outputs (processed/*.json).
 * These mirror the files exactly; nothing here is invented by the frontend.
 * Only the fields the UI reads are declared.
 */

export type RawVec3 = [number, number, number]
export type RawRing = [number, number][]
export interface RawPolygon { type: 'Polygon'; coordinates: RawRing[] }
export interface RawMultiPolygon { type: 'MultiPolygon'; coordinates: RawRing[][] }
export type RawFootprint = RawPolygon | RawMultiPolygon

export interface RawCoordinateReference {
  source_crs: string
  source_crs_declared_in_ifc?: string | null
  target_crs: string | null
  vertical_reference: string
  transformation_status: string
  coordinate_status: string
  gnss_cors_control?: string
  notes?: string[]
}

export interface RawStorey {
  storey_id: string
  name: string
  building_id?: string
  order_index?: number
  elevation_m: number
  z_min: number
  z_max: number | null
  height_m?: number | null
  nominal_height_m?: number | null
  z_source: string
  space_count: number
  space_ids?: string[]
  space_classes?: string[]
  measured_space_count?: number
  vertical_reference?: string
  warnings?: string[]
}

export interface RawFloors {
  source_mode: string
  method: string
  storey_count: number
  storeys: RawStorey[]
  method_type: string
  model_status: string
}

export interface RawBuilding {
  building_id: string
  name: string
  storey_count: number
  storeys: RawStorey[]
  space_envelope_bounds_m: [RawVec3, RawVec3]
  z_min: number
  z_max: number
  height_m: number
  coordinate_reference: RawCoordinateReference
  geometry_basis: string
  extraction: {
    buildings: Array<{
      building_id: string
      method: string
      status: string
      footprint: RawFootprint
      footprint_area_m2: number
      footprint_note: string
      space_geometry_count: number
    }>
    method: string
    model_status: string
  }
  method_type: string
  model_status: string
  terrain_status: string
  parcel_id: string | null
  parcel_status: string
}

export interface RawGroupingEvidence { signal: string; detail: string | string[] }

export interface RawUnitGeometry {
  geometry_status: string
  representation: string
  union_status: string
  constituent_count: number
  missing_constituents: string[]
  z_min: number
  z_max: number
  height_m: number
  volume_m3: number
  surface_area_m2: number
  centroid: RawVec3
  footprint_area_m2: number
  footprint: RawFootprint
  footprint_note: string
  volume_note: string
  geometry_source: string
  is_fallback: boolean
  fallback_space_count: number
  body_space_count: number
  fallback_note?: string
  confidence: number
  confidence_note: string
  boundary_corroboration_summary: Record<string, number>
  watertight: boolean
  mesh_vertex_count: number
  mesh_face_count: number
  notes: string[]
}

export interface RawPropertyUnit {
  property_unit_id: string
  label: string
  classification: string
  legal_status: string
  ownership_status: string
  storey_names: string[]
  storey_ids: string[]
  source_space_ids: string[]
  source_space_names: string[]
  grouping_evidence: RawGroupingEvidence[]
  confidence_of_grouping: number
  geometry: RawUnitGeometry
  prototype_ulpin: string
  validation_state: string
  provenance: {
    derivation: string
    method_type: string
    model_status: string
    source_ifc: string
    source_ifc_global_ids: string[]
  }
}

export interface RawPropertyUnits {
  classification: string
  summary: {
    unit_count: number
    units_with_geometry: number
    geometry_success_rate: number
    units_geometry_valid: number
    by_geometry_status: Record<string, number>
    by_representation: Record<string, number>
  }
  coordinate_reference: RawCoordinateReference
  units: RawPropertyUnit[]
}

export interface RawUlpinRecord {
  prototype_ulpin: string
  identity: {
    scheme: string
    dataset: string
    parcel_id: string | null
    building_id: string
    property_unit_id: string
    storey_ids: string[]
    vertical_extent_m: [number, number]
    geometry_version: string
    source_ids: string[]
  }
  parcel_id: string | null
  building_id: string
  property_unit_id: string
  storey_ids: string[]
  storey_names: string[]
  geometry_version: string
  source_ids: string[]
  identifier_class: string
  is_official_ulpin: boolean
  issuer: string
  geometry: {
    geometry_status: string
    z_min: number
    z_max: number
    height_m: number
    volume_m3: number
    footprint_area_m2: number
    geometry_source: string
    is_fallback: boolean
    geometry_confidence: number
  }
  validation_status: string
  legal_status: string
  ownership_status: string
  cadastral_status: string
  data_status: string
  provenance: {
    source_dataset: string
    derivation_method: string
    unit_status: string
    unit_confidence: number
    disclaimer: string
  }
}

export interface RawUlpins {
  scheme: string
  disclaimer: string
  count: number
  records: RawUlpinRecord[]
}

export interface RawValidationCheck {
  status: string
  note?: string
  reason?: string
  method?: string
  [key: string]: unknown
}

export interface RawValidation {
  valid: boolean
  errors: string[]
  warnings: string[]
  checks: Record<string, RawValidationCheck>
  metrics: {
    unit_count: number
    units_with_geometry: number
    units_without_geometry: string[]
    space_geometry_count: number
    spaces_without_geometry: number
    total_unit_volume_m3: number
    required_checks: string[]
    required_checks_not_passed: string[]
    check_status_counts: Record<string, number>
  }
  validity_definition: string
}

export interface RawSpaceGeometrySummary {
  space_count: number
  geometry_extracted: number
  success_rate: number
  by_status: Record<string, number>
  by_method: Record<string, number>
  real_body_geometry: number
  fallback_geometry: number
  boundary_corroboration: Record<string, number>
  mean_confidence: number
  space_boundaries_in_model: number
}

export interface RawUnitGeometrySummary {
  unit_count: number
  units_with_geometry: number
  geometry_success_rate: number
  units_geometry_valid: number
  by_geometry_status: Record<string, number>
  by_representation: Record<string, number>
}

export interface RawPipelineReport {
  source_mode: string
  ifc_source: string
  buildings: number
  ifc_storeys: number
  ifc_spaces: number
  classified_spaces: number
  class_counts: Record<string, number>
  common_service_spaces: number
  inferred_property_units: number
  declared_count_check: { declared_in_ifc_project_name: number; derived: number; agrees: boolean; note: string }
  ambiguous_space_names: string[]
  space_geometry: RawSpaceGeometrySummary
  unit_geometry: RawUnitGeometrySummary
  topology_valid: boolean
  topology_errors: string[]
  topology_check_status_counts: Record<string, number>
  pointcloud_files_detected: number
  pointcloud_files_processed: number
  pointcloud_files_git_lfs_pointer: number
  pointcloud_status: { inventory: string; alignment: string; ifc_comparison: string }
  cadastral_status: string
  terrain_status: string
  crs: { coordinate_status: string; transformation_status: string; vertical_reference: string; gnss_cors_control: string }
  drone_imagery: string
  underground_status: string
  prototype_3d_ulpins: number
}

export interface RawProvenance {
  run_timestamp_utc: string
  note: string
  environment: Record<string, string>
  inputs: {
    ifc: { path: string; sha256: string; schema: string; length_unit: { length_scale_to_metre: number }; source_mode: string }
    pointclouds: Array<{ name: string; size_bytes: number; parse_status: string }>
  }
  methods: Record<string, { method_type?: string; model_status?: string; official?: boolean } | boolean>
  geometry: { space_summary: RawSpaceGeometrySummary; unit_summary: RawUnitGeometrySummary }
  pointcloud_comparison_status: string
  coordinate_reference: RawCoordinateReference
  data_availability: {
    drone_imagery_available: boolean
    drone_imagery_used: boolean
    cadastral: string
    terrain: string
    underground: string
  }
  legal_notice: string
}

export interface RawPointCloudFile {
  path: string
  name: string
  format: string
  size_bytes: number
  crs_known: boolean
  crs_statement: string
  parse_status: string
  lfs_pointer?: { oid_sha256: string; expected_size_bytes: number }
  note?: string
  point_count: number | null
  bounds: [RawVec3, RawVec3] | null
}

export interface RawPointCloudMetricFile { file?: string; name?: string; status?: string; [key: string]: unknown }

export interface RawPointCloud {
  inventory: {
    status: string
    source_root: string
    files: RawPointCloudFile[]
    files_processed: number
    files_git_lfs_pointer: number
    format_summary: Record<string, number>
    total_detected: number
    acquisition_statement: string
  }
  coverage: { status: string; files: RawPointCloudMetricFile[] }
  alignment: { status: string; ifc_bounds_m?: [RawVec3, RawVec3]; files: RawPointCloudMetricFile[]; method?: string }
  ifc_comparison: {
    status: string
    method?: string
    registration_files_found?: boolean
    files: RawPointCloudMetricFile[]
    reason?: string
  }
}

export interface RawModelSpaceRef { global_id: string; name: string; long_name: string | null; function?: string }

export interface RawCadastralModel {
  model_version: string
  legal_notice: string
  coordinate_reference: RawCoordinateReference
  hierarchy_order: string[]
  parcels: Array<{
    parcel_id: string | null
    cadastral_status: string
    link_basis: string | null
    building_refs: string[]
    ownership_status: string
    provenance: { derivation_method: string; data_status: string }
  }>
  buildings: Array<{
    building_id: string
    name: string
    parcel_ref: string | null
    status: string
    bag_id: string | null
    footprint_2d: RawFootprint
    storeys: Array<RawStorey & { property_unit_refs: string[] }>
  }>
  property_units: Array<{
    unit_id: string
    status: string
    volume_3d: { glb_node: string }
    vertical_extent: { reference: string }
    ifc_spaces: RawModelSpaceRef[]
    confidence: number
    warnings: string[]
    provenance: { derivation_method: string; data_status: string }
  }>
  common_service_spaces: Array<RawModelSpaceRef & { classification: string; storey: string }>
  underground_volumetric_entities: { underground_status: string; entities: unknown[]; supported_types: string[]; notes?: string[] }
  terrain: { terrain_status: string }
  validation_summary: { valid: boolean; error_count: number; warning_count: number }
  unit_grouping_summary: {
    ifc_space_count: number
    inferred_property_unit_count: number
    spaces_in_units: number
    common_or_service_spaces: number
    unassigned_private_like_spaces: number
    reassigned_by_geometry: number
    ambiguous_space_names: string[]
  }
}

export interface RawSpaceClassification {
  method: string
  model_status: string
  space_count: number
  class_counts: Record<string, number>
  spaces: Array<{
    space_global_id: string
    space_name: string
    long_name: string | null
    storey_id: string
    storey_name: string
    prefix_group: string
    group_scope: string
    classification: string
    function: string
    confidence: number
  }>
}

export interface RawSpaceGeometry {
  source_file: string
  coordinate_frame: string
  summary: RawSpaceGeometrySummary
  spaces: Array<{
    space_global_id: string
    space_name: string
    storey_global_id: string
    storey_name: string
    geometry_status: string
    method: string
    geometry_source: string
    is_fallback: boolean
    confidence: number
    confidence_basis: string
    volume_m3: number
    footprint_area_m2: number
    z_min: number
    z_max: number
    height_m: number
    footprint: RawPolygon
    boundary_corroboration?: { status: string; xy_bbox_max_deviation_m?: number }
  }>
}
