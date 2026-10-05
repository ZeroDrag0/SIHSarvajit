import { useDataset } from '../services/datasetContext'
import { fmtElevation } from '../utils/format'

/**
 * Schematic vertical stack: one row per IFC storey, one block per property unit.
 * Block width is proportional to the unit's footprint area. It is not a section drawing.
 */
export function StackDiagram({ selectedUnitId, onSelectUnit }: { selectedUnitId: string | null; onSelectUnit: (unitId: string) => void }) {
  const { storeys, units } = useDataset()
  const ordered = [...storeys].sort((a, b) => b.orderIndex - a.orderIndex)
  return (
    <figure className="stack">
      <div className="stack-rows">
        {ordered.map((storey) => {
          const row = units.filter((u) => storey.unitIds.includes(u.id))
          return (
            <div className="stack-row" key={storey.id}>
              <div className="stack-label">
                <strong>{storey.name}</strong>
                <span>{fmtElevation(storey.elevationM)}</span>
              </div>
              <div className={`stack-units${row.length === 0 ? ' is-empty' : ''}`}>
                {row.length === 0 && <span>no property units</span>}
                {row.map((unit) => (
                  <button
                    key={unit.id}
                    type="button"
                    className={unit.id === selectedUnitId ? 'is-active' : ''}
                    style={{ flexGrow: unit.geometry.footprintAreaM2 }}
                    onClick={() => onSelectUnit(unit.id)}
                    title={`${unit.id} · ${unit.prototypeUlpin}`}
                  >
                    {unit.id}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
      <figcaption>Schematic stack from IFC storeys. Block width ∝ unit footprint area. Select a unit to open it in 3D.</figcaption>
    </figure>
  )
}
