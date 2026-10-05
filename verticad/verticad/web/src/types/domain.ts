/** Frontend domain model. Built by the API adapter from the raw pipeline outputs. */

export type Vec3 = [number, number, number]
/** A closed ring of [x, y] in IFC local metres. */
export type Ring = [number, number][]

/** UI status vocabulary. Every badge in the app resolves to one of these. */
export type StatusTone =
  | 'available'
  | 'derived'
  | 'inferred'
  | 'validated'
  | 'prototype'
  | 'warning'
  | 'error'
  | 'unavailable'
  | 'not-used'
  | 'unverified'
  | 'neutral'

export interface CoordinateReference {
  sourceCrs: string
  declaredInIfc: string | null
  targetCrs: string | null
  verticalReference: string
  transformationStatus: string
  coordinateStatus: string
  gnssCorsControl: string | null
  notes: string[]
  /** true only when the pipeline reports a verified, transformed CRS. */
  isVerified: boolean
}

export interface Storey {
  id: string
  name: string
  orderIndex: number
  elevationM: number
  zMin: number
  zMax: number | null
  heightM: number | null
  nominalHeightM: number | null
  /** 'measured_space_geometry' | 'nominal_ifc_elevation' | … as reported. */
  zSource: string
  spaceCount: number
  spaceIds: string[]
  spaceClasses: string[]
  verticalReference: string | null
  warnings: string[]
  unitIds: string[]
}

export interface Building {
  id: string
  name: string
  storeyCount: number
  boundsM: [Vec3, Vec3]
  zMin: number
  zMax: number
  heightM: number
  footprint: Ring[]
  footprintAreaM2: number
  footprintNote: string
  geometryBasis: string
  status: string
  methodType: string
  modelStatus: string
  terrainStatus: string
  parcelId: string | null
  parcelStatus: string
  crs: CoordinateReference
}

export type GeometrySourceKind = 'native_body' | 'derived_footprint_box' | 'mixed'

export interface GeometryMetadata {
  status: string
  representation: string
  unionStatus: string
  sourceKind: GeometrySourceKind
  /** Verbatim geometry_source string from the pipeline. */
  sourceText: string
  isFallback: boolean
  fallbackSpaceCount: number
  bodySpaceCount: number
  fallbackNote: string | null
  volumeM3: number
  volumeNote: string
  surfaceAreaM2: number
  footprintAreaM2: number
  footprintNote: string
  footprint: Ring[]
  heightM: number
  zMin: number
  zMax: number
  centroid: Vec3
  watertight: boolean
  meshVertexCount: number
  meshFaceCount: number
  confidence: number
  confidenceNote: string
  boundaryCorroboration: Record<string, number>
  notes: string[]
}

export interface UnitSpaceRef {
  globalId: string
  name: string
  longName: string | null
  fn: string | null
}

export interface PropertyUnit {
  id: string
  label: string
  classification: string
  /** 'inferred' as reported by the cadastral model. */
  status: string
  legalStatus: string
  ownershipStatus: string
  storeyIds: string[]
  storeyNames: string[]
  spaces: UnitSpaceRef[]
  groupingEvidence: Array<{ signal: string; detail: string }>
  groupingConfidence: number
  geometry: GeometryMetadata
  prototypeUlpin: string
  validationState: string
  warnings: string[]
  glbNode: string
  provenance: {
    derivation: string
    derivationMethod: string | null
    methodType: string
    modelStatus: string
    sourceIfc: string
    sourceIfcGlobalIds: string[]
  }
}

export interface ULPIN {
  code: string
  scheme: string
  dataset: string
  identifierClass: string
  isOfficial: boolean
  issuer: string
  parcelId: string | null
  buildingId: string
  unitId: string
  storeyIds: string[]
  storeyNames: string[]
  verticalExtentM: [number, number]
  geometryVersion: string
  sourceIds: string[]
  validationStatus: string
  legalStatus: string
  ownershipStatus: string
  cadastralStatus: string
  dataStatus: string
  derivationMethod: string
  unitStatus: string
  unitConfidence: number
  geometryConfidence: number
  disclaimer: string
}

export interface UlpinRegistry {
  scheme: string
  disclaimer: string
  count: number
  records: ULPIN[]
}

export type CheckStatus = 'passed' | 'warning' | 'failed' | 'incomplete' | 'not_run' | 'not_applicable' | string

export interface ValidationCheck {
  key: string
  title: string
  status: CheckStatus
  required: boolean
  /** note / reason / method strings exactly as reported. */
  remarks: string[]
  /** Scalar facts extracted from the check payload. */
  facts: Array<{ label: string; value: string }>
  /** Unit ids the check names (any list of PU-xx in the payload). */
  unitIds: string[]
}

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  checks: ValidationCheck[]
  statusCounts: Record<string, number>
  requiredChecks: string[]
  requiredChecksNotPassed: string[]
  validityDefinition: string
  totalUnitVolumeM3: number
  storeyCoverageRatio: Record<string, number>
  stackedPairs: Array<{ units: [string, string]; footprintOverlapM2: number; zOverlapM: number }>
  fallbackGeometryUnits: string[]
  spacesNotFullyCorroborated: string[]
  spacesDeviating: string[]
}

export interface Provenance {
  runTimestampUtc: string
  timestampNote: string
  environment: Record<string, string>
  ifc: { path: string; fileName: string; sha256: string; schema: string; lengthScaleToMetre: number; sourceMode: string }
  pointcloudInputs: Array<{ name: string; sizeBytes: number; parseStatus: string }>
  methods: Array<{ stage: string; methodType: string | null; modelStatus: string | null; official: boolean | null }>
  mlModelTrained: boolean | null
  crs: CoordinateReference
  legalNotice: string
}

export interface DataSource {
  key: string
  name: string
  tone: StatusTone
  statusLabel: string
  /** Raw status token from the pipeline, or null when the pipeline has no field for this source. */
  rawStatus: string | null
  source: string
  role: string
  processingState: string
  /** Which pipeline field(s) this row is read from. */
  basis: string
}

export interface PointCloudFile {
  name: string
  path: string
  format: string
  sizeBytes: number
  expectedSizeBytes: number | null
  parseStatus: string
  isLfsPointer: boolean
  pointCount: number | null
  bounds: [Vec3, Vec3] | null
  crsKnown: boolean
  crsStatement: string
  note: string | null
}

export interface PointCloudMetric {
  key: 'coverage' | 'alignment' | 'ifc_comparison'
  label: string
  status: string
  computed: boolean
  method: string | null
  reason: string | null
  perFile: Array<{ file: string; status: string }>
  /** Numeric results, only present when the pipeline produced them. */
  values: Array<{ label: string; value: string }>
}

export interface PointCloudStatus {
  inventoryStatus: string
  filesDetected: number
  filesProcessed: number
  filesLfsPointer: number
  formatSummary: Record<string, number>
  acquisitionStatement: string
  files: PointCloudFile[]
  metrics: PointCloudMetric[]
  registrationFilesFound: boolean | null
  /** true when at least one file was actually parsed into points. */
  hasPointData: boolean
}

export interface IfcSpace {
  globalId: string
  name: string
  longName: string | null
  storeyId: string
  storeyName: string
  classification: string
  fn: string
  groupScope: string
  classificationConfidence: number
  unitId: string | null
}

export interface IfcSpaceGeometry {
  globalId: string
  name: string
  storeyId: string
  method: string
  isFallback: boolean
  geometrySource: string
  confidence: number
  confidenceBasis: string
  corroboration: string | null
  volumeM3: number
  footprintAreaM2: number
  zMin: number
  zMax: number
  footprint: Ring
}

export interface CadastralStatus {
  modelVersion: string
  legalNotice: string
  hierarchyOrder: string[]
  parcel: { id: string | null; status: string; linkBasis: string | null; derivation: string; ownershipStatus: string }
  bagId: string | null
  terrainStatus: string
  underground: { status: string; entityCount: number; supportedTypes: string[]; notes: string[] }
  commonSpaces: Array<{ globalId: string; name: string; longName: string | null; classification: string; storeyName: string }>
  grouping: {
    spacesInUnits: number
    commonOrServiceSpaces: number
    unassignedPrivateLikeSpaces: number
    reassignedByGeometry: number
    ambiguousSpaceNames: string[]
  }
}

export interface Metrics {
  sourceMode: string
  buildings: number
  storeys: number
  ifcSpaces: number
  classifiedSpaces: number
  classCounts: Record<string, number>
  commonServiceSpaces: number
  propertyUnits: number
  prototypeUlpins: number
  nativeGeometries: number
  derivedGeometries: number
  spaceGeometryByMethod: Record<string, number>
  boundaryCorroboration: Record<string, number>
  meanSpaceConfidence: number
  spaceBoundariesInModel: number
  unitGeometryByStatus: Record<string, number>
  unitGeometryByRepresentation: Record<string, number>
  unitsWithGeometry: number
  unitsGeometryValid: number
  topologyValid: boolean
  checkStatusCounts: Record<string, number>
  declaredCountCheck: { declared: number; derived: number; agrees: boolean; note: string }
  ambiguousSpaceNames: string[]
  pointcloud: { detected: number; processed: number; lfsPointers: number; inventory: string; alignment: string; comparison: string }
  cadastralStatus: string
  terrainStatus: string
  droneImagery: string
  undergroundStatus: string
  gnssCorsControl: string
  coordinateStatus: string
}

/** Everything the app needs at start-up. */
export interface CadastreDataset {
  /** Dataset name as written into the ULPIN identity payload. */
  name: string
  building: Building
  storeys: Storey[]
  units: PropertyUnit[]
  ulpins: UlpinRegistry
  validation: ValidationResult
  metrics: Metrics
  cadastral: CadastralStatus
  spaces: IfcSpace[]
  dataSources: DataSource[]
  /** Optional resources: the UI shows an explicit error state when one failed. */
  provenance: Resource<Provenance>
  pointcloud: Resource<PointCloudStatus>
}

export type Resource<T> = { status: 'ready'; data: T } | { status: 'error'; error: string }
