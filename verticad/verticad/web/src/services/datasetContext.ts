import { createContext, useContext } from 'react'
import type { CadastreDataset } from '../types'

export const DatasetContext = createContext<CadastreDataset | null>(null)

/** The loaded Schependomlaan dataset. Only valid below <DatasetGate>. */
export function useDataset(): CadastreDataset {
  const dataset = useContext(DatasetContext)
  if (!dataset) throw new Error('useDataset must be used inside <DatasetGate>')
  return dataset
}
