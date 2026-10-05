import * as THREE from 'three'
import type { CameraView } from './settings'

const DIRECTION: Record<CameraView, THREE.Vector3> = {
  iso: new THREE.Vector3(1, 0.72, 1).normalize(),
  top: new THREE.Vector3(0, 1, 0.0015).normalize(),
  front: new THREE.Vector3(0, 0.12, 1).normalize(),
  side: new THREE.Vector3(1, 0.12, 0).normalize(),
}

export function cameraPosition(view: CameraView, focus: THREE.Vector3, distance: number): THREE.Vector3 {
  return focus.clone().addScaledVector(DIRECTION[view], distance)
}
