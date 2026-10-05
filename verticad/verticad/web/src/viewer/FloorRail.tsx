import type { Storey } from '../types'
import { fmtElevation } from '../utils/format'

interface FloorRailProps {
  storeys: Storey[]
  selectedId: string | null
  onSelect: (storeyId: string | null) => void
}

/** Storey list, top storey first. Built entirely from floors.json. */
export function FloorRail({ storeys, selectedId, onSelect }: FloorRailProps) {
  const ordered = [...storeys].sort((a, b) => b.orderIndex - a.orderIndex)
  const index = ordered.findIndex((s) => s.id === selectedId)
  const step = (delta: number) => {
    if (ordered.length === 0) return
    const next = index < 0 ? (delta < 0 ? 0 : ordered.length - 1) : Math.min(Math.max(index + delta, 0), ordered.length - 1)
    onSelect(ordered[next].id)
  }
  return (
    <section className="rail">
      <header className="rail-head">
        <span className="eyebrow">Storeys · {storeys.length}</span>
        <div className="rail-controls">
          <button type="button" aria-label="Storey above" onClick={() => step(-1)}>↑</button>
          <button type="button" aria-label="Storey below" onClick={() => step(1)}>↓</button>
        </div>
      </header>
      <div className="floor-rail" role="listbox" aria-label="Storeys">
        <button type="button" role="option" aria-selected={selectedId === null} className={selectedId === null ? 'selected' : ''} onClick={() => onSelect(null)}>
          <i />
          <span className="floor-name">All storeys</span>
          <span className="floor-meta">full building</span>
        </button>
        {ordered.map((storey) => (
          <button
            key={storey.id}
            type="button"
            role="option"
            aria-selected={storey.id === selectedId}
            className={`${storey.id === selectedId ? 'selected' : ''}${storey.unitIds.length === 0 ? ' is-empty' : ''}`}
            onClick={() => onSelect(storey.id === selectedId ? null : storey.id)}
          >
            <i />
            <span className="floor-name">{storey.name}</span>
            <span className="floor-meta">
              {fmtElevation(storey.elevationM)} · {storey.unitIds.length === 0 ? 'no units' : `${storey.unitIds.length} unit${storey.unitIds.length === 1 ? '' : 's'}`}
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
