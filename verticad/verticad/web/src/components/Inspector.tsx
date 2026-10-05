import { useDataset } from '../services/datasetContext'
import { useSelection } from '../services/selectionContext'
import type { IfcSpaceGeometry, PropertyUnit, Storey } from '../types'
import { fileName } from '../api/shared'
import { fmt, fmtElevation, fmtInt, fmtRange } from '../utils/format'
import { ringsBounds } from '../utils/geometry'
import { humanise } from '../utils/status'
import { GeometrySourceBadge } from './GeometrySource'
import { Field } from './Layout'
import { StatusBadge } from './StatusBadge'
import { UlpinPanel } from './UlpinPanel'

interface InspectorProps {
  /** Room-level geometry, when the viewer has loaded it. */
  spaceGeometry?: IfcSpaceGeometry[] | null
  footer?: React.ReactNode
}

export function Inspector({ spaceGeometry, footer }: InspectorProps) {
  const { units, storeys } = useDataset()
  const selection = useSelection()
  const unit = units.find((u) => u.id === selection.unitId)
  const storey = storeys.find((s) => s.id === selection.storeyId)

  return (
    <div className="inspector">
      {selection.spaceId && <SpaceCard spaceId={selection.spaceId} spaceGeometry={spaceGeometry ?? null} />}
      {unit ? <UnitInspector unit={unit} /> : storey ? <StoreyInspector storey={storey} /> : selection.spaceId ? null : <BuildingInspector />}
      {footer}
    </div>
  )
}

function SpaceCard({ spaceId, spaceGeometry }: { spaceId: string; spaceGeometry: IfcSpaceGeometry[] | null }) {
  const { spaces } = useDataset()
  const selection = useSelection()
  const space = spaces.find((s) => s.globalId === spaceId)
  const geometry = spaceGeometry?.find((g) => g.globalId === spaceId)
  if (!space) return null
  return (
    <section className="inspector-section inspector-section--space">
      <div className="inspector-head">
        <div>
          <span className="eyebrow">IFC space</span>
          <h2>{space.name}{space.longName ? ` · ${space.longName}` : ''}</h2>
        </div>
        <button type="button" className="icon-btn" aria-label="Clear space selection" onClick={() => selection.selectSpace(null)}>×</button>
      </div>
      <dl className="fields">
        <Field label="GlobalId" mono>{space.globalId}</Field>
        <Field label="Storey">{space.storeyName}</Field>
        <Field label="Class">{humanise(space.classification)}</Field>
        <Field label="Belongs to">{space.unitId ?? 'Common / service (no unit)'}</Field>
        {geometry ? (
          <>
            <Field label="Geometry source"><StatusBadge tone={geometry.isFallback ? 'derived' : 'available'} label={geometry.isFallback ? 'Derived · FootPrint + Box' : 'Native IFC Body'} /></Field>
            <Field label="Volume">{fmt(geometry.volumeM3)} m³</Field>
            <Field label="Boundary check"><StatusBadge raw={geometry.corroboration} /></Field>
            <Field label="Confidence">{geometry.confidence.toFixed(2)}</Field>
          </>
        ) : (
          <Field label="Geometry">Loads with the IFC spaces layer</Field>
        )}
      </dl>
      {geometry && <p className="note">{geometry.confidenceBasis}</p>}
    </section>
  )
}

function UnitInspector({ unit }: { unit: PropertyUnit }) {
  const { ulpins, validation } = useDataset()
  const selection = useSelection()
  const record = ulpins.records.find((r) => r.unitId === unit.id)
  const g = unit.geometry
  const bounds = ringsBounds(g.footprint)
  const inFallbackList = validation.fallbackGeometryUnits.includes(unit.id)
  const corroboration = Object.entries(g.boundaryCorroboration)

  return (
    <>
      <section className="inspector-section">
        <div className="inspector-head">
          <div>
            <span className="eyebrow">Property unit</span>
            <h2>{unit.id}</h2>
          </div>
          <button type="button" className="icon-btn" aria-label="Clear unit selection" onClick={() => selection.selectUnit(null)}>×</button>
        </div>
        <p className="inspector-sub">{unit.label}</p>
        <div className="badge-row">
          <StatusBadge raw={unit.status} />
          <StatusBadge raw={unit.legalStatus} />
        </div>
      </section>

      <section className="inspector-section">
        {record ? <UlpinPanel record={record} /> : <p className="note">No prototype ULPIN record for this unit in ulpins.json.</p>}
      </section>

      <section className="inspector-section">
        <span className="eyebrow">Geometry</span>
        <dl className="fields">
          <Field label="Storey">{unit.storeyNames.join(', ')}</Field>
          <Field label="Volume">{fmt(g.volumeM3)} m³</Field>
          <Field label="Footprint">{fmt(g.footprintAreaM2)} m²</Field>
          <Field label="Height">{fmt(g.heightM)} m</Field>
          <Field label="Z extent">{fmtRange(g.zMin, g.zMax)}</Field>
          {bounds && <Field label="Plan extent">{fmt(bounds.maxX - bounds.minX)} × {fmt(bounds.maxY - bounds.minY)} m</Field>}
          <Field label="Surface area">{fmt(g.surfaceAreaM2)} m²</Field>
          <Field label="Mesh">{fmtInt(g.meshFaceCount)} faces · {g.watertight ? 'watertight' : 'not watertight'}</Field>
        </dl>
        <p className="note">{g.volumeNote}; {g.footprintNote}.</p>
      </section>

      <section className="inspector-section">
        <span className="eyebrow">Geometry source</span>
        <div className="badge-row"><GeometrySourceBadge kind={g.sourceKind} /></div>
        <p className="note">{g.sourceText}</p>
        <dl className="fields">
          <Field label="Derived spaces">{g.fallbackSpaceCount} of {g.fallbackSpaceCount + g.bodySpaceCount}</Field>
          <Field label="Native Body spaces">{g.bodySpaceCount}</Field>
          <Field label="Representation" mono>{g.representation}</Field>
          <Field label="Geometry confidence">{g.confidence.toFixed(2)}</Field>
          <Field label="Grouping confidence">{unit.groupingConfidence.toFixed(2)}</Field>
        </dl>
        {corroboration.length > 0 && (
          <div className="badge-row">
            {corroboration.map(([status, count]) => <StatusBadge key={status} raw={status} label={`${count} ${humanise(status).toLowerCase()}`} />)}
          </div>
        )}
        <p className="note">{g.confidenceNote}. Not survey-grade; no point-cloud or GNSS check was applied.</p>
      </section>

      <section className="inspector-section">
        <span className="eyebrow">Validation</span>
        <div className="badge-row">
          <StatusBadge raw={unit.validationState} />
          {inFallbackList && <StatusBadge tone="warning" label="Fallback geometry" title="listed in checks.invalid_geometry.fallback_geometry_units" />}
        </div>
        {unit.warnings.length > 0 && (
          <ul className="warning-list">
            {unit.warnings.map((w) => <li key={w}>{w}</li>)}
          </ul>
        )}
        <p className="note">
          {validation.requiredChecks.length - validation.requiredChecksNotPassed.length} of {validation.requiredChecks.length} required topology checks passed for the building.
        </p>
      </section>

      <section className="inspector-section">
        <details className="disclosure" open>
          <summary>Source IFC spaces · {unit.spaces.length}</summary>
          <ul className="space-list">
            {unit.spaces.map((space) => (
              <li key={space.globalId}>
                <button type="button" className={selection.spaceId === space.globalId ? 'is-active' : ''} onClick={() => selection.selectSpace(space.globalId)} title={space.globalId}>
                  <span className="mono">{space.name}</span>
                  <span>{space.longName ?? '—'}</span>
                </button>
              </li>
            ))}
          </ul>
        </details>
      </section>

      <section className="inspector-section">
        <span className="eyebrow">Provenance</span>
        <dl className="fields">
          <Field label="Derivation" stack>{unit.provenance.derivationMethod ?? unit.provenance.derivation}</Field>
          <Field label="Method"><StatusBadge raw={unit.provenance.methodType} /></Field>
          <Field label="Source file" stack><span className="mono" title={unit.provenance.sourceIfc}>{fileName(unit.provenance.sourceIfc)}</span></Field>
          <Field label="Ownership"><StatusBadge raw={unit.ownershipStatus} /></Field>
        </dl>
        {unit.groupingEvidence.length > 0 && (
          <details className="disclosure">
            <summary>Grouping evidence · {unit.groupingEvidence.length} signals</summary>
            <ul className="evidence-list">
              {unit.groupingEvidence.map((e) => <li key={e.signal}><strong>{humanise(e.signal)}</strong><span>{e.detail}</span></li>)}
            </ul>
          </details>
        )}
      </section>
    </>
  )
}

function StoreyInspector({ storey }: { storey: Storey }) {
  const { units } = useDataset()
  const selection = useSelection()
  const storeyUnits = units.filter((u) => storey.unitIds.includes(u.id))
  const measured = storey.zSource === 'measured_space_geometry'
  return (
    <>
      <section className="inspector-section">
        <div className="inspector-head">
          <div>
            <span className="eyebrow">Storey</span>
            <h2>{storey.name}</h2>
          </div>
          <button type="button" className="icon-btn" aria-label="Clear storey selection" onClick={() => selection.selectStorey(null)}>×</button>
        </div>
        <dl className="fields">
          <Field label="Elevation">{fmtElevation(storey.elevationM)}</Field>
          <Field label="Z extent">{fmtRange(storey.zMin, storey.zMax)}</Field>
          <Field label="Height">{storey.heightM === null ? 'Not measured' : `${fmt(storey.heightM)} m`}</Field>
          <Field label="Nominal height">{storey.nominalHeightM === null ? '—' : `${fmt(storey.nominalHeightM)} m`}</Field>
          <Field label="Geometry status">
            <StatusBadge tone={measured ? 'derived' : 'unverified'} label={measured ? 'Measured from space geometry' : 'Nominal IFC elevation only'} title={`z_source: ${storey.zSource}`} />
          </Field>
          <Field label="Property units">{storey.unitIds.length}</Field>
          <Field label="IFC spaces">{storey.spaceCount}</Field>
          <Field label="GlobalId" mono>{storey.id}</Field>
        </dl>
        {storey.verticalReference && <p className="note">{storey.verticalReference}</p>}
        {storey.warnings.length > 0 && <ul className="warning-list">{storey.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
      </section>
      <section className="inspector-section">
        <span className="eyebrow">Units on this storey</span>
        {storeyUnits.length === 0 ? (
          <p className="note">No property units on this storey. It has no IfcSpaces in the model.</p>
        ) : (
          <div className="unit-picker">
            {storeyUnits.map((u) => (
              <button key={u.id} type="button" onClick={() => selection.selectUnit(u.id)}>
                <strong>{u.id}</strong>
                <small>{fmt(u.geometry.volumeM3, 0)} m³</small>
              </button>
            ))}
          </div>
        )}
      </section>
      {storey.spaceClasses.length > 0 && (
        <section className="inspector-section">
          <span className="eyebrow">Space classes present</span>
          <div className="badge-row">
            {storey.spaceClasses.map((c) => <StatusBadge key={c} tone="neutral" label={humanise(c)} />)}
          </div>
        </section>
      )}
    </>
  )
}

function BuildingInspector() {
  const { name, building, metrics, validation, cadastral } = useDataset()
  return (
    <>
      <section className="inspector-section">
        <span className="eyebrow">Building</span>
        <h2 className="inspector-title">{name}</h2>
        <p className="inspector-sub">Select a storey or a property unit to open its record.</p>
        <dl className="fields">
          <Field label="IFC name">{building.name}</Field>
          <Field label="GlobalId" mono>{building.id}</Field>
          <Field label="Storeys">{building.storeyCount}</Field>
          <Field label="Property units">{metrics.propertyUnits}</Field>
          <Field label="Space envelope height">{fmt(building.heightM)} m</Field>
          <Field label="Footprint">{fmt(building.footprintAreaM2)} m²</Field>
          <Field label="Extraction"><StatusBadge raw={building.status} /></Field>
        </dl>
        <p className="note">{building.geometryBasis}. Footprint: {building.footprintNote}.</p>
      </section>
      <section className="inspector-section">
        <span className="eyebrow">Context</span>
        <dl className="fields">
          <Field label="Parcel"><StatusBadge raw={cadastral.parcel.status} /></Field>
          <Field label="Terrain"><StatusBadge raw={building.terrainStatus} /></Field>
          <Field label="Coordinates"><StatusBadge raw={building.crs.coordinateStatus} /></Field>
          <Field label="Topology">
            <StatusBadge tone={validation.valid ? (validation.warnings.length ? 'warning' : 'validated') : 'error'} label={validation.valid ? `Valid · ${validation.warnings.length} warning(s)` : `${validation.errors.length} error(s)`} />
          </Field>
        </dl>
      </section>
    </>
  )
}
