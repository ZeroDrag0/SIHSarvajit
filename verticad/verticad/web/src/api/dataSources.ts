import type { CadastralStatus, DataSource, Metrics, PointCloudStatus, Provenance, Resource } from '../types'
import { fmtBytes } from '../utils/format'
import { statusDisplay } from '../utils/status'

/**
 * GET /api/data-sources
 *
 * The pipeline has no single "data sources" document, so this view is composed
 * from the status fields it does report. Every row names the field it reads
 * (`basis`). Sources the pipeline has no field for are marked "Not reported".
 */
export function composeDataSources(
  metrics: Metrics,
  cadastral: CadastralStatus,
  provenance: Resource<Provenance>,
  pointcloud: Resource<PointCloudStatus>,
): DataSource[] {
  const prov = provenance.status === 'ready' ? provenance.data : null
  const pc = pointcloud.status === 'ready' ? pointcloud.data : null

  const row = (
    key: string,
    name: string,
    rawStatus: string | null,
    source: string,
    role: string,
    processingState: string,
    basis: string,
    override?: Pick<DataSource, 'tone' | 'statusLabel'>,
  ): DataSource => {
    const display = override ?? { tone: statusDisplay(rawStatus).tone, statusLabel: statusDisplay(rawStatus).label }
    return { key, name, rawStatus, source, role, processingState, basis, ...display }
  }

  const expected = pc?.files.reduce((sum, f) => sum + (f.expectedSizeBytes ?? 0), 0) ?? 0
  const pcOverride =
    metrics.pointcloud.processed > 0
      ? { tone: 'available' as const, statusLabel: 'Available' }
      : metrics.pointcloud.detected > 0
        ? { tone: 'unavailable' as const, statusLabel: 'Detected · not processed' }
        : { tone: 'unavailable' as const, statusLabel: 'Unavailable' }

  return [
    row(
      'ifc',
      'IFC design model',
      metrics.sourceMode,
      prov ? `${prov.ifc.fileName} · ${prov.ifc.schema}` : 'Design IFC (file details unavailable: provenance not loaded)',
      'Authoritative source for building structure, storeys and IfcSpace geometry',
      `${metrics.ifcSpaces} IfcSpaces read · ${metrics.nativeGeometries} native Body · ${metrics.derivedGeometries} derived FootPrint + Box`,
      'pipeline_report.source_mode, space_geometry',
    ),
    row(
      'pointcloud',
      'Point cloud',
      metrics.pointcloud.inventory,
      pc
        ? `${pc.filesDetected} file(s) detected${expected ? ` · ${fmtBytes(expected)} expected` : ''}`
        : `${metrics.pointcloud.detected} file(s) detected`,
      'Independent as-built check of IFC-derived geometry',
      `${metrics.pointcloud.processed} of ${metrics.pointcloud.detected} processed · ${metrics.pointcloud.lfsPointers} Git-LFS pointer stub(s) · comparison ${statusDisplay(metrics.pointcloud.comparison).label.toLowerCase()}`,
      'pipeline_report.pointcloud_status',
      pcOverride,
    ),
    row(
      'cadastral',
      'Cadastral parcel layer',
      metrics.cadastralStatus,
      'None supplied',
      'Parcel boundary and parcel ↔ building link',
      `Parcel id ${cadastral.parcel.id ?? 'null'} · ${cadastral.parcel.derivation}`,
      'pipeline_report.cadastral_status, model.parcels',
    ),
    row(
      'terrain',
      'DEM / DSM (terrain)',
      metrics.terrainStatus,
      'None supplied',
      'Ground level, roof elevation, height above terrain',
      'Terrain-relative heights not derived',
      'pipeline_report.terrain_status',
    ),
    row(
      'gnss',
      'GNSS / CORS control',
      metrics.gnssCorsControl,
      'None supplied',
      'Georeferencing to a verified CRS',
      `Coordinates remain ${metrics.coordinateStatus}`,
      'pipeline_report.crs.gnss_cors_control',
    ),
    row(
      'drone',
      'Drone imagery',
      metrics.droneImagery,
      'None supplied',
      'Roof / façade extraction and visual context',
      'Not part of this run',
      'pipeline_report.drone_imagery',
    ),
    row(
      'underground',
      'Underground / subsurface',
      metrics.undergroundStatus,
      'None supplied',
      'Basement, foundation, utility and tunnel volumes',
      `${cadastral.underground.entityCount} volumetric entities in model`,
      'pipeline_report.underground_status',
    ),
    row(
      'floorplans',
      'Separate floor plans',
      null,
      'Not a separate input',
      'Room layout',
      'Plan geometry is taken from IFC FootPrint curves; the pipeline reports no standalone floor-plan source',
      'no pipeline field',
      { tone: 'not-used', statusLabel: 'Not reported' },
    ),
  ]
}
