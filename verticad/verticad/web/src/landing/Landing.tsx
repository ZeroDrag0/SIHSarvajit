import type { MouseEvent } from 'react'
import { useDataset } from '../services/datasetContext'
import { routeHref } from '../services/router'
import './landing.css'

const VIEWER_HREF = routeHref('viewer')
const PREVIEW_IMAGE = `${import.meta.env.BASE_URL}images/property-preview.png`

/** In-page section links. The app routes by URL hash, so scroll instead of changing the hash. */
function jump(event: MouseEvent<HTMLAnchorElement>, id: string) {
  event.preventDefault()
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ━━━━━━━━━━━━━━━━ ICONS ━━━━━━━━━━━━━━━━

function IconBuilding({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2 21h20M4 21V8l8-5 8 5v13M9 21v-8h6v8" />
    </svg>
  )
}
function IconLayers({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 2 2.5 7 12 12l9.5-5L12 2zm-9.5 10 9.5 5 9.5-5m-19 5 9.5 5 9.5-5" />
    </svg>
  )
}
function IconID({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="7" width="18" height="14" rx="2" strokeLinecap="round" strokeLinejoin="round" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V5a4 4 0 0 1 8 0v2M8 13h3m-3 3h8" />
    </svg>
  )
}
function IconCheck({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}
function IconArrow({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
    </svg>
  )
}

// ━━━━━━━━━━━━━━━━ LOGO ━━━━━━━━━━━━━━━━

function Logo({ light = false }: { light?: boolean }) {
  const textColor = light ? '#ffffff' : '#0f172a'
  const subColor = light ? '#94a3b8' : '#94a3b8'
  const barMain = light ? '#38bdf8' : '#0369a1'
  const barAccent = light ? '#7dd3fc' : '#0ea5e9'
  return (
    <div className="flex items-center gap-3 select-none flex-shrink-0">
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
        <rect x="2" y="23" width="6" height="11" fill={barMain} />
        <rect x="10" y="17" width="6" height="17" fill={barMain} />
        <rect x="18" y="9" width="6" height="25" fill={barMain} />
        <rect x="26" y="17" width="6" height="17" fill={barAccent} />
        <line x1="2" y1="34" x2="34" y2="34" stroke={barMain} strokeWidth="2.2" />
        <line x1="2" y1="34" x2="2" y2="23" stroke={barMain} strokeWidth="0.6" strokeOpacity="0.5" />
        <line x1="10" y1="34" x2="10" y2="17" stroke={barMain} strokeWidth="0.6" strokeOpacity="0.5" />
        <line x1="18" y1="34" x2="18" y2="9" stroke={barMain} strokeWidth="0.6" strokeOpacity="0.5" />
      </svg>
      <div>
        <div className="font-bold text-[20px] leading-none tracking-tight"
          style={{ fontFamily: "'DM Sans', sans-serif", color: textColor }}>
          VERTICAD
        </div>
        <div className="text-[8px] font-medium tracking-[0.22em] mt-0.5 uppercase"
          style={{ fontFamily: "'JetBrains Mono', monospace", color: subColor }}>
          3D Vertical Cadastre
        </div>
      </div>
    </div>
  )
}

// ━━━━━━━━━━━━━━━━ CADASTRE STAGE ILLUSTRATIONS ━━━━━━━━━━━━━━━━

const stageIllos = {
  footprint: (
    <svg viewBox="0 0 64 64" className="w-14 h-14">
      <rect width="64" height="64" fill="#EFF6FF" rx="8" />
      <polygon points="12,52 20,20 32,13 44,20 52,52"
        fill="#BFDBFE" stroke="#3B82F6" strokeWidth="2" strokeLinejoin="round" opacity="0.85" />
      <line x1="12" y1="36" x2="52" y2="36" stroke="#93C5FD" strokeWidth="0.9" strokeDasharray="3,2" />
      <line x1="32" y1="13" x2="32" y2="52" stroke="#93C5FD" strokeWidth="0.9" strokeDasharray="3,2" />
      <circle cx="32" cy="32" r="2.5" fill="#3B82F6" opacity="0.5" />
    </svg>
  ),
  building3d: (
    <svg viewBox="0 0 64 64" className="w-14 h-14">
      <rect width="64" height="64" fill="#EFF6FF" rx="8" />
      <rect x="11" y="20" width="26" height="34" fill="#E0EAF5" stroke="#3B82F6" strokeWidth="1.5" />
      <polygon points="37,20 48,14 48,48 37,54" fill="#C8D8EC" stroke="#3B82F6" strokeWidth="1.5" />
      <polygon points="11,20 22,14 48,14 37,20" fill="#D4E4F0" stroke="#3B82F6" strokeWidth="1.5" />
      {[28, 36, 44].map(y => (
        <line key={y} x1="11" y1={y} x2="37" y2={y} stroke="#93C5FD" strokeWidth="0.8" />
      ))}
    </svg>
  ),
  floor: (
    <svg viewBox="0 0 64 64" className="w-14 h-14">
      <rect width="64" height="64" fill="#EFF6FF" rx="8" />
      <rect x="12" y="12" width="40" height="40" fill="#E0EAF5" stroke="#CBD5E1" strokeWidth="1" />
      {[20, 28, 36, 44].map(y => (
        <line key={y} x1="12" y1={y} x2="52" y2={y} stroke="#CBD5E1" strokeWidth="0.8" />
      ))}
      <rect x="12" y="20" width="40" height="8" fill="#BFDBFE" opacity="0.92" />
      <line x1="12" y1="20" x2="52" y2="20" stroke="#3B82F6" strokeWidth="1.5" />
      <line x1="12" y1="28" x2="52" y2="28" stroke="#3B82F6" strokeWidth="1.5" />
    </svg>
  ),
  unit: (
    <svg viewBox="0 0 64 64" className="w-14 h-14">
      <rect width="64" height="64" fill="#EFF6FF" rx="8" />
      <rect x="7" y="18" width="50" height="28" fill="#E0EAF5" stroke="#CBD5E1" strokeWidth="1" />
      <line x1="22" y1="18" x2="22" y2="46" stroke="#CBD5E1" strokeWidth="0.8" />
      <line x1="38" y1="18" x2="38" y2="46" stroke="#CBD5E1" strokeWidth="0.8" />
      <line x1="7" y1="32" x2="57" y2="32" stroke="#CBD5E1" strokeWidth="0.8" />
      <rect x="38" y="18" width="19" height="14" fill="#BFDBFE" opacity="0.95" />
      <rect x="38" y="18" width="19" height="14" fill="none" stroke="#3B82F6" strokeWidth="1.5" />
      <text x="47.5" y="28" textAnchor="middle"
        fontFamily="'JetBrains Mono',monospace" fontSize="6" fill="#1D4ED8" fontWeight="600">B3</text>
    </svg>
  ),
  ulpin: (
    <svg viewBox="0 0 64 64" className="w-14 h-14">
      <rect width="64" height="64" fill="#EFF6FF" rx="8" />
      <rect x="7" y="16" width="50" height="30" rx="3" fill="#EFF6FF" stroke="#3B82F6" strokeWidth="1.5" />
      <rect x="7" y="16" width="50" height="10" rx="3" fill="#BFDBFE" />
      <text x="32" y="24" textAnchor="middle"
        fontFamily="'JetBrains Mono',monospace" fontSize="6.5" fontWeight="600" fill="#1D4ED8">KA-BLR-XXXX</text>
      {Array.from({ length: 8 }, (_, i) => (
        <line key={i} x1={13 + i * 5} y1="32" x2={13 + i * 5} y2="42"
          stroke="#3B82F6" strokeWidth={i % 3 === 0 ? 2 : 1} opacity="0.55" />
      ))}
      <circle cx="46" cy="43" r="6" fill="#10B981" />
      <path d="M43 43l2 2 3.5-4.5" stroke="white" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  ),
}

// ━━━━━━━━━━━━━━━━ HEADER ━━━━━━━━━━━━━━━━

function Header() {
  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 h-14 flex items-center justify-between gap-6">
        <Logo />
        <nav className="hidden md:flex items-center gap-5 lg:gap-7 flex-1">
          <a href="#footprint-to-property" onClick={e => jump(e, 'footprint-to-property')}
            className="text-sm font-medium text-slate-600 hover:text-sky-700 transition-colors">
            Explore
          </a>
          <a href="#data-validation" onClick={e => jump(e, 'data-validation')}
            className="text-sm font-medium text-slate-600 hover:text-sky-700 transition-colors">
            Data
          </a>
        </nav>
        <div className="flex items-center gap-3 lg:gap-5 flex-shrink-0">
          <a href="#how-it-works" onClick={e => jump(e, 'how-it-works')} className="hidden lg:block text-sm text-slate-500 hover:text-slate-800 transition-colors">
            Help
          </a>
          <a href={VIEWER_HREF} className="bg-sky-700 hover:bg-sky-800 text-white text-[10.5px] font-bold tracking-widest uppercase px-4 py-2 rounded transition-colors whitespace-nowrap">
            Open 3D Viewer
          </a>
        </div>
      </div>
    </header>
  )
}

// ━━━━━━━━━━━━━━━━ HERO ━━━━━━━━━━━━━━━━

function Hero() {
  const { building, validation } = useDataset()
  return (
    <section className="bg-white border-b border-slate-100">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 py-14 lg:py-20
        grid lg:grid-cols-[1fr_460px] xl:grid-cols-[1fr_520px] gap-10 xl:gap-16 items-center">

        {/* Left */}
        <div className="max-w-[560px]">
          <h1 className="text-[44px] lg:text-[54px] xl:text-[60px] font-bold text-slate-900
            leading-[1.07] mb-5 tracking-tight"
            style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Your Property.<br />In Every Dimension.
          </h1>
          <p className="text-slate-500 text-[17px] leading-relaxed mb-10 max-w-[490px]">
            Explore structured 3D cadastral information across buildings, floors and individual property units.
          </p>

          {/* Primary action — replaces the previous search interface */}
          <a
            href={VIEWER_HREF}
            className="inline-flex items-center justify-center gap-3 bg-sky-700 hover:bg-sky-800
              text-white font-bold text-[12px] tracking-[0.16em] uppercase px-8 py-4 rounded-xl
              transition-colors shadow-[0_4px_28px_-4px_rgba(3,105,161,0.28)]"
          >
            Open 3D Viewer
            <span className="text-lg leading-none">→</span>
          </a>

          <p className="mt-4 text-xs text-slate-400">
            Explore the {validation.valid ? 'validated ' : ''}{building.name} 3D cadastral model.
          </p>
        </div>

        {/* Right: Property preview */}
        <div className="hidden lg:block relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-50"
          style={{ aspectRatio: '420/500' }}>
          <img
            src={PREVIEW_IMAGE}
            alt="Modern residential property interior preview"
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/45 via-transparent to-transparent" />
          <div className="absolute top-4 left-4 bg-white/95 border border-white/80 px-3 py-2 rounded-lg shadow-sm">
            <div className="text-[9px] font-bold tracking-[0.18em] uppercase text-sky-700"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              Property preview
            </div>
            <div className="text-xs font-semibold text-slate-800 mt-0.5">Spatial data available</div>
          </div>
          <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-4">
            <div className="text-white">
              <div className="text-[10px] tracking-[0.18em] uppercase text-white/75"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                Explore the property
              </div>
              <div className="text-lg font-semibold mt-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                From place to spatial record.
              </div>
            </div>
            <a href={VIEWER_HREF} className="flex-shrink-0 bg-white/95 text-slate-900 text-[10px] font-bold px-3 py-2 rounded-lg hover:bg-white transition-colors">
              3D viewer →
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
// ━━━━━━━━━━━━━━━━ CADASTRE FLOW ━━━━━━━━━━━━━━━━

const cadastreStages = [
  { key: 'footprint' as const, label: '2D Footprint', desc: 'Base spatial geometry', sub: 'Georeferenced polygon' },
  { key: 'building3d' as const, label: '3D Building', desc: 'Reconstructed vertical structure', sub: 'Procedural extrusion' },
  { key: 'floor' as const, label: 'Floor', desc: 'Vertical decomposition', sub: 'Horizontal slice' },
  { key: 'unit' as const, label: 'Unit', desc: 'Property-level geometry', sub: 'Partitioned space' },
  { key: 'ulpin' as const, label: 'ULPIN', desc: 'Unique property identity', sub: 'Persistent identifier' },
]

function CadastreFlow() {
  return (
    <section id="footprint-to-property" className="bg-white border-b border-slate-100">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 py-16 lg:py-20">
        <div className="mb-12 text-center max-w-xl mx-auto">
          <div className="text-[10px] font-bold tracking-[0.22em] text-sky-700 uppercase mb-3"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Vertical Cadastre Explainer
          </div>
          <h2 className="text-3xl lg:text-4xl font-bold text-slate-900"
            style={{ fontFamily: "'DM Sans', sans-serif" }}>
            From Footprint to Property
          </h2>
        </div>

        <div className="flex flex-col md:flex-row items-stretch gap-0">
          {cadastreStages.flatMap((stage, i) => {
            const card = (
              <div key={stage.key} className="flex-1 bg-white border border-slate-200 rounded-xl p-6
                flex flex-col items-center text-center hover:border-sky-300 hover:shadow-sm transition-all group">
                <div className="mb-4 group-hover:scale-105 transition-transform">
                  {stageIllos[stage.key]}
                </div>
                <div className="text-[11px] font-bold text-sky-700 tracking-widest uppercase mb-2"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {String(i + 1).padStart(2, '0')}
                </div>
                <div className="font-bold text-slate-900 text-[14px] mb-1.5 leading-tight"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}>{stage.label}</div>
                <div className="text-[12.5px] text-slate-600 mb-1.5 font-medium">{stage.desc}</div>
                <div className="text-[10px] text-slate-400"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}>{stage.sub}</div>
              </div>
            )
            if (i < cadastreStages.length - 1) {
              return [
                card,
                <div key={`a${i}`} className="flex-shrink-0 flex items-center justify-center
                  w-full h-8 md:w-8 md:h-auto text-sky-300">
                  <span className="md:hidden rotate-90 md:rotate-0"><IconArrow size={20} /></span>
                  <span className="hidden md:block"><IconArrow size={20} /></span>
                </div>
              ]
            }
            return [card]
          })}
        </div>
      </div>
    </section>
  )
}

// ━━━━━━━━━━━━━━━━ DATA VALIDATION ━━━━━━━━━━━━━━━━

const validationCards = [
  {
    icon: <IconBuilding size={22} />,
    title: 'Geometry',
    status: 'Validated',
    items: ['Polygon validity checked', '3D volume computed', 'Floor boundaries verified'],
  },
  {
    icon: <IconLayers size={22} />,
    title: 'Topology',
    status: 'Overlap checked',
    items: ['No self-intersections', 'Floor–unit adjacency valid', 'Vertical stack consistent'],
  },
  {
    icon: <IconID size={22} />,
    title: 'Identifiers',
    status: 'Duplicate checked',
    items: ['ULPIN uniqueness verified', 'Building ID linked', 'Floor/unit references intact'],
  },
  {
    icon: (
      <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2z" />
      </svg>
    ),
    title: 'Provenance',
    status: 'Source traceable',
    items: ['Input source recorded', 'Processing steps logged', 'Transformation history'],
  },
]

function DataValidation() {
  return (
    <section id="data-validation" className="bg-slate-50 border-b border-slate-200">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 py-16 lg:py-20">
        <div className="mb-10">
          <div className="text-[10px] font-bold tracking-[0.22em] text-sky-700 uppercase mb-3"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Data & Validation
          </div>
          <h2 className="text-3xl lg:text-4xl font-bold text-slate-900"
            style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Built for traceable spatial data.
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {validationCards.map(card => (
            <div key={card.title}
              className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-5">
                <span className="text-sky-700">{card.icon}</span>
                <span className="flex items-center gap-1 bg-emerald-50 text-emerald-700
                  text-[9px] font-bold tracking-wide px-2.5 py-1 rounded-full border border-emerald-200"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  <IconCheck size={10} /> {card.status}
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-lg mb-4"
                style={{ fontFamily: "'DM Sans', sans-serif" }}>{card.title}</h3>
              <ul className="space-y-2">
                {card.items.map(item => (
                  <li key={item} className="flex items-start gap-2 text-sm text-slate-500">
                    <span className="text-sky-400 mt-0.5 flex-shrink-0"><IconCheck size={12} /></span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ━━━━━━━━━━━━━━━━ TECHNOLOGY PIPELINE ━━━━━━━━━━━━━━━━

type CatColor = 'blue' | 'purple' | 'green' | 'orange' | 'cyan'
const catColorMap: Record<CatColor, string> = {
  blue: 'bg-blue-100 text-blue-700 border-blue-200',
  purple: 'bg-purple-100 text-purple-700 border-purple-200',
  green: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  orange: 'bg-orange-100 text-orange-700 border-orange-200',
  cyan: 'bg-cyan-100 text-cyan-700 border-cyan-200',
}

const techSteps: { n: string; label: string; cat: string; catColor: CatColor; desc: string }[] = [
  { n: '01', label: 'Geospatial Data', cat: 'Geospatial', catColor: 'blue', desc: 'OSM, cadastral maps, satellite imagery' },
  { n: '02', label: 'Preprocessing', cat: 'Geospatial', catColor: 'blue', desc: 'Coordinate normalization, datum alignment' },
  { n: '03', label: '3D Reconstruction', cat: 'AI / ML', catColor: 'purple', desc: 'Height estimation, model inference' },
  { n: '04', label: 'Floor Decomposition', cat: 'Procedural', catColor: 'green', desc: 'Slicing by floor count and height' },
  { n: '05', label: 'Unit Partitioning', cat: 'Procedural', catColor: 'green', desc: 'Rule-based floor plan subdivision' },
  { n: '06', label: 'Property Identifier', cat: 'Rule-based', catColor: 'orange', desc: 'ULPIN prototype generation' },
  { n: '07', label: 'Validation', cat: 'Rule-based', catColor: 'orange', desc: 'Geometry, topology, identity checks' },
  { n: '08', label: '3D Cadastral View', cat: 'Visualization', catColor: 'cyan', desc: 'Interactive 3D viewer output' },
]

function TechPipeline() {
  return (
    <section id="how-it-works" className="bg-slate-50 border-b border-slate-200">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 py-16 lg:py-20">
        <div className="mb-12">
          <div className="text-[10px] font-bold tracking-[0.22em] text-sky-700 uppercase mb-3"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Technology
          </div>
          <h2 className="text-3xl lg:text-4xl font-bold text-slate-900"
            style={{ fontFamily: "'DM Sans', sans-serif" }}>
            How it works.
          </h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {techSteps.map((step, i) => (
            <div key={step.n} className="relative bg-white border border-slate-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="text-[32px] font-bold text-slate-100 mb-3 leading-none select-none"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                {step.n}
              </div>
              <span className={`inline-block text-[9px] font-bold tracking-[0.14em] uppercase
                px-2 py-1 rounded border mb-3 ${catColorMap[step.catColor]}`}
                style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                {step.cat}
              </span>
              <div className="font-bold text-slate-900 text-[13.5px] mb-1 leading-tight"
                style={{ fontFamily: "'DM Sans', sans-serif" }}>{step.label}</div>
              <div className="text-[11.5px] text-slate-400 leading-snug">{step.desc}</div>
              {/* Right arrow (not at column end) */}
              {i < techSteps.length - 1 && (i + 1) % 4 !== 0 && (
                <div className="absolute -right-3 top-1/2 -translate-y-1/2 text-slate-300 hidden md:block z-10">
                  <IconArrow size={13} />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2.5 items-center">
          <span className="text-xs text-slate-400 mr-1">Category:</span>
          {(Object.entries({ 'Geospatial': 'blue', 'AI / ML': 'purple', 'Procedural': 'green', 'Rule-based': 'orange', 'Visualization': 'cyan' }) as [string, CatColor][]).map(([cat, color]) => (
            <span key={cat}
              className={`text-[9px] font-bold tracking-wide px-2.5 py-1 rounded border ${catColorMap[color]}`}
              style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {cat}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

// ━━━━━━━━━━━━━━━━ FINAL CTA ━━━━━━━━━━━━━━━━

function FinalCTA() {
  return (
    <section className="bg-sky-700">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 py-16 lg:py-24 text-center">
        <h2 className="text-3xl lg:text-5xl font-bold text-white mb-5 leading-tight"
          style={{ fontFamily: "'DM Sans', sans-serif" }}>
          Explore property in three dimensions.
        </h2>
        <p className="text-sky-200 text-[17px] mb-10 max-w-xl mx-auto leading-relaxed">
          Search a building. Inspect its floors. Explore its property structure.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a href={VIEWER_HREF} className="bg-white hover:bg-sky-50 text-sky-800 font-bold text-[12px]
            tracking-widest uppercase py-4 px-10 rounded-lg transition-colors">
            Open 3D Viewer
          </a>
          <a href={VIEWER_HREF} className="border border-sky-400 hover:border-white text-white font-bold text-[12px]
            tracking-widest uppercase py-4 px-10 rounded-lg transition-colors">
            Explore Demo
          </a>
        </div>
      </div>
    </section>
  )
}

// ━━━━━━━━━━━━━━━━ FOOTER ━━━━━━━━━━━━━━━━

function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400">
      <div className="max-w-[1440px] mx-auto px-5 xl:px-8 py-12">
        <div className="grid md:grid-cols-[1fr_auto] gap-8 items-start mb-10">
          <div>
            <div className="mb-3">
              <Logo light />
            </div>
            <div className="text-[10px] tracking-widest text-slate-500 mb-3 mt-4"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              
            </div>
            <p className="text-sm text-slate-500 max-w-sm leading-relaxed">
              A geospatial cadastral platform for structured 3D property data, spatial discovery and traceable validation.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-12 gap-y-2.5">
            {[
              ['Explore', '#footprint-to-property'],
              ['Data', '#data-validation'],
              ['Help', '#how-it-works'],
              ['Open 3D Viewer', VIEWER_HREF],
            ].map(([link, href]) => (
              <a key={link} href={href}
                onClick={href.startsWith('#') ? e => jump(e, href.slice(1)) : undefined}
                className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                {link}
              </a>
            ))}
          </div>
        </div>
        <div className="border-t border-slate-800 pt-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="text-[10.5px] text-slate-600"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Prototype demonstration. Not legally certified cadastral data.
          </div>
          <div className="text-[10.5px] text-slate-600"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            
          </div>
        </div>
      </div>
    </footer>
  )
}

// ━━━━━━━━━━━━━━━━ APP ━━━━━━━━━━━━━━━━

export function Landing() {
  return (
    <div className="vc-landing min-h-screen bg-white">
      <Header />
      <main>
        <Hero />
        <CadastreFlow />
        <DataValidation />
        <TechPipeline />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  )
}
