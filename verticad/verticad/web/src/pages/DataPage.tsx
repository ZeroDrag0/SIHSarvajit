import { Field, Page, Panel } from '../components/Layout'
import { ErrorState, UnavailableState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { DATA_MODE } from '../api'
import { useDataset } from '../services/datasetContext'
import { fmt, fmtBytes, fmtInt, fmtTimestamp, shortHash } from '../utils/format'
import { humanise } from '../utils/status'

export function DataPage() {
  const { dataSources, provenance, pointcloud, building, cadastral, metrics } = useDataset()
  const crs = building.crs

  return (
    <Page
      eyebrow="Data & provenance"
      title="What this run is built on"
      lede="Each source is listed with its real status. Missing inputs are shown as missing; nothing is substituted."
      aside={<StatusBadge tone="neutral" label={DATA_MODE === 'http' ? 'Live API' : 'Pipeline output files'} title="Data access mode of this frontend" />}
    >
      <Panel title="Data sources">
        <div className="table-wrap">
          <table className="table table--sources">
            <thead><tr><th>Source</th><th>Status</th><th>Supplied</th><th>Role</th><th>Processing state</th></tr></thead>
            <tbody>
              {dataSources.map((s) => (
                <tr key={s.key}>
                  <td><strong>{s.name}</strong><small className="mono">{s.basis}</small></td>
                  <td><StatusBadge tone={s.tone} label={s.statusLabel} title={s.rawStatus ? `pipeline value: ${s.rawStatus}` : 'no pipeline field for this source'} /></td>
                  <td>{s.source}</td>
                  <td>{s.role}</td>
                  <td>{s.processingState}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid-2">
        <Panel title="Run provenance">
          {provenance.status === 'error' ? (
            <ErrorState title="Provenance unavailable" detail={provenance.error} />
          ) : (
            <>
              <dl className="fields">
                <Field label="Run">{fmtTimestamp(provenance.data.runTimestampUtc)}</Field>
                <Field label="IFC file" stack><span className="mono" title={provenance.data.ifc.path}>{provenance.data.ifc.fileName}</span></Field>
                <Field label="Schema" mono>{provenance.data.ifc.schema}</Field>
                <Field label="SHA-256" mono><span title={provenance.data.ifc.sha256}>{shortHash(provenance.data.ifc.sha256)}</span></Field>
                <Field label="Length unit → m">{provenance.data.ifc.lengthScaleToMetre}</Field>
                <Field label="Trained ML model">{provenance.data.mlModelTrained === null ? '—' : provenance.data.mlModelTrained ? 'Yes' : 'None (rule-based)'}</Field>
              </dl>
              <p className="note">{provenance.data.legalNotice}</p>
              <details className="disclosure">
                <summary>Methods · {provenance.data.methods.length} stages</summary>
                <ul className="method-list">
                  {provenance.data.methods.map((m) => (
                    <li key={m.stage}>
                      <span>{humanise(m.stage)}</span>
                      <span>
                        {m.methodType && <StatusBadge raw={m.methodType} />}
                        {m.modelStatus && <StatusBadge raw={m.modelStatus} />}
                        {m.official === false && <StatusBadge tone="prototype" label="Not official" />}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
              <details className="disclosure">
                <summary>Environment</summary>
                <dl className="fields fields--dense">
                  {Object.entries(provenance.data.environment).map(([k, v]) => <Field key={k} label={k} mono>{v}</Field>)}
                </dl>
              </details>
            </>
          )}
        </Panel>

        <Panel title="Coordinate reference">
          <div className="badge-row"><StatusBadge raw={crs.coordinateStatus} label={`Coordinate reference: ${crs.coordinateStatus}`} /></div>
          <dl className="fields">
            <Field label="Source CRS">{crs.sourceCrs}</Field>
            <Field label="Declared in IFC">{crs.declaredInIfc ?? 'None'}</Field>
            <Field label="Target CRS">{crs.targetCrs ?? 'None'}</Field>
            <Field label="Transformation"><StatusBadge raw={crs.transformationStatus} /></Field>
            <Field label="Vertical reference">{crs.verticalReference}</Field>
            <Field label="GNSS / CORS control"><StatusBadge raw={crs.gnssCorsControl} /></Field>
          </dl>
          {crs.notes.map((n) => <p className="note" key={n}>{n}. No latitude or longitude is shown anywhere in this app.</p>)}
        </Panel>
      </div>

      <Panel title="Point cloud">
        {pointcloud.status === 'error' ? (
          <ErrorState title="Point-cloud inventory unavailable" detail={pointcloud.error} />
        ) : (
          <>
            <div className="badge-row">
              <StatusBadge raw={pointcloud.data.inventoryStatus} />
              <span className="muted">{pointcloud.data.filesDetected} detected · {pointcloud.data.filesProcessed} processed · {pointcloud.data.filesLfsPointer} Git-LFS pointer stub(s)</span>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>File</th><th>Format</th><th className="num">On disk</th><th className="num">Expected</th><th className="num">Points</th><th>Bounds / Z range</th><th>CRS</th><th>Parse status</th></tr></thead>
                <tbody>
                  {pointcloud.data.files.map((f) => (
                    <tr key={f.path} title={f.note ?? undefined}>
                      <td className="mono">{f.name}</td>
                      <td className="mono">{f.format.toUpperCase()}</td>
                      <td className="num">{fmtBytes(f.sizeBytes)}</td>
                      <td className="num">{fmtBytes(f.expectedSizeBytes)}</td>
                      <td className="num">{f.pointCount === null ? <span className="muted">not read</span> : fmtInt(f.pointCount)}</td>
                      <td>{f.bounds === null ? <span className="muted">not computed</span> : `z ${fmt(f.bounds[0][2])} → ${fmt(f.bounds[1][2])}`}</td>
                      <td>{f.crsKnown ? 'Known' : <StatusBadge tone="unverified" label="Unknown" title={f.crsStatement} />}</td>
                      <td><StatusBadge raw={f.parseStatus} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="metric-cards">
              {pointcloud.data.metrics.map((m) => (
                <div className="metric-card" key={m.key}>
                  <header><strong>{m.label}</strong><StatusBadge raw={m.status} /></header>
                  {m.computed ? (
                    <dl className="fields fields--dense">{m.values.map((v) => <Field key={v.label} label={v.label}>{v.value}</Field>)}</dl>
                  ) : (
                    <p className="note">Not computed{m.reason ? `: ${m.reason}` : ''}. <span className="mono">{m.status}</span></p>
                  )}
                  {m.method && <p className="note">Method: {m.method}</p>}
                </div>
              ))}
            </div>
            <p className="note">
              {pointcloud.data.acquisitionStatement} Registration file found: {pointcloud.data.registrationFilesFound === null ? 'not reported' : pointcloud.data.registrationFilesFound ? 'yes' : 'no'}.
              No point count, RMSE, p95, overlap or coverage figure is shown unless the pipeline computed it.
            </p>
          </>
        )}
      </Panel>

      <div className="grid-2">
        <Panel title="Underground / volumetric cadastre">
          {cadastral.underground.entityCount === 0 ? (
            <UnavailableState title="Underground data unavailable">
              {cadastral.underground.notes[0] ?? 'No subsurface source was supplied.'}
            </UnavailableState>
          ) : (
            <p>{cadastral.underground.entityCount} volumetric entities in the model.</p>
          )}
          <span className="eyebrow">Entity types the model schema supports</span>
          <div className="badge-row">
            {cadastral.underground.supportedTypes.map((t) => <StatusBadge key={t} tone="neutral" label={humanise(t)} />)}
          </div>
          <p className="note">The storey “-1 fundering” is an IFC storey level with no IfcSpaces; it is not an underground property volume.</p>
        </Panel>
        <Panel title="Cadastral model">
          <dl className="fields">
            <Field label="Model version" mono>{cadastral.modelVersion}</Field>
            <Field label="Hierarchy" stack>{cadastral.hierarchyOrder.join(' › ')}</Field>
            <Field label="Parcel"><StatusBadge raw={cadastral.parcel.status} /></Field>
            <Field label="Parcel id">{cadastral.parcel.id ?? 'null'}</Field>
            <Field label="BAG id">{cadastral.bagId ?? 'null'}</Field>
            <Field label="Ownership"><StatusBadge raw={cadastral.parcel.ownershipStatus} /></Field>
            <Field label="Terrain"><StatusBadge raw={cadastral.terrainStatus} /></Field>
            <Field label="Spaces reassigned by geometry">{cadastral.grouping.reassignedByGeometry}</Field>
            <Field label="Ambiguous space names" mono>{metrics.ambiguousSpaceNames.join(', ') || 'none'}</Field>
          </dl>
        </Panel>
      </div>
    </Page>
  )
}
