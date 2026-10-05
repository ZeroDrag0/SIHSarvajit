import type { Ring, Vec3 } from '../types'

export interface Bounds2D { minX: number; minY: number; maxX: number; maxY: number }

export function ringsBounds(rings: Ring[]): Bounds2D | null {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const ring of rings) {
    for (const [x, y] of ring) {
      if (x < minX) minX = x
      if (y < minY) minY = y
      if (x > maxX) maxX = x
      if (y > maxY) maxY = y
    }
  }
  return Number.isFinite(minX) ? { minX, minY, maxX, maxY } : null
}

/** Area-weighted centroid of a simple ring (falls back to the vertex mean for degenerate rings). */
export function ringCentroid(ring: Ring): [number, number] {
  let area = 0, cx = 0, cy = 0
  for (let i = 0; i < ring.length; i += 1) {
    const [x0, y0] = ring[i]
    const [x1, y1] = ring[(i + 1) % ring.length]
    const cross = x0 * y1 - x1 * y0
    area += cross
    cx += (x0 + x1) * cross
    cy += (y0 + y1) * cross
  }
  if (Math.abs(area) < 1e-9) {
    const n = ring.length || 1
    return [ring.reduce((s, p) => s + p[0], 0) / n, ring.reduce((s, p) => s + p[1], 0) / n]
  }
  return [cx / (3 * area), cy / (3 * area)]
}

export function ringArea(ring: Ring): number {
  let area = 0
  for (let i = 0; i < ring.length; i += 1) {
    const [x0, y0] = ring[i]
    const [x1, y1] = ring[(i + 1) % ring.length]
    area += x0 * y1 - x1 * y0
  }
  return Math.abs(area) / 2
}

/** IFC local (x, y, z-up) → three.js world (x, y-up, z), re-centred on `origin`. */
export function ifcToWorld(x: number, y: number, z: number, origin: [number, number]): Vec3 {
  return [x - origin[0], z, -(y - origin[1])]
}
