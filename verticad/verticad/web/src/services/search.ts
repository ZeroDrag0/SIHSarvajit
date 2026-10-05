import type { CadastreDataset } from '../types'

export type SearchKind = 'ulpin' | 'unit' | 'space' | 'storey' | 'building'

export interface SearchEntry {
  kind: SearchKind
  key: string
  title: string
  subtitle: string
  haystack: string
  storeyId?: string
  unitId?: string
  spaceId?: string
}

export const KIND_LABEL: Record<SearchKind, string> = {
  ulpin: 'Prototype 3D ULPIN',
  unit: 'Property unit',
  space: 'IFC space',
  storey: 'Storey',
  building: 'Building',
}

const norm = (text: string) => text.toLowerCase().replace(/[\s-]+/g, '')

export function buildSearchIndex(dataset: CadastreDataset): SearchEntry[] {
  const entries: SearchEntry[] = []
  const { building, storeys, units, ulpins, spaces } = dataset

  entries.push({
    kind: 'building',
    key: `building:${building.id}`,
    title: building.id,
    subtitle: `${building.name} · ${building.storeyCount} storeys`,
    haystack: norm(`${building.id} ${building.name}`),
  })
  for (const s of storeys) {
    entries.push({
      kind: 'storey',
      key: `storey:${s.id}`,
      title: s.name,
      subtitle: `${s.id} · ${s.unitIds.length} unit(s)`,
      haystack: norm(`${s.name} ${s.id} floor storey ${s.orderIndex}`),
      storeyId: s.id,
    })
  }
  for (const u of units) {
    entries.push({
      kind: 'unit',
      key: `unit:${u.id}`,
      title: u.id,
      subtitle: `${u.label} · ${u.storeyNames.join(', ')}`,
      haystack: norm(`${u.id} ${u.label}`),
      unitId: u.id,
    })
  }
  for (const r of ulpins.records) {
    entries.push({
      kind: 'ulpin',
      key: `ulpin:${r.code}`,
      title: r.code,
      subtitle: `${r.unitId} · ${r.geometryVersion}`,
      haystack: norm(`${r.code} ${r.geometryVersion}`),
      unitId: r.unitId,
    })
  }
  for (const s of spaces) {
    entries.push({
      kind: 'space',
      key: `space:${s.globalId}`,
      title: `${s.name}${s.longName ? ` · ${s.longName}` : ''}`,
      subtitle: `${s.globalId} · ${s.unitId ?? 'common / service'} · ${s.storeyName}`,
      haystack: norm(`${s.globalId} ${s.name} ${s.longName ?? ''}`),
      storeyId: s.storeyId,
      unitId: s.unitId ?? undefined,
      spaceId: s.globalId,
    })
  }
  return entries
}

const ORDER: SearchKind[] = ['unit', 'ulpin', 'storey', 'building', 'space']

export function runSearch(index: SearchEntry[], query: string, limit = 12): SearchEntry[] {
  const q = norm(query)
  if (q.length < 1) return []
  const scored: Array<{ entry: SearchEntry; score: number }> = []
  for (const entry of index) {
    const at = entry.haystack.indexOf(q)
    if (at < 0) continue
    scored.push({ entry, score: (at === 0 ? 0 : 10) + ORDER.indexOf(entry.kind) })
  }
  return scored.sort((a, b) => a.score - b.score).slice(0, limit).map((s) => s.entry)
}
