import type { Provenance, RawProvenance } from '../types'
import { getJson } from './client'
import { fileName, toCoordinateReference } from './shared'

/** GET /api/provenance */
export async function fetchProvenance(): Promise<Provenance> {
  const raw = await getJson<RawProvenance>('provenance')
  const methods: Provenance['methods'] = []
  let mlModelTrained: boolean | null = null
  for (const [stage, value] of Object.entries(raw.methods)) {
    if (typeof value === 'boolean') {
      if (stage === 'ml_model_trained') mlModelTrained = value
      continue
    }
    methods.push({
      stage,
      methodType: value.method_type ?? null,
      modelStatus: value.model_status ?? null,
      official: value.official ?? null,
    })
  }
  return {
    runTimestampUtc: raw.run_timestamp_utc,
    timestampNote: raw.note,
    environment: raw.environment,
    ifc: {
      path: raw.inputs.ifc.path,
      fileName: fileName(raw.inputs.ifc.path),
      sha256: raw.inputs.ifc.sha256,
      schema: raw.inputs.ifc.schema,
      lengthScaleToMetre: raw.inputs.ifc.length_unit.length_scale_to_metre,
      sourceMode: raw.inputs.ifc.source_mode,
    },
    pointcloudInputs: raw.inputs.pointclouds.map((p) => ({ name: p.name, sizeBytes: p.size_bytes, parseStatus: p.parse_status })),
    methods,
    mlModelTrained,
    crs: toCoordinateReference(raw.coordinate_reference),
    legalNotice: raw.legal_notice,
  }
}
