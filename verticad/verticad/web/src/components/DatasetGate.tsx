import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { DATA_MODE, clearApiCache, errorMessage, loadDataset } from '../api'
import { DatasetContext } from '../services/datasetContext'
import type { CadastreDataset } from '../types'
import { ErrorState, LoadingState } from './States'

type LoadState = { status: 'loading' } | { status: 'ready'; dataset: CadastreDataset } | { status: 'error'; error: string }

/** Loads the dataset through the API layer and blocks the app until it is available. */
export function DatasetGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    loadDataset().then(
      (dataset) => { if (!cancelled) setState({ status: 'ready', dataset }) },
      (error: unknown) => { if (!cancelled) setState({ status: 'error', error: errorMessage(error) }) },
    )
    return () => { cancelled = true }
  }, [attempt])

  const retry = useCallback(() => {
    clearApiCache()
    setState({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])

  if (state.status === 'loading') {
    return <div className="gate"><LoadingState label="Loading building…" /></div>
  }
  if (state.status === 'error') {
    return (
      <div className="gate">
        <ErrorState title={DATA_MODE === 'http' ? 'Backend unavailable' : 'Pipeline outputs unavailable'} detail={state.error} onRetry={retry}>
          <p className="muted">
            {DATA_MODE === 'http'
              ? 'Check that the API named in VITE_API_BASE_URL is running and returns the pipeline JSON documents.'
              : 'Run `npm run sync:data` to copy the pipeline outputs into public/data/schependomlaan.'}
          </p>
          <p className="muted">No substitute data is shown.</p>
        </ErrorState>
      </div>
    )
  }
  return <DatasetContext.Provider value={state.dataset}>{children}</DatasetContext.Provider>
}
