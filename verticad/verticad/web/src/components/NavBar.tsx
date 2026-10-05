import { ROUTES, ROUTE_LABEL, routeHref, type Route } from '../services/router'
import type { ThemeName } from '../viewer/palette'

export function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 36 36" fill="none" aria-hidden="true">
      <rect x="2" y="23" width="6" height="11" fill="currentColor" opacity="0.55" />
      <rect x="10" y="17" width="6" height="17" fill="currentColor" opacity="0.75" />
      <rect x="18" y="9" width="6" height="25" fill="currentColor" />
      <rect x="26" y="17" width="6" height="17" fill="currentColor" opacity="0.4" />
      <line x1="2" y1="34.5" x2="34" y2="34.5" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

export function NavBar({ route, theme, onTheme }: { route: Route; theme: ThemeName; onTheme: (theme: ThemeName) => void }) {
  return (
    <header className="nav-bar">
      <a className="brand" href={routeHref('overview')}>
        <span className="brand-mark"><Logo /></span>
        <span><strong>VERTICAD</strong><small>3D PROPERTY MAPPING</small></span>
      </a>
      <nav className="nav-tabs" aria-label="Main navigation">
        {ROUTES.map((r) => (
          <a key={r} href={routeHref(r)} className={route === r ? 'active' : ''} aria-current={route === r ? 'page' : undefined}>
            {ROUTE_LABEL[r].toUpperCase()}
          </a>
        ))}
      </nav>
      <div className="nav-actions">
        <div className="theme-switch" role="group" aria-label="Appearance">
          {(['dark', 'light'] as ThemeName[]).map((mode) => (
            <button key={mode} type="button" className={theme === mode ? 'active' : ''} aria-pressed={theme === mode} onClick={() => onTheme(mode)}>
              {mode.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
