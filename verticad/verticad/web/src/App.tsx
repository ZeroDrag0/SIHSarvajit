import { Suspense, lazy, useEffect, useState } from 'react'
import { DatasetGate } from './components/DatasetGate'
import { NavBar } from './components/NavBar'
import { LoadingState } from './components/States'
import { DataPage } from './pages/DataPage'
import { Landing } from './landing/Landing'
import { TechnologyPage } from './pages/TechnologyPage'
import { ValidationPage } from './pages/ValidationPage'
import { UnitsPage } from './pages/UnitsPage'
import { useRoute } from './services/router'
import { SelectionProvider } from './services/SelectionProvider'
import type { ThemeName } from './viewer/palette'

const ViewerPage = lazy(() => import('./pages/ViewerPage').then((m => ({ default: m.ViewerPage }))))
const THEME_KEY = 'verticad-theme'
function readTheme(): ThemeName {
  try { return window.localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark' } catch { return 'dark' }
}
export default function App() {
  const route = useRoute()
  const [theme, setTheme] = useState<ThemeName>(readTheme)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { window.localStorage.setItem(THEME_KEY, theme) } catch {}
  }, [theme])
  return <div className="app">
    <DatasetGate>
      <SelectionProvider>
        {route === 'overview' ? <Landing /> : <NavBar route={route} theme={theme} onTheme={setTheme} />}
        {route === 'viewer' && <Suspense fallback={<div className="gate"><LoadingState label="Loading 3D model…" /></div>}><ViewerPage theme={theme} /></Suspense>}
        {route === 'units' && <UnitsPage />}
        {route === 'validation' && <ValidationPage />}
        {route === 'data' && <DataPage />}
        {route === 'technology' && <TechnologyPage />}
      </SelectionProvider>
    </DatasetGate>
  </div>
}
