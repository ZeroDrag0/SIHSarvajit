import { Component, Suspense, useEffect, useState, type ReactNode } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { endpointLabel } from '../api'
import { cameraPosition } from './camera'
import { CameraRig } from './CameraRig'
import { SCENE_PALETTE, type ThemeName } from './palette'
import { Scene, type SceneProps } from './Scene'
import type { CameraView } from './settings'

class SceneErrorBoundary extends Component<{ onError: (message: string) => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(error: unknown) {
    this.props.onError(error instanceof Error ? error.message : 'Unknown error')
  }
  render() {
    return this.state.failed ? null : this.props.children
  }
}

/** Mounts only once the suspended GLB has resolved. */
function Ready({ onReady }: { onReady: () => void }) {
  useEffect(() => { onReady() }, [onReady])
  return null
}

export interface CadastralViewerProps extends Omit<SceneProps, 'palette'> {
  theme: ThemeName
  view: CameraView
  viewNonce: number
  onReady: () => void
}

export function CadastralViewer({ theme, view, viewNonce, onReady, ...scene }: CadastralViewerProps) {
  const palette = SCENE_PALETTE[theme]
  const [error, setError] = useState<string | null>(null)
  const { building, storeys, settings, selectedStoreyId } = scene

  const [min, max] = building.boundsM
  const radius = Math.hypot(max[0] - min[0], max[1] - min[1]) / 2
  const top = storeys.length > 0 ? Math.max(...storeys.map((s) => s.orderIndex)) : 0
  const fullHeight = building.zMax + settings.explode * top
  const selected = storeys.find((s) => s.id === selectedStoreyId)
  const focusY = selected
    ? (selected.zMin + (selected.zMax ?? selected.zMin)) / 2 + settings.explode * selected.orderIndex
    : (building.zMin + fullHeight) / 2
  const distance = Math.max(radius, fullHeight) * 3.25

  // Initial placement only; later moves go through <CameraRig>.
  const [initial] = useState(() => ({
    camera: cameraPosition('iso', new THREE.Vector3(0, focusY, 0), distance).toArray(),
    target: [0, focusY, 0] as [number, number, number],
  }))

  if (error) {
    return (
      <div className="viewer-fallback" role="alert">
        <span className="eyebrow">3D geometry unavailable</span>
        <p>The unit mesh could not be loaded from <code>{endpointLabel('unitsGlb')}</code>.</p>
        <p className="muted">{error}</p>
        <p className="muted">No placeholder building is drawn in its place.</p>
      </div>
    )
  }

  return (
    <Canvas
      frameloop="demand"
      dpr={[1, 1.75]}
      camera={{ position: initial.camera, fov: 34, near: 0.1, far: 600 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
    >
      <color attach="background" args={[palette.background]} />
      <ambientLight intensity={theme === 'dark' ? 0.85 : 1.1} />
      <directionalLight position={[18, 30, 22]} intensity={theme === 'dark' ? 2.1 : 1.8} />
      <directionalLight position={[-20, 12, -16]} intensity={0.55} color="#9fd0ff" />
      <SceneErrorBoundary onError={setError}>
        <Suspense fallback={null}>
          <Scene {...scene} palette={palette} />
          <Ready onReady={onReady} />
        </Suspense>
      </SceneErrorBoundary>
      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.1}
        minDistance={4}
        maxDistance={distance * 3}
        maxPolarAngle={Math.PI * 0.495}
        target={initial.target}
      />
      <CameraRig view={view} nonce={viewNonce} focusY={focusY} distance={distance} />
    </Canvas>
  )
}
