import { useEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { cameraPosition } from './camera'
import type { CameraView } from './settings'

interface CameraRigProps {
  view: CameraView
  /** Bumped on every explicit view/reset request so the same view can be re-applied. */
  nonce: number
  focusY: number
  distance: number
}

/** Eases the camera to preset views and keeps the orbit target on the active storey. */
export function CameraRig({ view, nonce, focusY, distance }: CameraRigProps) {
  const invalidate = useThree((s) => s.invalidate)
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null
  const applied = useRef({ nonce: -1, focusY: Number.NaN })
  const goal = useRef<{ position: THREE.Vector3 | null; target: THREE.Vector3 | null }>({ position: null, target: null })

  useEffect(() => { invalidate() }, [invalidate, view, nonce, focusY, distance])

  useEffect(() => {
    if (!controls) return
    const cancel = () => { goal.current.position = null; goal.current.target = null }
    controls.addEventListener('start', cancel)
    return () => controls.removeEventListener('start', cancel)
  }, [controls])

  useFrame((state) => {
    const orbit = state.controls as OrbitControlsImpl | null
    if (!orbit) return
    const camera = state.camera

    if (applied.current.nonce !== nonce) {
      const focus = new THREE.Vector3(0, focusY, 0)
      goal.current = { position: cameraPosition(view, focus, distance), target: focus }
      applied.current = { nonce, focusY }
    } else if (applied.current.focusY !== focusY) {
      const dy = focusY - orbit.target.y
      goal.current = {
        position: camera.position.clone().setY(camera.position.y + dy),
        target: orbit.target.clone().setY(focusY),
      }
      applied.current.focusY = focusY
    }

    const { position, target } = goal.current
    if (!position || !target) return
    camera.position.lerp(position, 0.16)
    orbit.target.lerp(target, 0.16)
    if (camera.position.distanceTo(position) < 0.02 && orbit.target.distanceTo(target) < 0.02) {
      camera.position.copy(position)
      orbit.target.copy(target)
      goal.current = { position: null, target: null }
    } else {
      state.invalidate()
    }
    orbit.update()
  })

  return null
}
