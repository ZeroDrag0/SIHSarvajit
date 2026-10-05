export type LayerKey = 'building' | 'storeys' | 'units' | 'rooms' | 'common' | 'labels'
export type ColorMode = 'storey' | 'source'
export type CameraView = 'iso' | 'top' | 'front' | 'side'

export interface ViewerSettings {
  layers: Record<LayerKey, boolean>
  colorMode: ColorMode
  /** 0.15 – 1 */
  unitOpacity: number
  /** Vertical separation between storeys in metres (display only). */
  explode: number
  /** Hide (rather than fade) everything outside the selected storey. */
  isolate: boolean
}

export const DEFAULT_SETTINGS: ViewerSettings = {
  layers: { building: true, storeys: true, units: true, rooms: false, common: true, labels: true },
  colorMode: 'storey',
  unitOpacity: 0.9,
  explode: 0,
  isolate: false,
}

export const CAMERA_VIEWS: Array<{ key: CameraView; label: string }> = [
  { key: 'iso', label: 'ISO' },
  { key: 'top', label: 'TOP' },
  { key: 'front', label: 'FRONT' },
  { key: 'side', label: 'SIDE' },
]
