import type { ReactNode } from 'react'

export function Page({ eyebrow, title, lede, aside, children }: { eyebrow: string; title: string; lede?: ReactNode; aside?: ReactNode; children: ReactNode }) {
  return (
    <main className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
          {lede && <p className="lede">{lede}</p>}
        </div>
        {aside && <div className="page-head-aside">{aside}</div>}
      </header>
      {children}
    </main>
  )
}

export function Panel({ title, action, children, className }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel${className ? ` ${className}` : ''}`}>
      {(title || action) && (
        <header className="panel-head">
          {title && <h2>{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

/** Definition row: label left, value right. */
export function Field({ label, children, mono, stack }: { label: string; children: ReactNode; mono?: boolean; stack?: boolean }) {
  return (
    <div className={`field${stack ? ' field--stack' : ''}`}>
      <dt>{label}</dt>
      <dd className={mono ? 'mono' : undefined}>{children}</dd>
    </div>
  )
}

export function Stat({ value, label, tone }: { value: ReactNode; label: string; tone?: 'warning' | 'error' | 'ok' }) {
  return (
    <div className={`stat${tone ? ` stat--${tone}` : ''}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}
