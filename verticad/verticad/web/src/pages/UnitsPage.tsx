import { GeometrySourceBadge } from '../components/GeometrySource'
import { Inspector } from '../components/Inspector'
import { Page } from '../components/Layout'
import { StatusBadge } from '../components/StatusBadge'
import { useDataset } from '../services/datasetContext'
import { navigate } from '../services/router'
import { useSelection } from '../services/selectionContext'
import { fmt, fmtRange } from '../utils/format'

export function UnitsPage() {
  const { units, cadastral, metrics } = useDataset()
  const selection = useSelection()
  return (
    <Page
      eyebrow="Property unit explorer"
      title="Inferred property units"
      lede={<>{units.length} units inferred from {cadastral.grouping.spacesInUnits} IfcSpaces. {cadastral.grouping.commonOrServiceSpaces} common or service spaces belong to no unit. IFC project name declares {metrics.declaredCountCheck.declared}; derived count {metrics.declaredCountCheck.agrees ? 'agrees' : 'differs'}.</>}
    >
      <div className="split split--units">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Unit</th>
                <th>Prototype 3D ULPIN</th>
                <th>Storey</th>
                <th className="num">Spaces</th>
                <th className="num">Volume m³</th>
                <th className="num">Footprint m²</th>
                <th className="num">Height m</th>
                <th>Z extent</th>
                <th>Geometry</th>
                <th className="num">Conf.</th>
                <th>Validation</th>
              </tr>
            </thead>
            <tbody>
              {units.map((u) => (
                <tr
                  key={u.id}
                  className={u.id === selection.unitId ? 'is-selected' : ''}
                  tabIndex={0}
                  onClick={() => selection.selectUnit(u.id)}
                  onKeyDown={(e) => { if (e.key === 'Enter') selection.selectUnit(u.id) }}
                >
                  <td className="nowrap"><strong className="mono">{u.id}</strong></td>
                  <td className="mono nowrap">{u.prototypeUlpin}</td>
                  <td className="nowrap">{u.storeyNames.join(', ')}</td>
                  <td className="num">{u.spaces.length}</td>
                  <td className="num">{fmt(u.geometry.volumeM3, 1)}</td>
                  <td className="num">{fmt(u.geometry.footprintAreaM2, 1)}</td>
                  <td className="num">{fmt(u.geometry.heightM)}</td>
                  <td className="nowrap">{fmtRange(u.geometry.zMin, u.geometry.zMax)}</td>
                  <td><GeometrySourceBadge kind={u.geometry.sourceKind} compact /></td>
                  <td className="num">{u.geometry.confidence.toFixed(2)}</td>
                  <td className="nowrap">
                    <StatusBadge raw={u.validationState} />
                    {u.warnings.length > 0 && <StatusBadge tone="warning" label={`${u.warnings.length} note`} title={u.warnings.join('\n')} />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note">
            Geometry “Derived” = IFC FootPrint + Box extrusion, not a native IFC Body. Confidence is a rule-based heuristic score, not a statistical probability. Volumes are net internal volumes of the constituent IfcSpaces.
          </p>
        </div>
        <aside className="split-aside">
          <Inspector
            footer={selection.unitId ? (
              <div className="inspector-footer">
                <button type="button" className="btn btn--primary" onClick={() => navigate('viewer')}>View in 3D</button>
              </div>
            ) : null}
          />
        </aside>
      </div>
    </Page>
  )
}
