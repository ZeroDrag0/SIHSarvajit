import { useDataset } from '../services/datasetContext'
import { Stat } from './Layout'

/** Headline counts. Every number is read from pipeline_report.json / topology_validation.json. */
export function MetricsStrip() {
  const { metrics, validation } = useDataset()
  return (
    <div className="metrics-strip">
      <Stat value={metrics.storeys} label="Storeys" />
      <Stat value={metrics.propertyUnits} label="Property units" />
      <Stat value={metrics.ifcSpaces} label="IFC spaces" />
      <Stat value={metrics.prototypeUlpins} label="Prototype 3D ULPINs" />
      <Stat value={metrics.nativeGeometries} label="Native geometries" />
      <Stat value={metrics.derivedGeometries} label="Derived geometries" />
      <Stat value={validation.errors.length} label="Validation errors" tone={validation.errors.length > 0 ? 'error' : 'ok'} />
      <Stat value={validation.warnings.length} label="Validation warnings" tone={validation.warnings.length > 0 ? 'warning' : 'ok'} />
    </div>
  )
}
