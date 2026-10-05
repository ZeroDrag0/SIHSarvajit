import { useEffect, useMemo, useState } from 'react'
import { Grid, Html, Line, useGLTF } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'
import * as THREE from 'three'
import { endpointUrl } from '../api'
import type { Building, IfcSpaceGeometry, PropertyUnit, Ring, Storey, Vec3 } from '../types'
import { ifcToWorld } from '../utils/geometry'
import { storeyColorMap, type ScenePalette } from './palette'
import type { ViewerSettings } from './settings'

const UNITS_GLB_URL = endpointUrl('unitsGlb')
const UP_FIX: [number, number, number] = [-Math.PI / 2, 0, 0]

export interface SceneProps {
  building: Building
  storeys: Storey[]
  units: PropertyUnit[]
  /** Room-level geometry; null until loaded. */
  spaceGeometry: IfcSpaceGeometry[] | null
  spaceOwner: Map<string, string | null>
  settings: ViewerSettings
  showRooms: boolean
  palette: ScenePalette
  selectedStoreyId: string | null
  selectedUnitId: string | null
  selectedSpaceId: string | null
  onSelectUnit: (unitId: string) => void
  onSelectSpace: (spaceId: string) => void
  onSelectStorey: (storeyId: string) => void
}

type Emphasis = 'normal' | 'selected' | 'hovered' | 'faded' | 'hidden'

function isClick(event: ThreeEvent<MouseEvent>): boolean {
  return event.delta <= 4
}

/** Real unit meshes exported by the pipeline (geometry/property_units.glb), keyed by GLB node name. */
function useUnitGeometries(): Map<string, THREE.BufferGeometry> {
  const gltf = useGLTF(UNITS_GLB_URL)
  return useMemo(() => {
    const map = new Map<string, THREE.BufferGeometry>()
    gltf.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        const name = object.name || object.parent?.name
        if (name) map.set(name, object.geometry as THREE.BufferGeometry)
      }
    })
    return map
  }, [gltf])
}

function useEdges(geometry: THREE.BufferGeometry | undefined, threshold = 25): THREE.EdgesGeometry | null {
  const edges = useMemo(() => (geometry ? new THREE.EdgesGeometry(geometry, threshold) : null), [geometry, threshold])
  useEffect(() => () => edges?.dispose(), [edges])
  return edges
}

function extrudeRing(ring: Ring, zMin: number, zMax: number): THREE.ExtrudeGeometry {
  const closed = ring.length > 1 && ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1]
  const points = closed ? ring.slice(0, -1) : ring
  const shape = new THREE.Shape(points.map(([x, y]) => new THREE.Vector2(x, y)))
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: Math.max(zMax - zMin, 0.01), bevelEnabled: false, steps: 1, curveSegments: 1 })
  geometry.translate(0, 0, zMin)
  return geometry
}

function ringToWorld(ring: Ring, z: number, origin: [number, number], yOffset: number): Vec3[] {
  const points = ring.map(([x, y]) => {
    const p = ifcToWorld(x, y, z, origin)
    return [p[0], p[1] + yOffset, p[2]] as Vec3
  })
  if (points.length > 0) points.push(points[0])
  return points
}

function emphasisOpacity(emphasis: Emphasis, base: number): number {
  if (emphasis === 'selected') return Math.max(base, 0.96)
  if (emphasis === 'hovered') return Math.max(base, 0.9)
  if (emphasis === 'faded') return Math.min(base, 0.07)
  return base
}

interface SolidProps {
  geometry: THREE.BufferGeometry
  color: string
  emphasis: Emphasis
  baseOpacity: number
  fill: boolean
  palette: ScenePalette
  onClick?: () => void
  onHover?: (hovering: boolean) => void
}

/** One pickable volume: flat-shaded fill plus crisp feature edges. */
function Solid({ geometry, color, emphasis, baseOpacity, fill, palette, onClick, onHover }: SolidProps) {
  const edges = useEdges(geometry)
  if (emphasis === 'hidden') return null
  const selected = emphasis === 'selected'
  const opacity = emphasisOpacity(emphasis, baseOpacity)
  const interactive = emphasis !== 'faded'
  return (
    <group>
      {fill && (
        <mesh
          geometry={geometry}
          renderOrder={selected ? 2 : 1}
          onClick={interactive && onClick ? (event) => { if (isClick(event)) { event.stopPropagation(); onClick() } } : undefined}
          onPointerOver={interactive && onHover ? (event) => { event.stopPropagation(); onHover(true) } : undefined}
          onPointerOut={interactive && onHover ? () => onHover(false) : undefined}
        >
          <meshStandardMaterial
            color={selected ? palette.selected : color}
            emissive={selected ? palette.selectedEmissive : '#000000'}
            emissiveIntensity={selected ? 0.55 : 0}
            flatShading
            roughness={0.72}
            metalness={0.02}
            transparent={opacity < 0.999}
            opacity={opacity}
            depthWrite={opacity > 0.5}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
      {edges && (
        <lineSegments geometry={edges} renderOrder={3}>
          <lineBasicMaterial
            color={selected ? palette.selected : fill ? palette.edge : color}
            transparent
            opacity={emphasis === 'faded' ? 0.1 : fill ? 0.85 : 0.9}
          />
        </lineSegments>
      )}
    </group>
  )
}

function Room({ space, color, emphasis, baseOpacity, palette, onClick, onHover }: {
  space: IfcSpaceGeometry
  color: string
  emphasis: Emphasis
  baseOpacity: number
  palette: ScenePalette
  onClick: () => void
  onHover: (hovering: boolean) => void
}) {
  const geometry = useMemo(() => extrudeRing(space.footprint, space.zMin, space.zMax), [space])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <Solid geometry={geometry} color={color} emphasis={emphasis} baseOpacity={baseOpacity} fill palette={palette} onClick={onClick} onHover={onHover} />
}

function Envelope({ building, origin, palette }: { building: Building; origin: [number, number]; palette: ScenePalette }) {
  const geometries = useMemo(
    () => building.footprint.map((ring) => extrudeRing(ring, building.zMin, building.zMax)),
    [building],
  )
  useEffect(() => () => geometries.forEach((g) => g.dispose()), [geometries])
  return (
    <group position={[-origin[0], 0, origin[1]]} rotation={UP_FIX}>
      {geometries.map((geometry, i) => (
        <mesh key={i} geometry={geometry} renderOrder={0}>
          <meshBasicMaterial color={palette.envelope} transparent opacity={0.045} depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
      ))}
    </group>
  )
}

function Tooltip({ position, text, tone }: { position: Vec3; text: string; tone: 'unit' | 'room' }) {
  return (
    <Html position={position} center zIndexRange={[20, 0]} style={{ pointerEvents: 'none' }}>
      <div className={`scene-tooltip scene-tooltip--${tone}`}>{text}</div>
    </Html>
  )
}

export function Scene(props: SceneProps) {
  const { building, storeys, units, spaceGeometry, spaceOwner, settings, showRooms, palette } = props
  const { selectedStoreyId, selectedUnitId, selectedSpaceId, onSelectUnit, onSelectSpace, onSelectStorey } = props
  const unitGeometries = useUnitGeometries()
  const [hovered, setHovered] = useState<{ kind: 'unit' | 'room'; id: string } | null>(null)

  const [min, max] = building.boundsM
  const origin = useMemo<[number, number]>(() => [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2], [min, max])
  const storeyColors = useMemo(() => storeyColorMap(storeys, palette), [storeys, palette])
  const storeyIndex = useMemo(() => new Map(storeys.map((s) => [s.id, s.orderIndex])), [storeys])
  const lift = (storeyId: string | undefined) => settings.explode * (storeyId ? (storeyIndex.get(storeyId) ?? 0) : 0)

  useEffect(() => {
    document.body.style.cursor = hovered ? 'pointer' : ''
    return () => { document.body.style.cursor = '' }
  }, [hovered])

  const storeyEmphasis = (storeyIds: string[]): Emphasis | null => {
    if (!selectedStoreyId || storeyIds.includes(selectedStoreyId)) return null
    return settings.isolate ? 'hidden' : 'faded'
  }

  const unitEmphasis = (unit: PropertyUnit): Emphasis => {
    const byStorey = storeyEmphasis(unit.storeyIds)
    if (byStorey) return byStorey
    if (unit.id === selectedUnitId) return 'selected'
    if (hovered?.kind === 'unit' && hovered.id === unit.id) return 'hovered'
    return selectedUnitId ? 'faded' : 'normal'
  }

  const roomEmphasis = (space: IfcSpaceGeometry, owner: string | null): Emphasis => {
    const byStorey = storeyEmphasis([space.storeyId])
    if (byStorey) return byStorey
    if (space.globalId === selectedSpaceId) return 'selected'
    if (hovered?.kind === 'room' && hovered.id === space.globalId) return 'hovered'
    if (selectedSpaceId) return owner && owner === selectedUnitId ? 'normal' : 'faded'
    if (selectedUnitId) return owner === selectedUnitId ? 'normal' : 'faded'
    return 'normal'
  }

  const unitColor = (unit: PropertyUnit): string =>
    settings.colorMode === 'source'
      ? unit.geometry.sourceKind === 'native_body' ? palette.native : palette.derived
      : storeyColors.get(unit.storeyIds[0]) ?? palette.common

  const roomColor = (space: IfcSpaceGeometry, owner: string | null): string => {
    if (settings.colorMode === 'source') return space.isFallback ? palette.derived : palette.native
    return owner ? storeyColors.get(space.storeyId) ?? palette.common : palette.common
  }

  const rooms = spaceGeometry ?? []
  const hoveredUnit = hovered?.kind === 'unit' ? units.find((u) => u.id === hovered.id) : undefined
  const hoveredRoom = hovered?.kind === 'room' ? rooms.find((r) => r.globalId === hovered.id) : undefined
  const span = Math.max(max[0] - min[0], max[1] - min[1])

  return (
    <group>
      <Grid
        position={[0, building.zMin - 0.02, 0]}
        args={[span * 6, span * 6]}
        cellSize={1}
        sectionSize={5}
        cellColor={palette.grid}
        sectionColor={palette.gridSection}
        cellThickness={0.6}
        sectionThickness={1}
        fadeDistance={span * 5}
        fadeStrength={1.6}
        infiniteGrid
      />

      {settings.layers.building && settings.explode === 0 && <Envelope building={building} origin={origin} palette={palette} />}

      {settings.layers.storeys && storeys.map((storey) => {
        const active = storey.id === selectedStoreyId
        const hidden = settings.isolate && selectedStoreyId !== null && !active
        if (hidden) return null
        const dim = selectedStoreyId !== null && !active
        const nominal = storey.zMax === null || storey.spaceCount === 0
        const y = lift(storey.id)
        const label = ifcToWorld(min[0] - 0.5, min[1] - 0.5, storey.zMin, origin)
        const outlineZ = storey.zMin - 0.03
        return (
          <group key={storey.id}>
            {building.footprint.map((ring, i) => (
              <Line
                key={i}
                points={ringToWorld(ring, outlineZ, origin, y)}
                color={active ? palette.outlineActive : palette.outline}
                lineWidth={active ? 2 : 1}
                dashed={nominal}
                dashSize={0.5}
                gapSize={0.35}
                transparent
                opacity={active ? 1 : dim ? 0.16 : 0.55}
              />
            ))}
            {active && storey.zMax !== null && building.footprint.map((ring, i) => (
              <Line key={`top-${i}`} points={ringToWorld(ring, storey.zMax ?? storey.zMin, origin, y)} color={palette.outlineActive} lineWidth={2} transparent opacity={0.9} />
            ))}
            {settings.layers.labels && (
              <Html position={[label[0], label[1] + y, label[2]]} zIndexRange={[10, 0]} style={{ pointerEvents: 'auto' }}>
                <button
                  type="button"
                  className={`storey-tag${active ? ' is-active' : ''}${dim ? ' is-dim' : ''}`}
                  title={storey.name}
                  onClick={() => onSelectStorey(storey.id)}
                >
                  {storey.name.split(' ')[0]}
                </button>
              </Html>
            )}
          </group>
        )
      })}

      {settings.layers.units && units.map((unit) => {
        const geometry = unitGeometries.get(unit.glbNode)
        if (!geometry) return null
        return (
          <group key={unit.id} position={[-origin[0], lift(unit.storeyIds[0]), origin[1]]}>
            <Solid
              geometry={geometry}
              color={unitColor(unit)}
              emphasis={unitEmphasis(unit)}
              baseOpacity={settings.unitOpacity}
              fill={!showRooms}
              palette={palette}
              onClick={() => onSelectUnit(unit.id)}
              onHover={(hovering) => setHovered(hovering ? { kind: 'unit', id: unit.id } : null)}
            />
          </group>
        )
      })}

      {rooms.map((space) => {
        const owner = spaceOwner.get(space.globalId) ?? null
        const visible = owner ? showRooms : settings.layers.common
        if (!visible) return null
        return (
          <group key={space.globalId} position={[-origin[0], lift(space.storeyId), origin[1]]} rotation={UP_FIX}>
            <Room
              space={space}
              color={roomColor(space, owner)}
              emphasis={roomEmphasis(space, owner)}
              baseOpacity={owner ? settings.unitOpacity : Math.min(settings.unitOpacity, 0.55)}
              palette={palette}
              onClick={() => onSelectSpace(space.globalId)}
              onHover={(hovering) => setHovered(hovering ? { kind: 'room', id: space.globalId } : null)}
            />
          </group>
        )
      })}

      {hoveredUnit && (() => {
        const [x, y, z] = hoveredUnit.geometry.centroid
        const p = ifcToWorld(x, y, hoveredUnit.geometry.zMax, origin)
        void z
        return <Tooltip position={[p[0], p[1] + lift(hoveredUnit.storeyIds[0]) + 0.5, p[2]]} text={`${hoveredUnit.id} · ${hoveredUnit.storeyNames.join(', ')}`} tone="unit" />
      })()}
      {hoveredRoom && (() => {
        const xs = hoveredRoom.footprint.map((p) => p[0])
        const ys = hoveredRoom.footprint.map((p) => p[1])
        const p = ifcToWorld((Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2, hoveredRoom.zMax, origin)
        return <Tooltip position={[p[0], p[1] + lift(hoveredRoom.storeyId) + 0.4, p[2]]} text={`${hoveredRoom.name} · ${hoveredRoom.isFallback ? 'derived' : 'native Body'}`} tone="room" />
      })()}
    </group>
  )
}
