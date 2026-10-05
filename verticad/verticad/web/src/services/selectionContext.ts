import { createContext, useContext } from 'react'

export interface Selection {
  storeyId: string | null
  unitId: string | null
  spaceId: string | null
}

export interface SelectionApi extends Selection {
  selectStorey: (storeyId: string | null) => void
  selectUnit: (unitId: string | null) => void
  selectSpace: (spaceId: string | null) => void
  clear: () => void
}

export const SelectionContext = createContext<SelectionApi | null>(null)

export function useSelection(): SelectionApi {
  const api = useContext(SelectionContext)
  if (!api) throw new Error('useSelection must be used inside <SelectionProvider>')
  return api
}
