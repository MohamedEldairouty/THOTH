import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { getMapOverview, getMapExhibits, getRobotStatus, getCurrentTourRun, getExhibit } from '../services/api'
import type { MapOverview, MapExhibitMarker, MapConfig, RobotStatus, ExhibitLocalized } from '../types'
import type { TourRun } from '../services/api'

/** Convert ROS world coordinates (meters) to screen percentages (0..100).
 *  ROS map convention: origin is the world coord of the PGM's bottom-left,
 *  so Y must be flipped when going to image space (PGM origin is top-left). */
function worldToPercent(wx: number, wy: number, cfg: MapConfig): { left: string; top: string } {
  const px = (wx - cfg.origin_x) / cfg.resolution           // 0 .. width_px
  const py = cfg.height_px - (wy - cfg.origin_y) / cfg.resolution
  const xPct = (px / cfg.width_px) * 100
  const yPct = (py / cfg.height_px) * 100
  return { left: `${xPct}%`, top: `${yPct}%` }
}

export default function MapPage() {
  const { lang } = useLanguage()
  const [map, setMap] = useState<MapOverview | null>(null)
  const [markers, setMarkers] = useState<MapExhibitMarker[]>([])
  const [robot, setRobot] = useState<RobotStatus | null>(null)
  const [selected, setSelected] = useState<MapExhibitMarker | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<ExhibitLocalized | null>(null)
  const [tourRun, setTourRun] = useState<TourRun | null>(null)

  // Fetch the full exhibit (image + era) whenever the user picks a marker.
  useEffect(() => {
    if (!selected) { setSelectedDetail(null); return }
    let alive = true
    getExhibit(selected.id, lang).then(ex => { if (alive) setSelectedDetail(ex) }).catch(() => {})
    return () => { alive = false }
  }, [selected?.id, lang])

  useEffect(() => {
    Promise.all([getMapOverview(), getMapExhibits(lang), getRobotStatus(), getCurrentTourRun()]).then(
      ([m, mx, r, tr]) => { setMap(m); setMarkers(mx); setRobot(r); setTourRun(tr) }
    )
    // Fast poll while watching the robot animate during navigation
    const interval = setInterval(() => {
      Promise.all([getRobotStatus(), getCurrentTourRun()]).then(
        ([r, tr]) => { setRobot(r); setTourRun(tr) }
      )
    }, 400)
    return () => clearInterval(interval)
  }, [lang])

  const inTour = tourRun?.status === 'moving' || tourRun?.status === 'arrived'
  const activeTargetId = inTour ? tourRun!.current_exhibit_id : null
  // Map exhibit_id → tour stop state ('visited' | 'current' | 'pending')
  // so we can color all markers consistently with the TourRunPage.
  const tourStateById = new Map<number, 'visited' | 'current' | 'pending'>()
  if (inTour) {
    for (const s of tourRun!.all_stops) {
      const state =
        s.sequence_order < tourRun!.current_stop_index ? 'visited'
        : s.sequence_order === tourRun!.current_stop_index ? 'current'
        : 'pending'
      tourStateById.set(s.exhibit_id, state)
    }
  }

  const cfg = map?.map_config

  return (
    <div className="max-w-7xl mx-auto px-4 py-10 animate-fade-in">
      <h1 className="gem-section-title mb-6">
        {lang === 'ar' ? 'خريطة المتحف' : lang === 'fr' ? 'Plan du Musée' : 'Museum Map'}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map canvas */}
        <div className="lg:col-span-2 gem-card p-4">
          <div className="relative w-full aspect-[17/8] bg-gem-dark rounded-xl overflow-hidden border border-gem-gold/20">

            {/* Real museum map (themed from ROS Nav2 occupancy grid) */}
            <img
              src="/assets/museum_map.png"
              alt="Museum floor plan"
              className="absolute inset-0 w-full h-full object-contain select-none pointer-events-none"
              draggable={false}
            />

            {/* Subtle grid overlay on top of the map */}
            <svg className="absolute inset-0 w-full h-full opacity-[0.06] pointer-events-none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid" width="10%" height="10%" patternUnits="objectBoundingBox">
                  <path d="M 0 0 L 100 0 L 100 100 L 0 100 Z" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            {/* Exhibit markers. When a tour is active:
                  visited  = dim gold w/ check
                  current  = bright gold + pulse ring + sequence label
                  pending  = navy w/ gold sequence label
                Outside a tour: standard gold dots. */}
            {cfg && markers.map(m => {
              const pos = worldToPercent(m.x, m.y, cfg)
              const tourState = tourStateById.get(m.id)
              const isTarget = m.id === activeTargetId
              const seq = inTour
                ? (tourRun!.all_stops.find(s => s.exhibit_id === m.id)?.sequence_order ?? -1) + 1
                : 0

              // Default (no tour) → simple gold dot
              if (!inTour) {
                return (
                  <button
                    key={m.id}
                    onClick={() => setSelected(m)}
                    style={pos}
                    className="absolute -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-gem-gold border-2 border-gem-navy hover:scale-150 transition-transform z-10 shadow-[0_0_8px_rgba(201,168,76,0.6)]"
                    title={m.title}
                  />
                )
              }

              // Tour-aware rendering
              return (
                <div key={m.id} style={pos} className="absolute -translate-x-1/2 -translate-y-1/2 z-10">
                  {isTarget && (
                    <div className="absolute -inset-2.5 rounded-full border-2 border-gem-gold animate-ping pointer-events-none" />
                  )}
                  <button
                    onClick={() => setSelected(m)}
                    className={
                      tourState === 'current'
                        ? 'relative w-7 h-7 rounded-full bg-gem-gold border-2 border-gem-navy text-gem-navy text-[10px] font-bold flex items-center justify-center hover:scale-110 transition-transform shadow-[0_0_16px_rgba(201,168,76,0.95)]'
                      : tourState === 'visited'
                        ? 'relative w-5 h-5 rounded-full bg-gem-gold/30 border border-gem-gold/60 text-gem-gold text-[10px] font-bold flex items-center justify-center hover:scale-125 transition-transform'
                      : tourState === 'pending'
                        ? 'relative w-5 h-5 rounded-full bg-gem-navy border border-gem-gold/60 text-gem-gold/80 text-[10px] font-bold flex items-center justify-center hover:scale-125 transition-transform'
                      : 'relative w-4 h-4 rounded-full bg-gem-gold/40 border border-gem-gold/40 hover:scale-150 transition-transform'
                    }
                    title={`${m.title}${tourState ? ' (' + tourState + ')' : ' (not in current tour)'}`}
                  >
                    {tourState === 'visited' ? '✓' : tourState ? seq : ''}
                  </button>
                </div>
              )
            })}

            {/* Robot position — also in world meters */}
            {cfg && robot && (
              <div
                style={{
                  ...worldToPercent(robot.current_x, robot.current_y, cfg),
                  transition: "left 400ms linear, top 400ms linear",
                }}
                className="absolute -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-blue-400 border-2 border-white z-20 animate-pulse shadow-[0_0_12px_rgba(96,165,250,0.8)]"
                title={`THOTH (${robot.current_x.toFixed(1)} m, ${robot.current_y.toFixed(1)} m)`}
              />
            )}

            <p className="absolute bottom-2 right-3 text-xs text-gem-muted bg-gem-navy/70 px-2 py-1 rounded">
              {lang === 'ar' ? 'نقاط ذهبية = معروضات | نقطة زرقاء = الروبوت' :
               lang === 'fr' ? 'Points dorés = expositions | Point bleu = robot' :
               'Gold = exhibits · Blue = robot'}
            </p>
          </div>
        </div>

        {/* Sidebar */}
        <div className="flex flex-col gap-4">
          {/* Selected exhibit */}
          {selected ? (
            <div className="gem-card overflow-hidden">
              {/* Thumbnail (like tour cards) */}
              <div className="h-40 bg-gem-dark">
                {selectedDetail?.image_url ? (
                  <img
                    src={selectedDetail.image_url}
                    alt={selected.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-5xl text-gem-gold/20">𓅓</div>
                )}
              </div>
              <div className="p-4">
                <h3 className="font-display text-gem-gold text-base mb-2">{selected.title}</h3>
                {selectedDetail?.era && (
                  <span className="inline-block text-xs text-gem-muted border border-gem-gold/30 px-2 py-0.5 rounded-full mb-3">
                    {selectedDetail.era}
                  </span>
                )}
                <Link to={`/exhibits/${selected.id}`} className="gem-btn-primary w-full block text-center text-sm py-2 mt-1">
                  {lang === 'ar' ? 'عرض التفاصيل' : lang === 'fr' ? 'Voir détails' : 'View Details'}
                </Link>
              </div>
            </div>
          ) : (
            <div className="gem-card p-4 text-gem-muted text-sm text-center">
              {lang === 'ar' ? 'انقر على نقطة لعرض معرض' :
               lang === 'fr' ? 'Cliquez sur un point pour voir une exposition' :
               'Click a marker to select an exhibit'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
