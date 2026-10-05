import { useEffect, useMemo, useRef, useState } from 'react'
import { useDataset } from '../services/datasetContext'
import { navigate } from '../services/router'
import { KIND_LABEL, buildSearchIndex, runSearch, type SearchEntry } from '../services/search'
import { useSelection } from '../services/selectionContext'

/** Global search over ULPIN, unit id, IFC space id/name, storey and building id. */
export function SearchBox() {
  const dataset = useDataset()
  const selection = useSelection()
  const index = useMemo(() => buildSearchIndex(dataset), [dataset])
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [cursor, setCursor] = useState(0)
  const root = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const results = useMemo(() => runSearch(index, query), [index, query])

  useEffect(() => {
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === '/' && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLTextAreaElement)) {
        event.preventDefault()
        input.current?.focus()
      }
    }
    window.addEventListener('pointerdown', onPointer)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('pointerdown', onPointer)
      window.removeEventListener('keydown', onKey)
    }
  }, [])

  const choose = (entry: SearchEntry) => {
    if (entry.spaceId) selection.selectSpace(entry.spaceId)
    else if (entry.unitId) selection.selectUnit(entry.unitId)
    else if (entry.storeyId) selection.selectStorey(entry.storeyId)
    else selection.clear()
    navigate('viewer')
    setQuery('')
    setOpen(false)
    input.current?.blur()
  }

  return (
    <div className="search" ref={root}>
      <label className="search-box">
        <span aria-hidden="true">⌕</span>
        <input
          ref={input}
          value={query}
          placeholder="Search ULPIN, unit, space, storey"
          aria-label="Search ULPIN, unit, IFC space, storey or building"
          role="combobox"
          aria-expanded={open && query.length > 0}
          aria-controls="search-results"
          onFocus={() => setOpen(true)}
          onChange={(event) => { setQuery(event.target.value); setCursor(0); setOpen(true) }}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') { event.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)) }
            else if (event.key === 'ArrowUp') { event.preventDefault(); setCursor((c) => Math.max(c - 1, 0)) }
            else if (event.key === 'Enter' && results[cursor]) choose(results[cursor])
            else if (event.key === 'Escape') { setOpen(false); input.current?.blur() }
          }}
        />
        <kbd aria-hidden="true">/</kbd>
      </label>
      {open && query.length > 0 && (
        <ul className="search-results" id="search-results" role="listbox">
          {results.length === 0 && <li className="search-empty">No match in this dataset</li>}
          {results.map((entry, i) => (
            <li key={entry.key} role="option" aria-selected={i === cursor}>
              <button type="button" className={i === cursor ? 'is-active' : ''} onMouseEnter={() => setCursor(i)} onClick={() => choose(entry)}>
                <span className="search-kind">{KIND_LABEL[entry.kind]}</span>
                <strong className="mono">{entry.title}</strong>
                <small>{entry.subtitle}</small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
