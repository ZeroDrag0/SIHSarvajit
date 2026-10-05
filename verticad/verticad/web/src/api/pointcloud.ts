import type { PointCloudMetric, PointCloudStatus, RawPointCloud, RawPointCloudMetricFile } from '../types'
import { getJson } from './client'

const STATUS_KEYS = new Set(['file', 'name', 'status'])

function perFile(files: RawPointCloudMetricFile[]): PointCloudMetric['perFile'] {
  return files.map((f) => ({ file: f.file ?? f.name ?? 'unnamed', status: f.status ?? 'unknown' }))
}

/** Numeric results only. If the pipeline did not compute a number, nothing is emitted. */
function numericValues(files: RawPointCloudMetricFile[]): PointCloudMetric['values'] {
  const values: PointCloudMetric['values'] = []
  for (const file of files) {
    for (const [key, value] of Object.entries(file)) {
      if (STATUS_KEYS.has(key) || typeof value !== 'number') continue
      values.push({ label: `${file.file ?? file.name ?? ''} · ${key.replace(/_/g, ' ')}`.trim(), value: String(value) })
    }
  }
  return values
}

function isComputed(status: string, values: PointCloudMetric['values']): boolean {
  return values.length > 0 && !/^(no_|not_)/.test(status)
}

/** GET /api/pointcloud */
export async function fetchPointCloud(): Promise<PointCloudStatus> {
  const raw = await getJson<RawPointCloud>('pointcloud')
  const coverageValues = numericValues(raw.coverage.files)
  const alignmentValues = numericValues(raw.alignment.files)
  const comparisonValues = numericValues(raw.ifc_comparison.files)
  const files = raw.inventory.files.map((f) => ({
    name: f.name,
    path: f.path,
    format: f.format,
    sizeBytes: f.size_bytes,
    expectedSizeBytes: f.lfs_pointer?.expected_size_bytes ?? null,
    parseStatus: f.parse_status,
    isLfsPointer: Boolean(f.lfs_pointer),
    pointCount: f.point_count,
    bounds: f.bounds,
    crsKnown: f.crs_known,
    crsStatement: f.crs_statement,
    note: f.note ?? null,
  }))
  return {
    inventoryStatus: raw.inventory.status,
    filesDetected: raw.inventory.total_detected,
    filesProcessed: raw.inventory.files_processed,
    filesLfsPointer: raw.inventory.files_git_lfs_pointer,
    formatSummary: raw.inventory.format_summary,
    acquisitionStatement: raw.inventory.acquisition_statement,
    files,
    registrationFilesFound: raw.ifc_comparison.registration_files_found ?? null,
    hasPointData: files.some((f) => f.pointCount !== null),
    metrics: [
      {
        key: 'coverage',
        label: 'Coverage',
        status: raw.coverage.status,
        computed: isComputed(raw.coverage.status, coverageValues),
        method: null,
        reason: null,
        perFile: perFile(raw.coverage.files),
        values: coverageValues,
      },
      {
        key: 'alignment',
        label: 'Registration / overlap',
        status: raw.alignment.status,
        computed: isComputed(raw.alignment.status, alignmentValues),
        method: raw.alignment.method ?? null,
        reason: null,
        perFile: perFile(raw.alignment.files),
        values: alignmentValues,
      },
      {
        key: 'ifc_comparison',
        label: 'IFC comparison (RMSE / p95)',
        status: raw.ifc_comparison.status,
        computed: isComputed(raw.ifc_comparison.status, comparisonValues),
        method: raw.ifc_comparison.method ?? null,
        reason: raw.ifc_comparison.reason ?? null,
        perFile: perFile(raw.ifc_comparison.files),
        values: comparisonValues,
      },
    ],
  }
}
