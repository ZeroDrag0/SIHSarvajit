import { Page, Panel, Stat } from '../components/Layout'
import { StatusBadge } from '../components/StatusBadge'
import { useDataset } from '../services/datasetContext'
import { useSelection } from '../services/selectionContext'
import { fmt } from '../utils/format'
import { humanise } from '../utils/status'

export function ValidationPage() {
  const { validation, units } = useDataset()
  const selection = useSelection()
  const counts = validation.statusCounts
  const verdictTone = !validation.valid || validation.errors.length > 0 ? 'error' : validation.warnings.length > 0 ? 'warning' : 'ok'
  const verdict = !validation.valid
    ? 'Validation failed'
    : validation.warnings.length > 0
      ? `Validation completed with ${validation.warnings.length} warning${validation.warnings.length === 1 ? '' : 's'}`
      : 'Validation completed with no warnings'

  return (
    <Page eyebrow="Topology validation" title="Validation results" lede={validation.validityDefinition.replace(/^true/, '“Valid” is true')}>
      <div className={`verdict verdict--${verdictTone}`}>
        <div>
          <span className="eyebrow">Result</span>
          <h2>{verdict}</h2>
        </div>
        <div className="verdict-stats">
          <Stat value={validation.valid ? 'VALID' : 'INVALID'} label="Required checks" tone={validation.valid ? 'ok' : 'error'} />
          <Stat value={validation.warnings.length} label="Warnings" tone={validation.warnings.length ? 'warning' : 'ok'} />
          <Stat value={validation.errors.length} label="Errors" tone={validation.errors.length ? 'error' : 'ok'} />
        </div>
      </div>

      <div className="grid-2">
        <Panel title="Warnings">
          {validation.warnings.length === 0 ? <p className="note">The pipeline reported no warnings.</p> : (
            <ul className="warning-list warning-list--lg">{validation.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          )}
          {validation.spacesNotFullyCorroborated.length > 0 && (
            <p className="note">Spaces not fully corroborated by IfcRelSpaceBoundary surfaces: <span className="mono">{validation.spacesNotFullyCorroborated.join(', ')}</span></p>
          )}
        </Panel>
        <Panel title="Errors">
          {validation.errors.length === 0 ? <p className="note">The pipeline reported no errors.</p> : (
            <ul className="warning-list warning-list--error">{validation.errors.map((e) => <li key={e}>{e}</li>)}</ul>
          )}
          <div className="count-row">
            {Object.entries(counts).map(([status, n]) => n === 0
              ? <StatusBadge key={status} tone="neutral" label={`0 ${humanise(status).toLowerCase()}`} />
              : <StatusBadge key={status} raw={status} label={`${n} ${humanise(status).toLowerCase()}`} />)}
          </div>
        </Panel>
      </div>

      <Panel title={`Checks · ${validation.checks.length}`}>
        <div className="table-wrap">
          <table className="table table--checks">
            <thead><tr><th>Check</th><th>Status</th><th>Scope</th><th>Reported detail</th></tr></thead>
            <tbody>
              {validation.checks.map((check) => (
                <tr key={check.key}>
                  <td><strong>{check.title}</strong><small className="mono">{check.key}</small></td>
                  <td><StatusBadge raw={check.status} /></td>
                  <td>{check.required ? 'Required' : 'Advisory'}</td>
                  <td>
                    {check.remarks.map((r) => <p key={r}>{r}</p>)}
                    {check.facts.length > 0 && (
                      <p className="facts">{check.facts.map((f) => <span key={f.label}>{f.label}: <b>{f.value}</b></span>)}</p>
                    )}
                    {check.remarks.length === 0 && check.facts.length === 0 && <span className="muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid-2">
        <Panel title="Storey coverage by unit footprints">
          {Object.keys(validation.storeyCoverageRatio).length === 0 ? <p className="note">Not reported.</p> : (
            <ul className="bars">
              {Object.entries(validation.storeyCoverageRatio).map(([storeyName, ratio]) => (
                <li key={storeyName}>
                  <span>{storeyName}</span>
                  <div className="bar"><i style={{ width: `${Math.min(ratio, 1) * 100}%` }} /></div>
                  <b>{(ratio * 100).toFixed(1)}%</b>
                </li>
              ))}
            </ul>
          )}
          <p className="note">Wall thickness separates net room volumes, so coverage below 100% is expected.</p>
        </Panel>
        <Panel title="Per-unit state">
          <ul className="unit-states">
            {units.map((u) => (
              <li key={u.id}>
                <button type="button" className="link mono" onClick={() => selection.selectUnit(u.id)}>{u.id}</button>
                <StatusBadge raw={u.validationState} />
                {validation.fallbackGeometryUnits.includes(u.id) && <StatusBadge tone="derived" label="Fallback geometry" />}
                {u.warnings.length > 0 && <StatusBadge tone="warning" label="Grouping note" title={u.warnings.join('\n')} />}
              </li>
            ))}
          </ul>
          <p className="note">Total unit volume {fmt(validation.totalUnitVolumeM3, 1)} m³.</p>
        </Panel>
      </div>

      {validation.stackedPairs.length > 0 && (
        <Panel title={`Vertically stacked unit pairs · ${validation.stackedPairs.length}`}>
          <details className="disclosure">
            <summary>Footprints overlap in plan while Z ranges are disjoint (expected stacking)</summary>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Lower</th><th>Upper</th><th className="num">Plan overlap m²</th><th className="num">Z overlap m (negative = gap)</th></tr></thead>
                <tbody>
                  {validation.stackedPairs.map((p) => (
                    <tr key={p.units.join('-')}>
                      <td className="mono">{p.units[0]}</td>
                      <td className="mono">{p.units[1]}</td>
                      <td className="num">{fmt(p.footprintOverlapM2)}</td>
                      <td className="num">{fmt(p.zOverlapM)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Panel>
      )}
    </Page>
  )
}
