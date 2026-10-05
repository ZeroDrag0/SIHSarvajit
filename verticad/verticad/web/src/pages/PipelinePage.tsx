import type { ReactNode } from 'react'
import { Page } from '../components/Layout'
import { StatusBadge } from '../components/StatusBadge'
import { useDataset } from '../services/datasetContext'
import type { StatusTone } from '../types'
import { fmt } from '../utils/format'
import { humanise, statusDisplay } from '../utils/status'

interface Stage {
  name: string
  tone: StatusTone
  status: string
  input: ReactNode
  output: ReactNode
  basis: ReactNode
}

export function PipelinePage() {
  const { metrics, validation, provenance, cadastral, ulpins, units, building } = useDataset()
  const prov = provenance.status === 'ready' ? provenance.data : null
  const method = (stage: string) => {
    const m = prov?.methods.find((x) => x.stage === stage)
    return m?.methodType ? humanise(m.methodType) : 'method not reported'
  }
  const classes = Object.entries(metrics.classCounts).map(([k, n]) => `${n} ${humanise(k).toLowerCase()}`).join(', ')
  const confidences = units.map((u) => u.groupingConfidence)
  const pcComputed = metrics.pointcloud.processed > 0
  const checkCounts = Object.entries(metrics.checkStatusCounts).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${humanise(k).toLowerCase()}`).join(' · ')

  const stages: Stage[] = [
    {
      name: 'Source data',
      tone: 'available',
      status: 'IFC available',
      input: prov ? `${prov.ifc.fileName} (${prov.ifc.schema})` : 'Design IFC',
      output: `${metrics.pointcloud.detected} point-cloud file(s) detected, ${metrics.pointcloud.processed} readable`,
      basis: 'Read directly from the source file; no cadastral, terrain, GNSS or imagery inputs',
    },
    {
      name: 'IFC structure',
      tone: 'available',
      status: 'Extracted',
      input: 'IFC spatial structure',
      output: `${metrics.buildings} building · ${metrics.storeys} storeys · ${metrics.ifcSpaces} IfcSpaces`,
      basis: `Building envelope ${statusDisplay(building.status).label.toLowerCase()} · ${method('building_extraction')}`,
    },
    {
      name: 'Space classification',
      tone: 'derived',
      status: 'Derived',
      input: `${metrics.ifcSpaces} IfcSpaces (names, long names, storey)`,
      output: `${metrics.classifiedSpaces} classified: ${classes}`,
      basis: `${method('space_classification')} · no trained model`,
    },
    {
      name: 'Property unit inference',
      tone: 'inferred',
      status: 'Inferred',
      input: `${cadastral.grouping.spacesInUnits} private-like spaces`,
      output: `${metrics.propertyUnits} property units · ${cadastral.grouping.commonOrServiceSpaces} common/service spaces left outside`,
      basis: `${method('vertical_property_delineation')} · grouping confidence ${Math.min(...confidences).toFixed(2)}–${Math.max(...confidences).toFixed(2)} · IFC project name declares ${metrics.declaredCountCheck.declared} (${metrics.declaredCountCheck.agrees ? 'agrees' : 'differs'})`,
    },
    {
      name: '3D geometry',
      tone: 'derived',
      status: 'Derived',
      input: 'IfcSpace Body, FootPrint and Box representations',
      output: `${metrics.nativeGeometries} native IFC Body · ${metrics.derivedGeometries} derived FootPrint + Box · ${metrics.unitsWithGeometry} unit volumes by boolean union`,
      basis: `Mean space confidence ${metrics.meanSpaceConfidence.toFixed(3)} · ${Object.entries(metrics.boundaryCorroboration).map(([k, n]) => `${n} ${humanise(k).toLowerCase()}`).join(', ')} against ${fmt(metrics.spaceBoundariesInModel, 0)} space boundaries`,
    },
    {
      name: 'Point-cloud validation',
      tone: pcComputed ? 'validated' : 'not-used',
      status: pcComputed ? 'Computed' : 'Not run',
      input: `${metrics.pointcloud.detected} file(s), ${metrics.pointcloud.lfsPointers} Git-LFS pointer stub(s)`,
      output: pcComputed ? 'See Data → Point cloud' : 'No alignment, RMSE or coverage computed',
      basis: `Alignment: ${statusDisplay(metrics.pointcloud.alignment).label.toLowerCase()} · comparison: ${statusDisplay(metrics.pointcloud.comparison).label.toLowerCase()}`,
    },
    {
      name: 'Topology validation',
      tone: !validation.valid ? 'error' : validation.warnings.length ? 'warning' : 'validated',
      status: !validation.valid ? 'Failed' : `Valid · ${validation.warnings.length} warning(s)`,
      input: `${metrics.propertyUnits} unit volumes`,
      output: checkCounts,
      basis: `${method('topology_validation')} · parcel and terrain checks not applicable (no data)`,
    },
    {
      name: 'Prototype 3D ULPIN',
      tone: 'prototype',
      status: 'Prototype',
      input: 'Unit identity + geometry version',
      output: `${metrics.prototypeUlpins} identifiers · scheme ${ulpins.scheme}`,
      basis: `${ulpins.records[0]?.derivationMethod ?? method('ulpin')} · not issued by any authority`,
    },
    {
      name: '3D cadastral model',
      tone: 'prototype',
      status: 'Prototype',
      input: cadastral.hierarchyOrder.join(' › '),
      output: `${cadastral.modelVersion} · parcel ${cadastral.parcel.id ?? 'null'} · ${cadastral.underground.entityCount} underground entities`,
      basis: `Parcel ${statusDisplay(cadastral.parcel.status).label.toLowerCase()} · coordinates ${metrics.coordinateStatus}`,
    },
  ]

  return (
    <Page eyebrow="System lineage" title="From IFC source to 3D cadastral model" lede="Nine stages, each with the status the pipeline reported for this run.">
      <ol className="pipeline">
        {stages.map((stage, i) => (
          <li key={stage.name} className={`pipeline-stage pipeline-stage--${stage.tone}`}>
            <span className="pipeline-index mono">{String(i + 1).padStart(2, '0')}</span>
            <div className="pipeline-body">
              <header>
                <h2>{stage.name}</h2>
                <StatusBadge tone={stage.tone} label={stage.status} />
              </header>
              <dl>
                <div><dt>Input</dt><dd>{stage.input}</dd></div>
                <div><dt>Output</dt><dd>{stage.output}</dd></div>
                <div><dt>Confidence / provenance</dt><dd>{stage.basis}</dd></div>
              </dl>
            </div>
          </li>
        ))}
      </ol>
    </Page>
  )
}
