import type { CadastreDataset, Resource } from '../types'
import { fetchBuilding } from './building'
import { fetchCadastral } from './cadastral'
import { errorMessage } from './client'
import { composeDataSources } from './dataSources'
import { fetchStoreys } from './floors'
import { fetchMetrics } from './metrics'
import { fetchPointCloud } from './pointcloud'
import { fetchProvenance } from './provenance'
import { fetchSpaces } from './spaces'
import { fetchUlpins } from './ulpin'
import { fetchUnits } from './units'
import { fetchValidation } from './validation'

export { ApiError, DATA_MODE, ENDPOINTS, clearApiCache, endpointLabel, endpointUrl, errorMessage } from './client'
export { fetchSpaceGeometry } from './spaces'

async function optional<T>(promise: Promise<T>): Promise<Resource<T>> {
  try {
    return { status: 'ready', data: await promise }
  } catch (error) {
    return { status: 'error', error: errorMessage(error) }
  }
}

/** Load everything the app shell needs. Required resources reject; optional ones degrade to an error state. */
export async function loadDataset(): Promise<CadastreDataset> {
  const [building, storeys, units, ulpins, validation, metrics, cadastral, spaces, provenance, pointcloud] = await Promise.all([
    fetchBuilding(),
    fetchStoreys(),
    fetchUnits(),
    fetchUlpins(),
    fetchValidation(),
    fetchMetrics(),
    fetchCadastral(),
    fetchSpaces(),
    optional(fetchProvenance()),
    optional(fetchPointCloud()),
  ])
  return {
    name: ulpins.records[0]?.dataset ?? building.name,
    building,
    storeys,
    units,
    ulpins,
    validation,
    metrics,
    cadastral,
    spaces,
    provenance,
    pointcloud,
    dataSources: composeDataSources(metrics, cadastral, provenance, pointcloud),
  }
}
