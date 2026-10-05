import type { Storey } from '../types'

export type ThemeName = 'dark' | 'light'

export interface ScenePalette {
  background: string
  grid: string
  gridSection: string
  outline: string
  outlineActive: string
  envelope: string
  common: string
  native: string
  derived: string
  selected: string
  selectedEmissive: string
  edge: string
  storeyRamp: string[]
}

export const SCENE_PALETTE: Record<ThemeName, ScenePalette> = {
  dark: {
    background: '#081820',
    grid: '#16323a',
    gridSection: '#24525a',
    outline: '#6fa3aa',
    outlineActive: '#6ee5c0',
    envelope: '#9fd4dc',
    common: '#6c8791',
    native: '#6ee5c0',
    derived: '#d8a35d',
    selected: '#ffd166',
    selectedEmissive: '#8a5c0c',
    edge: '#06141a',
    storeyRamp: ['#3f9c8f', '#4a90b8', '#7684c9', '#a57cc0', '#c77f9a', '#c9966b'],
  },
  light: {
    background: '#e3ecec',
    grid: '#c9d8d8',
    gridSection: '#a5bcbc',
    outline: '#4c7178',
    outlineActive: '#0b8767',
    envelope: '#4c7178',
    common: '#8fa3a9',
    native: '#0e9a76',
    derived: '#c5822f',
    selected: '#f2a900',
    selectedEmissive: '#7a5200',
    edge: '#24383c',
    storeyRamp: ['#2f8f82', '#3a80ab', '#6272bd', '#9569b3', '#b96a88', '#b98250'],
  },
}

/** Storeys that carry property units get consecutive ramp colours, bottom to top. */
export function storeyColorMap(storeys: Storey[], palette: ScenePalette): Map<string, string> {
  const map = new Map<string, string>()
  let i = 0
  for (const storey of storeys) {
    if (storey.unitIds.length === 0) continue
    map.set(storey.id, palette.storeyRamp[i % palette.storeyRamp.length])
    i += 1
  }
  return map
}
