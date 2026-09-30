const VIEWER_URL = import.meta.env.VITE_VIEWER_URL || 'http://localhost:5174'

// ━━━━━━━━━━━━━━━━ ICONS ━━━━━━━━━━━━━━━━

function IconSearch({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <circle cx="11" cy="11" r="8" /><path strokeLinecap="round" d="m21 21-4.35-4.35" />
    </svg>
  )
}
function IconBuilding({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2 21h20M4 21V8l8-5 8 5v13M9 21v-8h6v8" />
    </svg>
  )
}
function IconMap({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 20 4 22V6l5-2m0 16 6-3M9 4l6 3m0 13 5 2V9l-5-2" />
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

// ━━━━━━━━━━━━━━━━ BUILDING SVG ━━━━━━━━━━━━━━━━

function BuildingCadastralSVG() {
  const FH = 7.8 // floor height px
  const FC = 34
  const BH = FC * FH   // ≈264.6
  const BW = 136
  const DX = 48
  const DY = -26

  const L = 72
  const B = 446
  const T = B - BH  // ≈181
  const R = L + BW  // 208

  const HL = 33 // 0-indexed from bottom (top floor)
  const wCols = [L + 9, L + 42, L + 75, L + 108]
  const wW = 23

  return (
    <svg viewBox="0 0 420 500" className="w-full h-full" style={{ display: 'block' }}>
      <defs>
        <pattern id="bsvg-g1" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0L0 0 0 20" fill="none" stroke="#CBD5E1" strokeWidth="0.4" />
        </pattern>
        <pattern id="bsvg-g2" width="80" height="80" patternUnits="userSpaceOnUse">
          <path d="M80 0L0 0 0 80" fill="none" stroke="#94A3B8" strokeWidth="0.65" />
        </pattern>
      </defs>

      {/* Map base */}
      <rect width="420" height="500" fill="#F1F5F9" />
      <rect width="420" height="500" fill="url(#bsvg-g1)" />
      <rect width="420" height="500" fill="url(#bsvg-g2)" />

      {/* Roads */}
      <rect x="0" y="455" width="420" height="15" fill="#E2E8F0" opacity="0.9" />
      <rect x="285" y="0" width="14" height="455" fill="#E2E8F0" opacity="0.9" />

      {/* Neighboring building footprints */}
      <rect x="16" y="362" width="52" height="76" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" rx="1" opacity="0.6" />
      <rect x="310" y="378" width="56" height="54" fill="#EDE9FE" stroke="#C4B5FD" strokeWidth="1" rx="1" opacity="0.6" />
      <rect x="16" y="278" width="42" height="72" fill="#E0E7FF" stroke="#A5B4FC" strokeWidth="1" rx="1" opacity="0.5" />
      <rect x="312" y="290" width="46" height="78" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" rx="1" opacity="0.5" />
      <rect x="346" y="195" width="36" height="88" fill="#E0E7FF" stroke="#A5B4FC" strokeWidth="1" rx="1" opacity="0.4" />

      {/* Main footprint highlight */}
      <rect x={L - 2} y={B + 2} width={BW + DX + 4} height="22"
        fill="#BFDBFE" stroke="#3B82F6" strokeWidth="1.5" rx="1" opacity="0.75" />

      {/* ── 3D BUILDING ── */}
      {/* Top face */}
      <polygon
        points={`${L},${T} ${R},${T} ${R + DX},${T + DY} ${L + DX},${T + DY}`}
        fill="#BED0DF" stroke="#8BA8BA" strokeWidth="0.7"
      />
      {/* Right side face */}
      <polygon
        points={`${R},${T} ${R + DX},${T + DY} ${R + DX},${B + DY} ${R},${B}`}
        fill="#B4C8D8" stroke="#8BA8BA" strokeWidth="0.7"
      />
      {/* Side face floor lines */}
      {Array.from({ length: FC + 1 }, (_, i) => {
        const yF = B - i * FH
        const isHL = i === HL
        return (
          <line key={i}
            x1={R} y1={yF}
            x2={R + DX} y2={yF + DY}
            stroke={isHL ? "#60A5FA" : "#9BB5C5"}
            strokeWidth={isHL ? "0.8" : "0.35"}
            opacity={isHL ? 1 : 0.5}
          />
        )
      })}

      {/* Front face base */}
      <rect x={L} y={T} width={BW} height={BH} fill="#EDF2F8" stroke="#8BA8BA" strokeWidth="0.7" />

      {/* Floor bands + windows */}
      {Array.from({ length: FC }, (_, i) => {
        const yBot = B - i * FH
        const yTop = yBot - FH
        const isHL = i === HL
        return (
          <g key={i}>
            {isHL && <rect x={L} y={yTop} width={BW} height={FH} fill="#BFDBFE" opacity="0.92" />}
            <line x1={L} y1={yBot} x2={R} y2={yBot}
              stroke={isHL ? "#3B82F6" : "#C4D4E2"}
              strokeWidth={isHL ? "1" : "0.35"}
            />
            {wCols.map((wx, wi) => (
              <rect key={wi}
                x={wx} y={yTop + 1.4} width={wW} height={FH - 2.8}
                fill={isHL ? "#93C5FD" : "#DDE8F2"}
                stroke={isHL ? "#60A5FA" : "#C0D2E0"}
                strokeWidth="0.25"
                opacity="0.85"
              />
            ))}
          </g>
        )
      })}

      {/* Annotation: highlighted floor */}
      {(() => {
        const yHL = B - HL * FH - FH / 2
        return (
          <>
            <line x1={R} y1={yHL} x2={R + 74} y2={yHL - 52}
              stroke="#3B82F6" strokeWidth="0.8" strokeDasharray="4,3" />
            <circle cx={R} cy={yHL} r="3.5" fill="#3B82F6" />
            <rect x={R + 78} y={yHL - 74} width="112" height="58" rx="4"
              fill="white" stroke="#CBD5E1" strokeWidth="0.7"
              style={{ filter: 'drop-shadow(0 1px 4px rgba(0,0,0,0.08))' }} />
            <text x={R + 86} y={yHL - 56}
              fontFamily="'JetBrains Mono',monospace" fontSize="8" fontWeight="600" fill="#0F172A">
              Floor 34 · Unit B-3402
            </text>
            <text x={R + 86} y={yHL - 42}
              fontFamily="'JetBrains Mono',monospace" fontSize="7" fill="#2563EB">
              ULPIN: KA-BLR-XXXX-XXXX
            </text>
            <text x={R + 86} y={yHL - 28}
              fontFamily="'JetBrains Mono',monospace" fontSize="6.8" fill="#10B981">
              ✓ Geometry: Validated
            </text>
          </>
        )
      })()}

      {/* Scale bar */}
      <g transform="translate(16,472)">
        <line x1="0" y1="0" x2="44" y2="0" stroke="#64748B" strokeWidth="1.5" />
        <line x1="0" y1="-3" x2="0" y2="3" stroke="#64748B" strokeWidth="1.5" />
        <line x1="44" y1="-3" x2="44" y2="3" stroke="#64748B" strokeWidth="1.5" />
        <text x="22" y="-6" textAnchor="middle"
          fontFamily="'JetBrains Mono',monospace" fontSize="7" fill="#64748B">50 m</text>
      </g>

      {/* Coordinates */}
      <text x="404" y="488" textAnchor="end"
        fontFamily="'JetBrains Mono',monospace" fontSize="6.5" fill="#94A3B8">
        12.9716°N  77.5946°E
      </text>

      {/* North arrow */}
      <g transform="translate(388,28)">
        <circle cx="0" cy="0" r="18" fill="white" stroke="#CBD5E1" strokeWidth="1" opacity="0.95" />
        <polygon points="0,-12 -4,6 0,3 4,6" fill="#0369A1" />
        <text x="0" y="19" textAnchor="middle"
          fontFamily="'DM Sans',sans-serif" fontSize="9" fontWeight="700" fill="#475569">N</text>
      </g>

      {/* Layer badge */}
      <rect x="12" y="12" width="110" height="19" rx="3" fill="#0369A1" />
      <text x="67" y="24.5" textAnchor="middle"
        fontFamily="'JetBrains Mono',monospace" fontSize="7.5" fontWeight="600" fill="white" letterSpacing="1.2">
        CADASTRAL VIEW
      </text>
    </svg>
  )
}

// ━━━━━━━━━━━━━━━━ MINI MAP SVG ━━━━━━━━━━━━━━━━

function MiniMapSVG() {
  return (
    <svg viewBox="0 0 280 340" className="w-full h-full" style={{ display: 'block' }}>
      <defs>
        <pattern id="mm-g1" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0L0 0 0 20" fill="none" stroke="#CBD5E1" strokeWidth="0.4" />
        </pattern>
      </defs>
      <rect width="280" height="340" fill="#F1F5F9" />
      <rect width="280" height="340" fill="url(#mm-g1)" />
      {/* Roads */}
      <rect x="0" y="210" width="280" height="10" fill="#E2E8F0" opacity="0.9" />
      <rect x="182" y="0" width="10" height="210" fill="#E2E8F0" opacity="0.9" />
      {/* Nearby footprints */}
      <rect x="18" y="145" width="44" height="56" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" rx="1" opacity="0.7" />
      <rect x="68" y="158" width="32" height="44" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" rx="1" opacity="0.7" />
      <rect x="200" y="148" width="52" height="52" fill="#E0E7FF" stroke="#A5B4FC" strokeWidth="1" rx="1" opacity="0.65" />
      <rect x="200" y="58" width="44" height="78" fill="#E0E7FF" stroke="#A5B4FC" strokeWidth="1" rx="1" opacity="0.55" />
      <rect x="18" y="58" width="36" height="82" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" rx="1" opacity="0.6" />
      {/* Main building highlighted */}
      <rect x="82" y="48" width="82" height="98" fill="#BFDBFE" stroke="#3B82F6" strokeWidth="2" rx="2" />
      {[64, 72, 80, 88, 96, 104, 112, 120, 128].map(y => (
        <line key={y} x1="82" y1={y} x2="164" y2={y} stroke="#93C5FD" strokeWidth="0.5" />
      ))}
      {/* Label */}
      <rect x="84" y="28" width="78" height="16" rx="2" fill="#0369A1" />
      <text x="123" y="39" textAnchor="middle" fontFamily="'JetBrains Mono',monospace" fontSize="7" fontWeight="600" fill="white">
        KF TOWERS
      </text>
      {/* Below road */}
      <rect x="18" y="228" width="52" height="40" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" rx="1" opacity="0.6" />
      <rect x="80" y="228" width="82" height="44" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" rx="1" opacity="0.5" />
      <rect x="198" y="228" width="64" height="40" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" rx="1" opacity="0.5" />
      {/* Controls */}
      <rect x="244" y="136" width="28" height="56" rx="4" fill="white" stroke="#CBD5E1" strokeWidth="1" />
      <text x="258" y="158" textAnchor="middle" fontSize="16" fill="#475569">+</text>
      <line x1="248" y1="166" x2="268" y2="166" stroke="#CBD5E1" strokeWidth="1" />
      <text x="258" y="184" textAnchor="middle" fontSize="16" fill="#475569">−</text>
      {/* Compass */}
      <circle cx="258" cy="30" r="15" fill="white" stroke="#CBD5E1" strokeWidth="1" />
      <polygon points="258,18 254,30 258,27 262,30" fill="#0369A1" />
      <text x="258" y="42" textAnchor="middle" fontFamily="'DM Sans',sans-serif" fontSize="8" fontWeight="700" fill="#475569">N</text>
    </svg>
  )
}

// ━━━━━━━━━━━━━━━━ EXPLORATION MAP SVG ━━━━━━━━━━━━━━━━

function ExplorationMapSVG() {
  return (
    <svg viewBox="0 0 880 360" className="w-full h-full" style={{ display: 'block' }}>
      <defs>
        <pattern id="em-g1" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M24 0L0 0 0 24" fill="none" stroke="#CBD5E1" strokeWidth="0.4" />
        </pattern>
        <pattern id="em-g2" width="96" height="96" patternUnits="userSpaceOnUse">
          <path d="M96 0L0 0 0 96" fill="none" stroke="#94A3B8" strokeWidth="0.6" />
        </pattern>
      </defs>
      <rect width="880" height="360" fill="#EFF4F9" />
      <rect width="880" height="360" fill="url(#em-g1)" />
      <rect width="880" height="360" fill="url(#em-g2)" />

      {/* Major roads */}
      <rect x="0" y="176" width="880" height="14" fill="#E2E8F0" opacity="0.9" />
      <rect x="0" y="278" width="880" height="10" fill="#E2E8F0" opacity="0.8" />
      <rect x="282" y="0" width="14" height="360" fill="#E2E8F0" opacity="0.9" />
      <rect x="560" y="0" width="14" height="360" fill="#E2E8F0" opacity="0.8" />
      <rect x="440" y="0" width="10" height="360" fill="#E2E8F0" opacity="0.65" />
      <line x1="0" y1="360" x2="310" y2="0" stroke="#E2E8F0" strokeWidth="10" opacity="0.7" />

      {/* Cluster A — west area */}
      {[
        [48, 38, 52, 62], [108, 46, 36, 52], [48, 110, 82, 48],
        [156, 38, 58, 36], [156, 84, 42, 72],
      ].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h}
          fill="#E0E7FF" stroke="#A5B4FC" strokeWidth="0.8" rx="1" opacity="0.75" />
      ))}

      {/* Cluster B — demonstration building (Indiranagar) */}
      <rect x="328" y="55" width="86" height="104"
        fill="#BFDBFE" stroke="#3B82F6" strokeWidth="2" rx="2" />
      {[73, 84, 95, 106, 117, 128, 139].map(y => (
        <line key={y} x1="328" y1={y} x2="414" y2={y} stroke="#93C5FD" strokeWidth="0.6" />
      ))}
      <rect x="330" y="34" width="82" height="18" rx="3" fill="#0369A1" />
      <text x="371" y="46" textAnchor="middle"
        fontFamily="'JetBrains Mono',monospace" fontSize="7.5" fontWeight="600" fill="white">
        DEMO · VALIDATED
      </text>

      {/* Cluster C — centre */}
      {[
        [488, 28, 46, 58], [542, 36, 36, 44], [488, 96, 94, 68], [472, 28, 14, 136],
      ].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h}
          fill="#DBEAFE" stroke="#93C5FD" strokeWidth="0.8" rx="1" opacity="0.7" />
      ))}

      {/* Cluster D — right area */}
      {[
        [616, 46, 56, 72], [682, 58, 42, 56], [616, 128, 104, 48], [742, 46, 52, 126], [800, 56, 68, 106],
      ].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h}
          fill="#E0E7FF" stroke="#A5B4FC" strokeWidth="0.8" rx="1" opacity="0.65" />
      ))}

      {/* Cluster E — bottom sections */}
      {[
        [78, 210, 62, 52], [148, 220, 48, 44], [78, 270, 114, 62],
        [200, 268, 54, 48], [262, 218, 42, 104],
      ].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h}
          fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="0.8" rx="1" opacity="0.7" />
      ))}
      {[
        [596, 214, 82, 56], [688, 220, 58, 46], [596, 280, 68, 56],
        [672, 280, 54, 48], [738, 208, 104, 124], [850, 214, 30, 84],
      ].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h}
          fill="#DBEAFE" stroke="#93C5FD" strokeWidth="0.8" rx="1" opacity="0.6" />
      ))}

      {/* District labels */}
      {[
        [130, 172, 'CENTRAL BENGALURU'],
        [400, 172, 'INDIRANAGAR'],
        [660, 172, 'WHITEFIELD'],
      ].map(([x, y, label]) => (
        <text key={label as string} x={x as number} y={y as number} textAnchor="middle"
          fontFamily="'DM Sans',sans-serif" fontSize="10" fontWeight="600"
          fill="#64748B" opacity="0.6" letterSpacing="0.5">
          {label}
        </text>
      ))}

      {/* Demo location pin */}
      <circle cx="371" cy="107" r="12" fill="#0369A1" opacity="0.15" />
      <circle cx="371" cy="107" r="7" fill="#0369A1" opacity="0.9" />
      <circle cx="371" cy="107" r="3.5" fill="white" />

      {/* Floating search */}
      <rect x="18" y="322" width="306" height="30" rx="6" fill="white" stroke="#CBD5E1" strokeWidth="1"
        style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.08))' }} />
      <circle cx="34" cy="337" r="6" fill="none" stroke="#94A3B8" strokeWidth="1.3" />
      <line x1="38.2" y1="341.3" x2="41" y2="344" stroke="#94A3B8" strokeWidth="1.3" strokeLinecap="round" />
      <text x="50" y="342" fontFamily="'JetBrains Mono',monospace" fontSize="9" fill="#94A3B8">
        Search locality or ULPIN...
      </text>
    </svg>
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
          <a href="#footprint-to-property"
            className="text-sm font-medium text-slate-600 hover:text-sky-700 transition-colors">
            Explore
          </a>
          <a href="#data-validation"
            className="text-sm font-medium text-slate-600 hover:text-sky-700 transition-colors">
            Data
          </a>
        </nav>
        <div className="flex items-center gap-3 lg:gap-5 flex-shrink-0">
          <a href="#how-it-works" className="hidden lg:block text-sm text-slate-500 hover:text-slate-800 transition-colors">
            Help
          </a>
          <a href={VIEWER_URL} className="bg-sky-700 hover:bg-sky-800 text-white text-[10.5px] font-bold tracking-widest uppercase px-4 py-2 rounded transition-colors whitespace-nowrap">
            Open 3D Viewer
          </a>
        </div>
      </div>
    </header>
  )
}

// ━━━━━━━━━━━━━━━━ HERO ━━━━━━━━━━━━━━━━

function Hero() {
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
            href={VIEWER_URL}
            className="inline-flex items-center justify-center gap-3 bg-sky-700 hover:bg-sky-800
              text-white font-bold text-[12px] tracking-[0.16em] uppercase px-8 py-4 rounded-xl
              transition-colors shadow-[0_4px_28px_-4px_rgba(3,105,161,0.28)]"
          >
            Open 3D Viewer
            <span className="text-lg leading-none">→</span>
          </a>

          <p className="mt-4 text-xs text-slate-400">
            Explore the validated Kingfisher Towers 3D cadastral model.
          </p>
        </div>

        {/* Right: Property preview */}
        <div className="hidden lg:block relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-50"
          style={{ aspectRatio: '420/500' }}>
          <img
            src="/images/property-preview.png"
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
            <a href={VIEWER_URL} className="flex-shrink-0 bg-white/95 text-slate-900 text-[10px] font-bold px-3 py-2 rounded-lg hover:bg-white transition-colors">
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
          <a href={VIEWER_URL} className="bg-white hover:bg-sky-50 text-sky-800 font-bold text-[12px]
            tracking-widest uppercase py-4 px-10 rounded-lg transition-colors">
            Open 3D Viewer
          </a>
          <a href={VIEWER_URL} className="border border-sky-400 hover:border-white text-white font-bold text-[12px]
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
              ['Open 3D Viewer', VIEWER_URL],
            ].map(([link, href]) => (
              <a key={link} href={href}
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

export default function App() {
  return (
    <div className="min-h-screen bg-white">
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
