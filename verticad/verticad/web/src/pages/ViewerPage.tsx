import { useCallback, useMemo, useState } from 'react'
import { Inspector } from '../components/Inspector'
import { useDataset } from '../services/datasetContext'
import { useSelection } from '../services/selectionContext'
import { useSpaceGeometry } from '../services/useSpaceGeometry'
import { fmt } from '../utils/format'
import { ringsBounds } from '../utils/geometry'
import { CadastralViewer } from '../viewer/CadastralViewer'
import { FloorRail } from '../viewer/FloorRail'
import { LayerPanel } from '../viewer/LayerPanel'
import { SCENE_PALETTE, storeyColorMap, type ThemeName } from '../viewer/palette'
import { CAMERA_VIEWS, DEFAULT_SETTINGS, type CameraView, type LayerKey, type ViewerSettings } from '../viewer/settings'

export function ViewerPage({ theme }: { theme: ThemeName }) {
  const { name, building, storeys, units, spaces, metrics } = useDataset()
  const selection = useSelection()
  const [settings, setSettings] = useState<ViewerSettings>(DEFAULT_SETTINGS)
  const [view, setView] = useState<CameraView>('iso')
  const [viewNonce, setViewNonce] = useState(0)
  const [ready, setReady] = useState(false)
  const [leftOpen, setLeftOpen] = useState(false)
  const [rightOpen, setRightOpen] = useState(false)

  const roomsForced = selection.spaceId !== null && spaces.some((s) => s.globalId === selection.spaceId && s.unitId !== null)
  const showRooms = settings.layers.rooms || roomsForced
  const needGeometry = showRooms || settings.layers.common || selection.spaceId !== null
  const spaceGeometry = useSpaceGeometry(needGeometry)
  const spaceOwner = useMemo(() => new Map(spaces.map((s) => [s.globalId, s.unitId])), [spaces])

  const palette = SCENE_PALETTE[theme]
  const storeyColors = useMemo(() => storeyColorMap(storeys, palette), [storeys, palette])
  const unit = units.find((u) => u.id === selection.unitId)
  const storey = storeys.find((s) => s.id === selection.storeyId)

  const applyView = (next: CameraView) => { setView(next); setViewNonce((n) => n + 1) }
  const toggleLayer = (layer: LayerKey) => setSettings((s) => ({ ...s, layers: { ...s.layers, [layer]: !s.layers[layer] } }))
  const onReady = useCallback(() => setReady(true), [])
  const selectUnit = useCallback((id: string) => { selection.selectUnit(id); setRightOpen(true) }, [selection])
  const selectSpace = useCallback((id: string) => { selection.selectSpace(id); setRightOpen(true) }, [selection])

  const measure = useMemo(() => {
    if (unit) {
      const b = ringsBounds(unit.geometry.footprint)
      return b ? `${unit.id} · ${fmt(b.maxX - b.minX)} × ${fmt(b.maxY - b.minY)} × ${fmt(unit.geometry.heightM)} m` : null
    }
    if (storey) return `${storey.name} · z ${fmt(storey.zMin)} → ${storey.zMax === null ? 'not measured' : `${fmt(storey.zMax)} m`}`
    const [min, max] = building.boundsM
    return `Space envelope · ${fmt(max[0] - min[0])} × ${fmt(max[1] - min[1])} × ${fmt(building.heightM)} m`
  }, [unit, storey, building])

  const subtitle = unit
    ? `${unit.id} selected · ${unit.storeyNames.join(', ')}`
    : storey
      ? `${storey.name} ${settings.isolate ? 'isolated' : 'highlighted'}`
      : 'Full building · inferred property units'

  return (
    <main className={`model-stage${leftOpen ? ' left-open' : ''}${rightOpen ? ' right-open' : ''}`}>
      <aside className="stage-left">
        <button type="button" className="btn btn--sm drawer-close" onClick={() => setLeftOpen(false)}>Close</button>
        <FloorRail storeys={storeys} selectedId={selection.storeyId} onSelect={selection.selectStorey} />
        <LayerPanel settings={settings} roomsForced={roomsForced} spaceGeometry={spaceGeometry} onToggle={toggleLayer} />
      </aside>

      <section className="stage-view">
        <div className="hero-copy">
          <span className="eyebrow">3D cadastral viewer · {building.id}</span>
          <h1>{name}</h1>
          <p>{subtitle}</p>
        </div>

        <div className="camera-controls" role="group" aria-label="Camera">
          {CAMERA_VIEWS.map((v) => (
            <button key={v.key} type="button" className={view === v.key ? 'active' : ''} onClick={() => applyView(v.key)}>{v.label}</button>
          ))}
          <button type="button" onClick={() => applyView('iso')}>RESET</button>
        </div>

        <div className="panel-toggles">
          <button type="button" className="btn btn--sm" aria-expanded={leftOpen} onClick={() => { setLeftOpen((o) => !o); setRightOpen(false) }}>Storeys &amp; layers</button>
          <button type="button" className="btn btn--sm" aria-expanded={rightOpen} onClick={() => { setRightOpen((o) => !o); setLeftOpen(false) }}>Inspector</button>
        </div>

        <div className="canvas-shell">
          <CadastralViewer
            theme={theme}
            view={view}
            viewNonce={viewNonce}
            onReady={onReady}
            building={building}
            storeys={storeys}
            units={units}
            spaceGeometry={spaceGeometry.status === 'ready' ? spaceGeometry.data : null}
            spaceOwner={spaceOwner}
            settings={settings}
            showRooms={showRooms}
            selectedStoreyId={selection.storeyId}
            selectedUnitId={selection.unitId}
            selectedSpaceId={selection.spaceId}
            onSelectUnit={selectUnit}
            onSelectSpace={selectSpace}
            onSelectStorey={selection.selectStorey}
          />
          {!ready && <div className="canvas-loading" role="status"><span className="spinner" aria-hidden="true" />Loading unit geometry…</div>}
        </div>

        <div className="view-footer">
          <div className="legend">
            {settings.colorMode === 'storey'
              ? storeys.filter((s) => storeyColors.has(s.id)).map((s) => (
                  <span key={s.id}><i style={{ background: storeyColors.get(s.id) }} />{s.name}</span>
                ))
              : (
                <>
                  <span><i style={{ background: palette.native }} />Native IFC Body · {metrics.nativeGeometries} spaces</span>
                  <span><i style={{ background: palette.derived }} />Derived FootPrint + Box · {metrics.derivedGeometries} spaces</span>
                </>
              )}
            <span><i style={{ background: palette.selected }} />Selected</span>
          </div>
          <div className="view-tools">
            <label className="tool">
              <span>Opacity</span>
              <input type="range" min={0.15} max={1} step={0.05} value={settings.unitOpacity} onChange={(e) => setSettings((s) => ({ ...s, unitOpacity: Number(e.target.value) }))} />
            </label>
            <label className="tool">
              <span>Explode</span>
              <input type="range" min={0} max={4} step={0.25} value={settings.explode} onChange={(e) => setSettings((s) => ({ ...s, explode: Number(e.target.value) }))} />
            </label>
            <label className="tool tool--check">
              <input type="checkbox" checked={settings.isolate} onChange={() => setSettings((s) => ({ ...s, isolate: !s.isolate }))} />
              <span>Isolate storey</span>
            </label>
            <div className="segmented" role="group" aria-label="Colour by">
              <button type="button" className={settings.colorMode === 'storey' ? 'active' : ''} onClick={() => setSettings((s) => ({ ...s, colorMode: 'storey' }))}>STOREY</button>
              <button type="button" className={settings.colorMode === 'source' ? 'active' : ''} onClick={() => setSettings((s) => ({ ...s, colorMode: 'source' }))}>GEOMETRY SOURCE</button>
            </div>
          </div>
          <div className="view-status">
            {measure && <span className="mono">{measure}</span>}
            <span>IFC local metres · {building.crs.coordinateStatus}{settings.explode > 0 ? ' · exploded view (display offset only)' : ''}</span>
          </div>
        </div>
      </section>

      <aside className="stage-right">
        <button type="button" className="btn btn--sm drawer-close" onClick={() => setRightOpen(false)}>Close</button>
        <Inspector spaceGeometry={spaceGeometry.status === 'ready' ? spaceGeometry.data : null} />
      </aside>
    </main>
  )
}
