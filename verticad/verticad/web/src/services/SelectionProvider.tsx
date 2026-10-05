import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useDataset } from './datasetContext'
import { SelectionContext, type Selection, type SelectionApi } from './selectionContext'

const EMPTY: Selection = { storeyId: null, unitId: null, spaceId: null }

export function SelectionProvider({ children }: { children: ReactNode }) {
  const { units, spaces } = useDataset()
  const [selection, setSelection] = useState<Selection>(EMPTY)

  const selectStorey = useCallback(
    (storeyId: string | null) => {
      setSelection((current) => {
        const unit = units.find((u) => u.id === current.unitId)
        const keepUnit = Boolean(storeyId && unit?.storeyIds.includes(storeyId))
        return { storeyId, unitId: keepUnit ? current.unitId : null, spaceId: keepUnit ? current.spaceId : null }
      })
    },
    [units],
  )

  const selectUnit = useCallback(
    (unitId: string | null) => {
      setSelection((current) => {
        if (!unitId) return { ...current, unitId: null, spaceId: null }
        const unit = units.find((u) => u.id === unitId)
        if (!unit) return current
        // Keep the storey filter only if the unit is on it; never force one on.
        const storeyId = current.storeyId && unit.storeyIds.includes(current.storeyId) ? current.storeyId : null
        return { storeyId, unitId, spaceId: null }
      })
    },
    [units],
  )

  const selectSpace = useCallback(
    (spaceId: string | null) => {
      setSelection((current) => {
        if (!spaceId) return { ...current, spaceId: null }
        const space = spaces.find((s) => s.globalId === spaceId)
        if (!space) return current
        return { storeyId: space.unitId ? null : space.storeyId, unitId: space.unitId, spaceId }
      })
    },
    [spaces],
  )

  const clear = useCallback(() => setSelection(EMPTY), [])

  const api = useMemo<SelectionApi>(
    () => ({ ...selection, selectStorey, selectUnit, selectSpace, clear }),
    [selection, selectStorey, selectUnit, selectSpace, clear],
  )
  return <SelectionContext.Provider value={api}>{children}</SelectionContext.Provider>
}
