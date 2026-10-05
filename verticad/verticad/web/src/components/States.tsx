import type { ReactNode } from 'react'

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="state state--loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

export function ErrorState({ title, detail, onRetry, children }: { title: string; detail: string; onRetry?: () => void; children?: ReactNode }) {
  return (
    <div className="state state--error" role="alert">
      <span className="eyebrow eyebrow--error">Error</span>
      <h2>{title}</h2>
      <p className="mono">{detail}</p>
      {children}
      {onRetry && <button type="button" className="btn" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function UnavailableState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state state--unavailable">
      <span className="state-glyph" aria-hidden="true">○</span>
      <div>
        <strong>{title}</strong>
        {children && <p>{children}</p>}
      </div>
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="state state--empty">{children}</p>
}
