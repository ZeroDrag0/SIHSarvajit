import { useDataset } from '../services/datasetContext'
import type { SpaceGeometryState } from '../services/useSpaceGeometry'
import { statusDisplay } from '../utils/status'
import type { LayerKey, ViewerSettings } from './settings'

interface LayerPanelProps {
  settings: ViewerSettings
  roomsForced: boolean
  spaceGeometry: SpaceGeometryState
  onToggle: (layer: LayerKey) => void
}

interface Row {
  key: string
  label: string
  note: string
  layer?: LayerKey
  available: boolean
  state?: string
}

/** Layer switches. A layer is only switchable when the pipeline produced data for it. */
export function LayerPanel({ settings, roomsForced, spaceGeometry, onToggle }: LayerPanelProps) {
  const { cadastral, metrics, pointcloud } = useDataset()
  const geometryNote =
    spaceGeometry.status === 'loading' ? 'Loading room geometry…'
    : spaceGeometry.status === 'error' ? `Unavailable: ${spaceGeometry.error}`
    : null
  const parcel = statusDisplay(cadastral.parcel.status).label
  const hasPoints = pointcloud.status === 'ready' && pointcloud.data.hasPointData

  const rows: Row[] = [
    { key: 'building', label: 'Building', layer: 'building', available: true, note: 'Space envelope from IfcSpace footprints. Walls and slabs are not exported by the pipeline.' },
    { key: 'storeys', label: 'Storey levels', layer: 'storeys', available: true, note: 'Dashed = nominal IFC elevation only' },
    { key: 'units', label: 'Property units', layer: 'units', available: true, note: `${metrics.propertyUnits} inferred units · property_units.glb` },
    { key: 'rooms', label: 'IFC spaces', layer: 'rooms', available: spaceGeometry.status !== 'error', note: geometryNote ?? `${cadastral.grouping.spacesInUnits} rooms inside units · footprint × height display`, state: roomsForced ? 'auto · space selected' : undefined },
    { key: 'common', label: 'Common / service', layer: 'common', available: spaceGeometry.status !== 'error', note: geometryNote ?? `${cadastral.grouping.commonOrServiceSpaces} spaces outside any unit` },
    { key: 'labels', label: 'Storey labels', layer: 'labels', available: true, note: '' },
    { key: 'parcel', label: 'Parcel', available: false, note: 'Cadastral parcel boundary unavailable', state: parcel },
    { key: 'boundary', label: 'Cadastral boundary', available: false, note: 'No cadastral / BAG file supplied', state: parcel },
    { key: 'pointcloud', label: 'Point cloud', available: false, note: hasPoints ? 'Parsed, but no renderable point asset in the pipeline outputs' : `${metrics.pointcloud.processed} of ${metrics.pointcloud.detected} files processed`, state: statusDisplay(metrics.pointcloud.inventory).label },
    { key: 'dtm', label: 'DTM', available: false, note: 'No terrain raster supplied', state: statusDisplay(metrics.terrainStatus).label },
    { key: 'dsm', label: 'DSM', available: false, note: 'No surface raster supplied', state: statusDisplay(metrics.terrainStatus).label },
    { key: 'underground', label: 'Underground', available: false, note: 'Underground data unavailable', state: statusDisplay(cadastral.underground.status).label },
  ]

  return (
    <section className="layers">
      <header className="rail-head"><span className="eyebrow">Data layers</span></header>
      <ul>
        {rows.map((row) => {
          const forced = row.key === 'rooms' && roomsForced
          const checked = row.layer ? settings.layers[row.layer] || forced : false
          return (
            <li key={row.key} className={row.available ? '' : 'is-disabled'}>
              <label>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!row.available || forced}
                  onChange={() => row.layer && onToggle(row.layer)}
                />
                <span className="layer-name">{row.label.toUpperCase()}</span>
                {row.state && <span className="layer-state">{row.state}</span>}
              </label>
              {row.note && <small>{row.note}</small>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
