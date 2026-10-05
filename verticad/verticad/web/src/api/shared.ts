import type { CoordinateReference, RawCoordinateReference, RawFootprint, Ring } from '../types'

/** Flatten a GeoJSON Polygon / MultiPolygon to its outer rings. */
export function outerRings(footprint: RawFootprint): Ring[] {
  if (footprint.type === 'Polygon') return footprint.coordinates.slice(0, 1)
  return footprint.coordinates.map((polygon) => polygon[0]).filter((ring): ring is Ring => Array.isArray(ring))
}

export function toCoordinateReference(raw: RawCoordinateReference): CoordinateReference {
  const status = raw.coordinate_status.toLowerCase()
  return {
    sourceCrs: raw.source_crs,
    declaredInIfc: raw.source_crs_declared_in_ifc ?? null,
    targetCrs: raw.target_crs,
    verticalReference: raw.vertical_reference,
    transformationStatus: raw.transformation_status,
    coordinateStatus: raw.coordinate_status,
    gnssCorsControl: raw.gnss_cors_control ?? null,
    notes: raw.notes ?? [],
    isVerified: raw.target_crs !== null && !status.includes('unverified') && !status.includes('local'),
  }
}

export function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}
