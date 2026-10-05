import { useMemo, useState } from 'react'
import { Field, Page, Panel } from '../components/Layout'
import { UnavailableState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useDataset } from '../services/datasetContext'
import { navigate } from '../services/router'
import { useSelection } from '../services/selectionContext'
import { useSpaceGeometry } from '../services/useSpaceGeometry'
import type { Ring } from '../types'
import { fmt } from '../utils/format'
import { ringArea, ringCentroid, ringsBounds } from '../utils/geometry'
import { statusDisplay } from '../utils/status'

const PAD = 2.5
const GRID = 5

type PlanLayer = 'building' | 'units' | 'common'

export function SpatialPage() {
  const { building, storeys, units, spaces, cadastral } = useDataset()
  const selection = useSelection()
  const inhabited = storeys.filter((s) => s.unitIds.length > 0)
  const [storeyChoice, setStoreyChoice] = useState<string | null>(null)
  const [layers, setLayers] = useState<Record<PlanLayer, boolean>>({ building: true, units: true, common: true })
  const selectedUnit = units.find((u) => u.id === selection.unitId)
  const storeyId = storeyChoice ?? selectedUnit?.storeyIds[0] ?? selection.storeyId ?? inhabited[0]?.id ?? null
  const storey = storeys.find((s) => s.id === storeyId)
  const spaceGeometry = useSpaceGeometry(layers.common)

  const bounds = useMemo(() => ringsBounds(building.footprint) ?? { minX: 0, minY: 0, maxX: 1, maxY: 1 }, [building])
  const view = { x: bounds.minX - PAD, y: bounds.minY - PAD, w: bounds.maxX - bounds.minX + PAD * 2, h: bounds.maxY - bounds.minY + PAD * 2 }
  // SVG y grows downward; IFC y grows "up" the plan.
  const fy = (y: number) => view.y + view.h - (y - view.y)
  const path = (ring: Ring) => `${ring.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(3)} ${fy(y).toFixed(3)}`).join(' ')} Z`

  const gridX: number[] = []
  for (let x = Math.ceil(view.x / GRID) * GRID; x <= view.x + view.w; x += GRID) gridX.push(x)
  const gridY: number[] = []
  for (let y = Math.ceil(view.y / GRID) * GRID; y <= view.y + view.h; y += GRID) gridY.push(y)

  const storeyUnits = units.filter((u) => storeyId !== null && u.storeyIds.includes(storeyId))
  const commonIds = new Set(spaces.filter((s) => s.unitId === null && s.storeyId === storeyId).map((s) => s.globalId))
  const commonRooms = spaceGeometry.status === 'ready' ? spaceGeometry.data.filter((g) => commonIds.has(g.globalId)) : []
  const toggle = (layer: PlanLayer) => setLayers((l) => ({ ...l, [layer]: !l[layer] }))
  const parcelLabel = statusDisplay(cadastral.parcel.status).label

  return (
    <Page
      eyebrow="Spatial context"
      title="Plan view in IFC local coordinates"
      lede="Footprints as exported by the pipeline. There is no basemap because the model is not georeferenced."
      aside={<StatusBadge raw={building.crs.coordinateStatus} label={`Coordinate reference: ${building.crs.coordinateStatus}`} />}
    >
      <div className="split split--map">
        <div className="map-col">
          <div className="chip-row" role="group" aria-label="Storey">
            {inhabited.map((s) => (
              <button key={s.id} type="button" className={`chip${s.id === storeyId ? ' active' : ''}`} onClick={() => { setStoreyChoice(s.id); selection.selectUnit(null) }}>{s.name}</button>
            ))}
          </div>
          <div className="map-canvas">
            <svg viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`} role="img" aria-label={`Plan of ${storey?.name ?? 'building'} in IFC local metres`} preserveAspectRatio="xMidYMid meet">
              <g className="map-grid">
                {gridX.map((x) => <line key={`x${x}`} x1={x} x2={x} y1={view.y} y2={view.y + view.h} />)}
                {gridY.map((y) => <line key={`y${y}`} y1={fy(y)} y2={fy(y)} x1={view.x} x2={view.x + view.w} />)}
              </g>
              <g className="map-axis">
                {gridX.map((x) => <text key={`tx${x}`} x={x} y={view.y + view.h - 0.35} textAnchor="middle">{x}</text>)}
                {gridY.map((y) => <text key={`ty${y}`} x={view.x + 0.3} y={fy(y) + 0.22}>{y}</text>)}
              </g>
              {layers.building && building.footprint.map((ring, i) => <path key={i} className="map-building" d={path(ring)} />)}
              {layers.common && commonRooms.map((room) => {
                const [cx, cy] = ringCentroid(room.footprint)
                return (
                  <g key={room.globalId}>
                    <path className="map-common" d={path(room.footprint)}><title>{room.name} · common / service</title></path>
                    <text className="map-label map-label--sm" x={cx} y={fy(cy) + 0.15} textAnchor="middle">{room.name}</text>
                  </g>
                )
              })}
              {layers.units && storeyUnits.map((unit) => {
                const largest = [...unit.geometry.footprint].sort((a, b) => ringArea(b) - ringArea(a))[0]
                const [cx, cy] = largest ? ringCentroid(largest) : [0, 0]
                const active = unit.id === selection.unitId
                return (
                  <g
                    key={unit.id}
                    className={`map-unit${active ? ' is-active' : ''}`}
                    tabIndex={0}
                    role="button"
                    aria-label={`Select ${unit.id}`}
                    onClick={() => selection.selectUnit(unit.id)}
                    onKeyDown={(e) => { if (e.key === 'Enter') selection.selectUnit(unit.id) }}
                  >
                    {unit.geometry.footprint.map((ring, i) => <path key={i} d={path(ring)} />)}
                    <text className="map-label" x={cx} y={fy(cy) + 0.25} textAnchor="middle">{unit.id}</text>
                  </g>
                )
              })}
              <g className="map-scale" transform={`translate(${view.x + view.w - 6.2} ${view.y + view.h - 1.1})`}>
                <line x1={0} x2={5} y1={0} y2={0} />
                <line x1={0} x2={0} y1={-0.25} y2={0.25} />
                <line x1={5} x2={5} y1={-0.25} y2={0.25} />
                <text x={2.5} y={-0.4} textAnchor="middle">5 m</text>
              </g>
            </svg>
            <div className="map-tag map-tag--tl">X / Y in IFC local metres · orientation to true north not verified</div>
            <div className="map-tag map-tag--bl">Cadastral parcel boundary unavailable</div>
          </div>
          <p className="note">{building.footprintNote}. Unit footprints: union of net room footprints, so wall thickness appears as gaps.</p>
        </div>

        <aside className="split-aside">
          <Panel title="Plan layers">
            <ul className="layer-list">
              <li><label><input type="checkbox" checked={layers.building} onChange={() => toggle('building')} /><span>Building footprint</span></label><small>{fmt(building.footprintAreaM2)} m²</small></li>
              <li><label><input type="checkbox" checked={layers.units} onChange={() => toggle('units')} /><span>Property-unit footprints</span></label><small>{storeyUnits.length} on this storey</small></li>
              <li>
                <label><input type="checkbox" checked={layers.common} onChange={() => toggle('common')} /><span>Common / service spaces</span></label>
                <small>{spaceGeometry.status === 'loading' ? 'Loading…' : spaceGeometry.status === 'error' ? 'Unavailable' : `${commonIds.size} on this storey`}</small>
              </li>
              <li className="is-disabled"><label><input type="checkbox" disabled checked={false} readOnly /><span>Parcel</span></label><small>{parcelLabel}</small></li>
              <li className="is-disabled"><label><input type="checkbox" disabled checked={false} readOnly /><span>Cadastral boundary</span></label><small>{parcelLabel}</small></li>
            </ul>
          </Panel>
          <Panel title="Cadastral parcel">
            <UnavailableState title="Cadastral parcel boundary unavailable">
              {cadastral.parcel.derivation}. No parcel is drawn and no parcel id is assigned.
            </UnavailableState>
          </Panel>
          <Panel title="Coordinate reference">
            <dl className="fields">
              <Field label="Source">{building.crs.sourceCrs}</Field>
              <Field label="Target CRS">{building.crs.targetCrs ?? 'None'}</Field>
              <Field label="Transformation"><StatusBadge raw={building.crs.transformationStatus} /></Field>
              <Field label="Vertical">{building.crs.verticalReference}</Field>
              <Field label="Extent X">{fmt(bounds.minX)} → {fmt(bounds.maxX)} m</Field>
              <Field label="Extent Y">{fmt(bounds.minY)} → {fmt(bounds.maxY)} m</Field>
            </dl>
          </Panel>
          {selectedUnit && (
            <Panel title={selectedUnit.id} action={<button type="button" className="btn btn--sm" onClick={() => navigate('viewer')}>View in 3D</button>}>
              <dl className="fields">
                <Field label="Prototype 3D ULPIN" stack><span className="mono">{selectedUnit.prototypeUlpin}</span></Field>
                <Field label="Footprint">{fmt(selectedUnit.geometry.footprintAreaM2)} m²</Field>
                <Field label="Storey">{selectedUnit.storeyNames.join(', ')}</Field>
              </dl>
            </Panel>
          )}
        </aside>
      </div>
    </Page>
  )
}
