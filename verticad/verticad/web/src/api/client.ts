/**
 * Single entry point for all data access.
 *
 * Two modes, selected at build/dev time:
 *  - static (default): reads the pipeline's own output files, copied verbatim to
 *    /public/data/schependomlaan by `npm run sync:data`.
 *  - http: when VITE_API_BASE_URL is set, calls GET {base}/api/... instead. The
 *    backend is expected to return the same pipeline JSON documents unchanged.
 *
 * No other module calls fetch().
 */

export interface EndpointSpec {
  /** REST path used in http mode. */
  api: string
  /** Pipeline output (relative to processed/) used in static mode. */
  file: string
}

export const ENDPOINTS = {
  building: { api: '/api/building', file: 'building.json' },
  floors: { api: '/api/floors', file: 'floors.json' },
  units: { api: '/api/units', file: 'property_units.json' },
  ulpins: { api: '/api/ulpins', file: 'ulpins.json' },
  validation: { api: '/api/validation', file: 'topology_validation.json' },
  provenance: { api: '/api/provenance', file: 'provenance.json' },
  metrics: { api: '/api/metrics', file: 'pipeline_report.json' },
  pointcloud: { api: '/api/pointcloud', file: 'pointcloud_inventory.json' },
  cadastral: { api: '/api/cadastral', file: '3d_cadastral_model.json' },
  spaces: { api: '/api/spaces', file: 'space_classification.json' },
  spaceGeometry: { api: '/api/spaces/geometry', file: 'geometry/space_geometry.json' },
  unitsGlb: { api: '/api/assets/property_units.glb', file: 'geometry/property_units.glb' },
} as const satisfies Record<string, EndpointSpec>

export type EndpointKey = keyof typeof ENDPOINTS

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '')
const STATIC_ROOT = `${import.meta.env.BASE_URL}data/schependomlaan/`

// http when VITE_DATA_MODE=http (API on the same origin / dev proxy, API_BASE empty) or when a base URL is given.
export const DATA_MODE: 'static' | 'http' =
  import.meta.env.VITE_DATA_MODE === 'static' ? 'static' : import.meta.env.VITE_DATA_MODE === 'http' || API_BASE ? 'http' : 'static'

export function endpointUrl(key: EndpointKey): string {
  const spec = ENDPOINTS[key]
  return DATA_MODE === 'http' ? `${API_BASE}${spec.api}` : `${STATIC_ROOT}${spec.file}`
}

/** Human-readable name of where a resource comes from (shown in error states). */
export function endpointLabel(key: EndpointKey): string {
  const spec = ENDPOINTS[key]
  return DATA_MODE === 'http' ? `GET ${spec.api}` : `processed/${spec.file}`
}

export class ApiError extends Error {
  readonly endpoint: EndpointKey
  readonly status: number | null
  constructor(endpoint: EndpointKey, message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.endpoint = endpoint
    this.status = status
  }
}

const cache = new Map<EndpointKey, Promise<unknown>>()

async function fetchJson(key: EndpointKey): Promise<unknown> {
  const label = endpointLabel(key)
  let response: Response
  try {
    response = await fetch(endpointUrl(key), { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError(key, `${label}: network request failed (is the data source running?)`)
  }
  if (!response.ok) throw new ApiError(key, `${label}: HTTP ${response.status}`, response.status)
  const text = await response.text()
  try {
    return JSON.parse(text) as unknown
  } catch {
    throw new ApiError(key, `${label}: response is not JSON (file missing or wrong path)`, response.status)
  }
}

/** Fetch a pipeline document once; concurrent and repeat callers share the result. */
export function getJson<T>(key: EndpointKey): Promise<T> {
  let pending = cache.get(key)
  if (!pending) {
    pending = fetchJson(key).catch((error: unknown) => {
      cache.delete(key)
      throw error
    })
    cache.set(key, pending)
  }
  return pending as Promise<T>
}

export function clearApiCache(): void {
  cache.clear()
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error'
}
