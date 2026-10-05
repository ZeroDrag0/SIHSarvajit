import { useEffect, useState } from 'react'
import { errorMessage, fetchSpaceGeometry } from '../api'
import type { IfcSpaceGeometry } from '../types'

export type SpaceGeometryState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: IfcSpaceGeometry[] }
  | { status: 'error'; error: string }

/** Room-level geometry is ~330 kB, so it is only requested once a layer needs it. */
export function useSpaceGeometry(enabled: boolean): SpaceGeometryState {
  const [state, setState] = useState<SpaceGeometryState>({ status: 'idle' })
  const [requested, setRequested] = useState(false)
  if (enabled && !requested) {
    setRequested(true)
    setState({ status: 'loading' })
  }

  useEffect(() => {
    if (!requested) return
    let cancelled = false
    fetchSpaceGeometry().then(
      (data) => { if (!cancelled) setState({ status: 'ready', data }) },
      (error: unknown) => { if (!cancelled) setState({ status: 'error', error: errorMessage(error) }) },
    )
    return () => { cancelled = true }
  }, [requested])

  return state
}
