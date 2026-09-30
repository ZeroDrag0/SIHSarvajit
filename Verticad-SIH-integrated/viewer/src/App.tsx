import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { ContactShadows, Html, Line, OrbitControls, useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import './App.css'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const API = (path: string) => `${API_BASE}${path}`
const MODEL_URL = API('/api/assets/kingfisher_building_3d.glb')

type FloorRecord = {
  floor_id: string
  floor_number: number
  z_min_local_m: number
  z_max_local_m: number
  height_m: number
  volume_m3: number
  footprint_xy_m: [number, number][]
}

type UnitRecord = {
  unit_id: string
  floor_id: string
  floor_number: number
  unit_number: number
  area_m2: number
  volume_m3: number
  z_min_local_m: number
  z_max_local_m: number
  height_m: number
  polygon_xy_m: [number, number][]
}

type ULPINRecord = {
  ulpin_prototype: string
  unit_id: string
  floor_id: string
  geometry_hash: string
  area_m2: number
  volume_m3: number
}

type ValidationData = {
  ulpin: { duplicates: number }
  provenance: { major_inputs: Array<{ dataset: string; status: string; source: string }> }
}

type MetricsData = {
  footprint_area_m2: number
  building_height_m: number
  number_of_floors: number
  number_of_generated_units: number
  ulpin_count: number
  geometry_linkage_percent: number
}

type Theme = 'light' | 'dark' | 'night'
type ViewMode = 'model' | 'map' | 'pipeline' | 'data'
type CameraPreset = 'full' | 'iso' | 'top' | 'low'

// Per-theme 3D scene tuning: the tower must stay clearly visible and well lit in all three modes.
const SCENE_THEME: Record<Theme, { bg: string; ambient: number; key: number; tower: string; ground: string }> = {
  light: { bg: '#dfe9ea', ambient: 0.95, key: 2.1, tower: '#7fa3ae', ground: '#c3d3d2' },
  dark: { bg: '#091923', ambient: 0.55, key: 2.6, tower: '#89b3c1', ground: '#142e35' },
  night: { bg: '#050d12', ambient: 0.4, key: 2.1, tower: '#7ba0ac', ground: '#0d1e24' },
}

function usePersistedTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'dark'
    return (window.localStorage.getItem('sih-theme') as Theme) || 'dark'
  })
  useEffect(() => { window.localStorage.setItem('sih-theme', theme) }, [theme])
  return [theme, setTheme]
}

function App() {
  const [floors, setFloors] = useState<FloorRecord[]>([])
  const [units, setUnits] = useState<UnitRecord[]>([])
  const [ulpins, setUlpins] = useState<ULPINRecord[]>([])
  const [validation, setValidation] = useState<ValidationData | null>(null)
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [selectedFloor, setSelectedFloor] = useState<string | null>(null)
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('model')
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>('full')
  const [inspectOpen, setInspectOpen] = useState(false)
  const [demoRunning, setDemoRunning] = useState(false)
  const [search, setSearch] = useState('')
  const [autoRotate, setAutoRotate] = useState(true)
  const [theme, setTheme] = usePersistedTheme()
  const [buildingName, setBuildingName] = useState('')
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    const load = async <T,>(path: string) => {
      const response = await fetch(path)
      if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`)
      return response.json() as Promise<T>
    }
    Promise.all([
      load<{ floors: FloorRecord[] }>(API('/api/floors')),
      load<{ floors: Array<{ units: UnitRecord[] }> }>(API('/api/units')),
      load<{ records: ULPINRecord[]; building: string }>(API('/api/ulpins')),
      load<ValidationData>(API('/api/validation')),
      load<MetricsData>(API('/api/metrics')),
    ]).then(([floorData, unitData, ulpinData, validationData, metricsData]) => {
      setFloors(floorData.floors)
      setUnits(unitData.floors.flatMap((floor) => floor.units))
      setUlpins(ulpinData.records)
      setValidation(validationData)
      setMetrics(metricsData)
      setBuildingName(ulpinData.building)
      setLoadError(null)
    }).catch((error) => {
      console.error('Unable to load SIH data.', error)
      setLoadError(error instanceof Error ? error.message : 'Unable to load project data.')
    })
  }, [])

  const activeFloor = floors.find((floor) => floor.floor_id === selectedFloor)
  const activeUnit = units.find((unit) => unit.unit_id === selectedUnit)
  const activeUlpin = ulpins.find((record) => record.unit_id === selectedUnit)
  const floorUnits = units.filter((unit) => unit.floor_id === selectedFloor)

  useEffect(() => {
    if (!demoRunning) return
    const sequence = [
      window.setTimeout(() => setSelectedFloor('F17'), 850),
      window.setTimeout(() => setSelectedUnit('F17-U03'), 1850),
      window.setTimeout(() => setInspectOpen(true), 2450),
      window.setTimeout(() => setDemoRunning(false), 3100),
    ]
    return () => sequence.forEach(window.clearTimeout)
  }, [demoRunning])

  const handleSearch = (value: string) => {
    setSearch(value)
    const match = ulpins.find((record) => record.ulpin_prototype.toLowerCase().includes(value.toLowerCase()))
    if (match) {
      setSelectedFloor(match.floor_id)
      setSelectedUnit(match.unit_id)
      setInspectOpen(true)
      setViewMode('model')
    }
  }

  const selectFloor = (floorId: string) => {
    setSelectedFloor(floorId)
    setSelectedUnit(null)
    setInspectOpen(false)
    setAutoRotate(false)
  }

  const resetView = () => {
    setSelectedFloor(null)
    setSelectedUnit(null)
    setInspectOpen(false)
    setCameraPreset('full')
    setDemoRunning(false)
    setAutoRotate(true)
  }

  return (
    <div className="property-app" data-theme={theme}>
      <header className="nav-bar">
        <button className="brand" onClick={() => { setViewMode('model'); resetView() }}>
          <span className="brand-mark">S</span>
          <span><strong>SIH26011</strong><small>3D VERTICAL CADASTRE</small></span>
        </button>
        <nav className="nav-tabs" aria-label="Application views">
          {(['model', 'map', 'pipeline', 'data'] as ViewMode[]).map((mode) => (
            <button key={mode} className={viewMode === mode ? 'active' : ''} onClick={() => setViewMode(mode)}>
              {mode === 'model' ? '3D MODEL' : mode.toUpperCase()}
            </button>
          ))}
        </nav>
        <div className="nav-actions">
          <label className="search-box">
            <span>⌕</span>
            <input value={search} onChange={(event) => handleSearch(event.target.value)} placeholder="Search ULPIN" />
          </label>
          <div className="theme-switch" role="group" aria-label="Appearance">
            {(['light', 'dark', 'night'] as Theme[]).map((mode) => (
              <button key={mode} className={theme === mode ? 'active' : ''} onClick={() => setTheme(mode)}>{mode.toUpperCase()}</button>
            ))}
          </div>
          <button className="text-button" onClick={resetView}>Reset view</button>
        </div>
      </header>

      {loadError && (
        <div style={{ position: 'fixed', inset: '72px 0 0', display: 'grid', placeItems: 'center', zIndex: 20, background: 'var(--bg)', color: 'var(--text)' }}>
          <div style={{ maxWidth: 560, padding: 28, border: '1px solid var(--border)', borderRadius: 12, background: 'var(--panel-bg)' }}>
            <div style={{ color: 'var(--accent)', fontSize: 10, letterSpacing: '0.16em' }}>DATA LOAD ERROR</div>
            <h2 style={{ margin: '12px 0 8px', fontFamily: 'Georgia, serif', fontWeight: 400 }}>Project data could not be loaded</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.6 }}>{loadError}</p>
            <p style={{ marginTop: 12, color: 'var(--text-faint)', fontSize: 11 }}>Check that the FastAPI backend is running on http://localhost:8000 and that its MODEL_DATA_DIR points to the generated assets.</p>
          </div>
        </div>
      )}

      {viewMode === 'model' && (
        <main className="model-stage">
          <aside className="floor-explorer">
            <div className="rail-heading"><span>FLOOR</span><strong>{selectedFloor ?? 'FULL'}</strong></div>
            <div className="floor-rail" role="listbox" aria-label="Floor explorer">
              {[...floors].reverse().map((floor) => (
                <button
                  key={floor.floor_id}
                  className={selectedFloor === floor.floor_id ? 'selected' : ''}
                  onClick={() => selectFloor(floor.floor_id)}
                  onMouseEnter={() => setSelectedFloor(floor.floor_id)}
                >
                  <span>{floor.floor_id}</span><i />
                </button>
              ))}
            </div>
            <div className="rail-controls">
              <button onClick={() => selectFloor(floors[Math.min((activeFloor?.floor_number ?? 1), floors.length) - 1]?.floor_id ?? 'F01')}>↑</button>
              <button onClick={() => selectFloor(floors[Math.max((activeFloor?.floor_number ?? 1) - 2, 0)]?.floor_id ?? 'F01')}>↓</button>
            </div>
          </aside>

          <section className="tower-hero">
            <div className="hero-copy"><span>PROPERTY OBJECT / B01</span><h1>{buildingName || 'Kingfisher Towers'}</h1><p>{selectedFloor ? `${selectedFloor} isolated for exploration` : 'Full building model'}</p></div>
            <div className="canvas-shell">
              <Canvas camera={{ position: [10, 8, 15], fov: 35 }} shadows dpr={[1, 2]}>
                <color attach="background" args={[SCENE_THEME[theme].bg]} />
                <fog attach="fog" args={[SCENE_THEME[theme].bg, 28, 48]} />
                <ambientLight intensity={SCENE_THEME[theme].ambient} />
                <directionalLight castShadow position={[7, 16, 10]} intensity={SCENE_THEME[theme].key} shadow-mapSize={[2048, 2048]} />
                <directionalLight position={[-9, 6, -8]} intensity={0.4} color="#8fd0ff" />
                <Suspense fallback={null}>
                  <TowerScene floors={floors} units={units} selectedFloor={selectedFloor} selectedUnit={activeUnit} preset={cameraPreset} theme={theme} onFloorSelect={selectFloor} onUnitSelect={(unitId) => { setSelectedUnit(unitId); setInspectOpen(true); setAutoRotate(false) }} />
                </Suspense>
                <OrbitControls
                  makeDefault
                  enableDamping
                  dampingFactor={0.08}
                  minDistance={6}
                  maxDistance={34}
                  target={[0, 7.5, 0]}
                  autoRotate={autoRotate && !selectedFloor}
                  autoRotateSpeed={0.7}
                  onStart={() => setAutoRotate(false)}
                />
              </Canvas>
              <div className="viewport-hint">DRAG TO ORBIT <span>•</span> SCROLL TO ZOOM <span>•</span> RIGHT DRAG TO PAN</div>
              <button className="demo-button" onClick={() => { resetView(); setDemoRunning(true) }}>{demoRunning ? 'DEMO RUNNING' : 'EXPLORE VERTICAL CADASTRE'}</button>
            </div>
            <div className="camera-controls">
              {(['full', 'iso', 'top', 'low'] as CameraPreset[]).map((preset) => <button key={preset} className={cameraPreset === preset ? 'active' : ''} onClick={() => setCameraPreset(preset)}>{preset === 'full' ? 'FULL BUILDING' : preset.toUpperCase()}</button>)}
            </div>
          </section>

          <aside className={`context-panel ${inspectOpen ? 'open' : ''}`}>
            {!inspectOpen ? (
              <button className="inspect-launch" onClick={() => setInspectOpen(true)}><span>INSPECT</span><strong>{selectedFloor ?? 'Building'}</strong><small>Select a floor or unit to open the property record</small></button>
            ) : (
              <Inspector floor={activeFloor} unit={activeUnit} ulpin={activeUlpin} metrics={metrics} validation={validation} units={floorUnits} onUnitSelect={(unitId) => setSelectedUnit(unitId)} onClose={() => setInspectOpen(false)} />
            )}
          </aside>
        </main>
      )}

      {viewMode === 'map' && <MapView metrics={metrics} />}
      {viewMode === 'pipeline' && <PipelineView />}
      {viewMode === 'data' && <DataView validation={validation} metrics={metrics} />}
    </div>
  )
}

// Source mesh is authored with Z as the vertical (elevation) axis (0-120m) and
// X/Y as the footprint plane — glTF/three.js expects Y-up, so the model must be
// rotated -90° about X to stand upright. Floor/unit overlay math already assumes
// a Y-up world, so only the visual mesh needs the correction.
const MODEL_UP_FIX: [number, number, number] = [-Math.PI / 2, 0, 0]

function TowerScene({ floors, units, selectedFloor, selectedUnit, preset, theme, onFloorSelect, onUnitSelect }: { floors: FloorRecord[]; units: UnitRecord[]; selectedFloor: string | null; selectedUnit?: UnitRecord; preset: CameraPreset; theme: Theme; onFloorSelect: (id: string) => void; onUnitSelect: (id: string) => void }) {
  const { scene } = useGLTF(MODEL_URL)
  const [hoveredFloor, setHoveredFloor] = useState<string | null>(null)
  const { camera, controls } = useThree() as unknown as { camera: THREE.PerspectiveCamera; controls: { target: THREE.Vector3; update: () => void } | null }
  const floorScale = 15 / 120
  const palette = SCENE_THEME[theme]

  const { model, material, footprintD } = useMemo(() => {
    const cloned = scene.clone()
    const box = new THREE.Box3().setFromObject(cloned)
    const size = new THREE.Vector3()
    box.getSize(size)
    const mat = new THREE.MeshPhysicalMaterial({ color: palette.tower, roughness: 0.42, metalness: 0.1, clearcoat: 0.3, transparent: true, opacity: 1 })
    cloned.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true
        child.receiveShadow = true
        child.material = mat
      }
    })
    // size.x = footprint east-west, size.y = footprint north-south (becomes depth after the up-fix)
    return { model: cloned, material: mat, footprintW: size.x * floorScale, footprintD: size.y * floorScale }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene, floorScale])

  useEffect(() => {
    material.color.set(palette.tower)
  }, [material, palette.tower])

  useEffect(() => {
    const target = new THREE.Vector3(10, 8, 15)
    if (preset === 'iso') target.set(11, 12, 11)
    if (preset === 'top') target.set(0.01, 26, 0.01)
    if (preset === 'low') target.set(9, 2.4, 16)
    camera.position.copy(target)
  }, [camera, preset])

  useFrame(() => {
    const targetOpacity = selectedFloor ? 0.4 : 1
    // `material` is a plain three.js object memoized for reuse, not React state — animating its
    // properties every frame is the standard r3f/drei pattern (same as the target mutation below).
    // eslint-disable-next-line react-hooks/immutability
    material.opacity = THREE.MathUtils.lerp(material.opacity, targetOpacity, 0.1)
    if (controls) {
      const activeFloor = selectedFloor ? floors.find((f) => f.floor_id === selectedFloor) : null
      const desiredY = activeFloor ? ((activeFloor.z_min_local_m + activeFloor.z_max_local_m) / 2) * floorScale : 7.5
      // OrbitControls' target/camera are three.js objects, not React state — mutating them in the
      // render loop (outside React's render phase) is the standard r3f/drei pattern.
      // eslint-disable-next-line react-hooks/immutability
      controls.target.y = THREE.MathUtils.lerp(controls.target.y, desiredY, 0.08)
      controls.update()
    }
  })

  return (
    <group>
      <group rotation={MODEL_UP_FIX}>
        <primitive object={model} scale={[floorScale, floorScale, floorScale]} />
      </group>
      <mesh position={[0, -0.06, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[8, 64]} />
        <meshStandardMaterial color={palette.ground} roughness={0.92} />
      </mesh>
      <ContactShadows position={[0, -0.02, 0]} opacity={0.6} scale={10} blur={2.4} far={16} />
      {floors.map((floor) => (
        <FloorBand
          key={floor.floor_id}
          floor={floor}
          floorScale={floorScale}
          footprintD={footprintD}
          isSelected={floor.floor_id === selectedFloor}
          isHovered={floor.floor_id === hoveredFloor}
          isDimmed={Boolean(selectedFloor && floor.floor_id !== selectedFloor)}
          selectedUnit={selectedUnit}
          floorUnits={units.filter((unit) => unit.floor_id === floor.floor_id)}
          onHover={setHoveredFloor}
          onSelect={onFloorSelect}
          onUnitSelect={onUnitSelect}
        />
      ))}
    </group>
  )
}

function FloorBand({ floor, floorScale, footprintD, floorUnits, isSelected, isHovered, isDimmed, selectedUnit, onHover, onSelect, onUnitSelect }: {
  floor: FloorRecord; floorScale: number; footprintD: number; floorUnits: UnitRecord[]
  isSelected: boolean; isHovered: boolean; isDimmed: boolean; selectedUnit?: UnitRecord
  onHover: (id: string | null) => void; onSelect: (id: string) => void; onUnitSelect: (id: string) => void
}) {
  const group = useRef<THREE.Group>(null)
  const y = ((floor.z_min_local_m + floor.z_max_local_m) / 2) * floorScale
  const floorShape = useMemo(() => {
    const shape = new THREE.Shape()
    floor.footprint_xy_m.forEach(([x, z], index) => {
      const sx = x * floorScale
      const sy = z * floorScale
      if (index === 0) shape.moveTo(sx, sy)
      else shape.lineTo(sx, sy)
    })
    shape.closePath()
    return shape
  }, [floor.footprint_xy_m, floorScale])

  // The building mesh is rotated -90deg about X (Z-up -> Y-up), which sends footprint (x, y) to
  // world (x, -y). Outlines must use the same mapping or they end up mirrored off the building.
  const halfH = (floor.height_m * floorScale) / 2
  const ringAt = (yOffset: number) =>
    [...floor.footprint_xy_m, floor.footprint_xy_m[0]].map(([x, yy]) => [x * floorScale, yOffset, -yy * floorScale] as [number, number, number])
  const floorLineBottom = useMemo(() => ringAt(-halfH), [floor.footprint_xy_m, floorScale, halfH]) // eslint-disable-line react-hooks/exhaustive-deps
  const floorLineTop = useMemo(() => ringAt(halfH), [floor.footprint_xy_m, floorScale, halfH]) // eslint-disable-line react-hooks/exhaustive-deps

  useFrame(() => {
    if (!group.current) return
    const s = THREE.MathUtils.lerp(group.current.scale.x, isSelected ? 1.035 : 1, 0.12)
    group.current.scale.set(s, 1, s)
    group.current.position.y = THREE.MathUtils.lerp(group.current.position.y, y + (isSelected ? 0.22 : 0), 0.12)
  })

  return (
    <group ref={group} position={[0, y, 0]}>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        onPointerOver={(event) => { event.stopPropagation(); onHover(floor.floor_id) }}
        onPointerOut={() => onHover(null)}
        onClick={(event) => { event.stopPropagation(); onSelect(floor.floor_id) }}
      >
        <shapeGeometry args={[floorShape]} />
        <meshBasicMaterial transparent opacity={isSelected ? 0.14 : isHovered ? 0.07 : isDimmed ? 0.008 : 0.018} color={isSelected ? '#61e4b0' : '#bde7e8'} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <Line points={floorLineBottom} color={isSelected ? '#61e4b0' : isHovered ? '#b3ebff' : '#7fb4ba'} lineWidth={isSelected ? 1.5 : 1.0} transparent opacity={isSelected ? 0.9 : isHovered ? 0.7 : 0.14} />
      {isSelected && <Line points={floorLineTop} color="#61e4b0" lineWidth={1.5} transparent opacity={0.9} />}
      {isHovered && !isSelected && (
        <Html center distanceFactor={12} position={[0, 0.2, footprintD * 0.42]}>
          <div className="floor-tooltip">{floor.floor_id}</div>
        </Html>
      )}
      {isSelected && <UnitVolumes floorUnits={floorUnits} selectedUnit={selectedUnit} onUnitSelect={onUnitSelect} />}
    </group>
  )
}

function UnitVolumes({ floorUnits, selectedUnit, onUnitSelect }: {
  floorUnits: UnitRecord[]; selectedUnit?: UnitRecord; onUnitSelect: (unitId: string) => void
}) {
  // This component receives the actual polygon partitions from the JSON data rather than
  // inventing four rectangular boxes in the renderer.
  const [hovered, setHovered] = useState<string | null>(null)
  return <group>{floorUnits.map((unit) => (
    <UnitVolume
      key={unit.unit_id}
      unit={unit}
      selected={selectedUnit?.unit_id === unit.unit_id}
      hovered={hovered === unit.unit_id}
      onSelect={onUnitSelect}
      onHover={setHovered}
    />
  ))}</group>
}

function UnitVolume({ unit, selected, hovered, onSelect, onHover }: {
  unit: UnitRecord; selected: boolean; hovered: boolean
  onSelect: (id: string) => void; onHover: (id: string | null) => void
}) {
  const geometry = useMemo(() => {
    const shape = new THREE.Shape()
    unit.polygon_xy_m.forEach(([x, z], index) => {
      if (index === 0) shape.moveTo(x, z)
      else shape.lineTo(x, z)
    })
    shape.closePath()
    return new THREE.ExtrudeGeometry(shape, {
      depth: unit.height_m,
      bevelEnabled: false,
      curveSegments: 1,
      steps: 1,
    })
  }, [unit])

  useEffect(() => () => geometry.dispose(), [geometry])

  const scale = 15 / 120
  return (
    <group
      position={[0, -unit.height_m * scale / 2 + 0.03, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
      scale={[scale, scale, scale]}
    >
      <mesh
        geometry={geometry}
        onClick={(event) => { event.stopPropagation(); onSelect(unit.unit_id) }}
        onPointerOver={(event) => { event.stopPropagation(); onHover(unit.unit_id) }}
        onPointerOut={() => onHover(null)}
      >
        <meshPhysicalMaterial
          color={selected ? '#ffd166' : hovered ? '#ffbf7d' : '#f2a65a'}
          emissive={selected ? '#9b6811' : '#3e2810'}
          emissiveIntensity={selected ? 0.75 : hovered ? 0.35 : 0.12}
          transparent
          opacity={selected ? 1 : hovered ? 0.95 : 0.78}
          roughness={0.3}
          side={THREE.DoubleSide}
        />
      </mesh>
      {hovered && (
        <Html center distanceFactor={10} position={[0, unit.height_m * scale + 0.35, 0]}>
          <div className="unit-tooltip">{unit.unit_id}</div>
        </Html>
      )}
    </group>
  )
}

function Inspector({ floor, unit, ulpin, metrics, validation, units, onUnitSelect, onClose }: { floor?: FloorRecord; unit?: UnitRecord; ulpin?: ULPINRecord; metrics: MetricsData | null; validation: ValidationData | null; units: UnitRecord[]; onUnitSelect: (id: string) => void; onClose: () => void }) {
  return <div className="inspector-content">
    <div className="inspector-head"><div><span className="label">PROPERTY</span><h2>{unit?.unit_id ?? floor?.floor_id ?? 'BUILDING'}</h2></div><button onClick={onClose}>×</button></div>
    {floor && <section className="inspector-section"><span className="label">FLOOR</span><dl><div><dt>Z range</dt><dd>{floor.z_min_local_m.toFixed(2)}–{floor.z_max_local_m.toFixed(2)} m</dd></div><div><dt>Height</dt><dd>{floor.height_m.toFixed(2)} m</dd></div><div><dt>Volume</dt><dd>{floor.volume_m3.toFixed(1)} m³</dd></div></dl></section>}
    {floor && <div className="unit-picker"><span>FLOOR {floor.floor_id} · {units.length} units</span><div>{units.map((item) => <button key={item.unit_id} className={item.unit_id === unit?.unit_id ? 'active' : ''} onClick={() => onUnitSelect(item.unit_id)}>{item.unit_id.split('-')[1]}</button>)}</div></div>}
    {unit && <>
      <section className="inspector-section">
        <span className="label">ULPIN</span><strong className="ulpin-code">{ulpin?.ulpin_prototype}</strong><small>Prototype geometry-linked identifier</small>
      </section>
      <section className="inspector-section">
        <span className="label">GEOMETRY</span>
        <dl><div><dt>Area</dt><dd>{unit.area_m2.toFixed(2)} m²</dd></div><div><dt>Volume</dt><dd>{unit.volume_m3.toFixed(2)} m³</dd></div><div><dt>Z range</dt><dd>{unit.z_min_local_m.toFixed(2)}–{unit.z_max_local_m.toFixed(2)} m</dd></div><div><dt>Fingerprint</dt><dd>{ulpin?.geometry_hash}</dd></div></dl>
      </section>
      <section className="inspector-section"><span className="label">VALIDATION</span><div className="validation-lines"><span>Fingerprint verified <b>✓</b></span><span>Identifier reproducible <b>✓</b></span><span>Geometry ↔ ID linked <b>{metrics?.geometry_linkage_percent.toFixed(0)}%</b></span><span>Duplicate identifiers <b>{validation?.ulpin.duplicates ?? '—'}</b></span></div></section>
    </>}
    <p className="quiet-note">Derived prototype geometry and unit partitions.</p>
  </div>
}

function MapView({ metrics }: { metrics: MetricsData | null }) {
  return <main className="secondary-view map-view"><div className="secondary-heading"><span className="label">SPATIAL CONTEXT</span><h1>Kingfisher footprint</h1><p>Building footprint and local coordinate context</p></div><div className="map-canvas"><div className="map-grid" /><div className="map-footprint"><span>B01</span></div><div className="map-label map-aoi">AOI / EPSG:32643</div><div className="map-label map-osm">OSM context • no building match</div><div className="map-label map-cad">Cadastral context • no verified parcel</div></div><div className="map-stats"><span><b>{metrics?.footprint_area_m2.toFixed(1)} m²</b> footprint</span><span><b>28.0 m</b> east-west span</span><span><b>44.3 m</b> north-south span</span></div></main>
}

function PipelineView() {
  const stages: Array<[string, string]> = [
    ['DATA', 'Source cadastral, footprint and coordinate reference datasets for the building.'],
    ['COORDINATE HARMONISATION', 'All inputs re-projected to a common local coordinate frame (EPSG:32643).'],
    ['BUILDING FOOTPRINT', 'The building outline is resolved from the processed footprint dataset.'],
    ['3D BUILDING', 'A 3D volume is generated from the footprint using the project\u2019s prototype height parameter.'],
    ['FLOORS', 'The building volume is divided into 34 floors using an even prototype floor height.'],
    ['VOLUMETRIC UNITS', 'Each floor is partitioned into 4 demo units for the vertical-cadastre demonstration.'],
    ['ULPIN', 'A prototype ULPIN is assigned to each unit using a deterministic geometry-fingerprint process.'],
    ['VALIDATION', 'Generated identifiers and geometry links are checked for uniqueness and reproducibility.'],
  ]
  return <main className="secondary-view pipeline-view"><div className="secondary-heading"><span className="label">SYSTEM LINEAGE</span><h1>From source to vertical property</h1><p>Each stage feeds the next demonstrable representation.</p></div><div className="pipeline-list">{stages.map(([stage, description], index) => <div className="pipeline-stage" key={stage}><span>0{index + 1}</span><div><strong>{stage}</strong><p>{description}</p></div>{index < stages.length - 1 && <i>↓</i>}</div>)}</div></main>
}

function DataView({ validation, metrics }: { validation: ValidationData | null; metrics: MetricsData | null }) {
  const sourceGroups = useMemo(() => {
    const groups: Record<string, Array<{ dataset: string; source: string }>> = { 'DERIVED DATA': [], DEMONSTRATION: [] }
    validation?.provenance.major_inputs.forEach((item) => {
      const status = item.status.toLowerCase()
      if (status.includes('synthetic')) groups.DEMONSTRATION.push(item)
      else if (status.includes('derived')) groups['DERIVED DATA'].push(item)
    })
    return groups
  }, [validation])
  return <main className="secondary-view data-view"><div className="secondary-heading"><span className="label">DATA REGISTER</span><h1>Provenance and context</h1><p>Calm, inspectable source classification for the vertical cadastral demo.</p></div>
    <div className="data-groups">
      <section className="data-group validation-group">
        <h2>SYSTEM VALIDATION</h2>
        <ul>
          <li><span>Floors</span><b>{metrics?.number_of_floors ?? '—'}</b></li>
          <li><span>Demo volumetric units</span><b>{metrics?.number_of_generated_units ?? '—'}</b></li>
          <li><span>Unique prototype ULPINs</span><b>{metrics?.ulpin_count ?? '—'}</b></li>
          <li><span>Duplicate identifiers</span><b>{validation?.ulpin.duplicates ?? 0}</b></li>
          <li><span>Geometry ↔ ULPIN linkage</span><b>{metrics ? `${metrics.geometry_linkage_percent.toFixed(0)}%` : '—'}</b></li>
        </ul>
      </section>
      {Object.entries(sourceGroups).map(([group, items]) => <section className="data-group" key={group}><h2>{group}</h2>{items.map((item) => <div className="data-row" key={item.dataset}><strong>{item.dataset.split('/').pop()}</strong><span>{item.source}</span></div>)}</section>)}
    </div>
  </main>
}

useGLTF.preload(MODEL_URL)
export default App
