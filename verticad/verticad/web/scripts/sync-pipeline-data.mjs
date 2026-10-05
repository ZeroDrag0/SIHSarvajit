#!/usr/bin/env node
/**
 * Copies the pipeline's processed outputs into public/data/schependomlaan.
 * It copies files byte-for-byte. It does not transform, filter or generate data.
 *
 *   npm run sync:data                      # default: ../pipeline/Schependomlaan/processed
 *   npm run sync:data -- <path-to-processed>
 *   PIPELINE_PROCESSED_DIR=<path> npm run sync:data
 */
import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const source = resolve(webRoot, process.argv[2] ?? process.env.PIPELINE_PROCESSED_DIR ?? '../pipeline/Schependomlaan/processed')
const target = resolve(webRoot, 'public/data/schependomlaan')

// Must match the `file` entries in src/api/client.ts.
const FILES = [
  'building.json',
  'floors.json',
  'property_units.json',
  'ulpins.json',
  'topology_validation.json',
  'provenance.json',
  'pipeline_report.json',
  'pointcloud_inventory.json',
  '3d_cadastral_model.json',
  'space_classification.json',
  'geometry/space_geometry.json',
  'geometry/property_units.glb',
]

if (!existsSync(source)) {
  console.error(`Pipeline output folder not found: ${source}`)
  process.exit(1)
}

let missing = 0
for (const file of FILES) {
  const from = resolve(source, file)
  const to = resolve(target, file)
  if (!existsSync(from)) {
    console.error(`  missing  ${file}`)
    missing += 1
    continue
  }
  mkdirSync(dirname(to), { recursive: true })
  copyFileSync(from, to)
  console.log(`  copied   ${file} (${statSync(from).size} bytes)`)
}
if (missing > 0) {
  console.error(`${missing} file(s) missing. The frontend will show an error state for them.`)
  process.exit(1)
}
console.log(`Synced ${FILES.length} files from ${source}`)
