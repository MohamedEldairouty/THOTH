import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { getMapOverview, getMapExhibits, getRobotStatus, stopNavigation } from '../services/api'
import type { MapOverview, MapExhibitMarker, MapConfig, RobotStatus } from '../types'

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

  useEffect(() => {
    Promise.all([getMapOverview(), getMapExhibits(lang), getRobotStatus()]).then(
      ([m, mx, r]) => { setMap(m); setMarkers(mx); setRobot(r) }
    )
    // Fast poll while watching the robot animate during navigation
    const interval = setInterval(() => {
      getRobotStatus().then(setRobot)
    }, 400)
    return () => clearInterval(interval)
  }, [lang])

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

            {/* Exhibit markers — positions are in WORLD meters in the DB */}
            {cfg && markers.map(m => {
              const pos = worldToPercent(m.x, m.y, cfg)
              return (
                <button
                  key={m.id}
                  onClick={() => setSelected(m)}
                  style={pos}
                  className="absolute -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-gem-gold border-2 border-gem-navy hover:scale-150 transition-transform z-10 shadow-[0_0_8px_rgba(201,168,76,0.6)]"
                  title={`${m.title}  (${m.x.toFixed(1)} m, ${m.y.toFixed(1)} m)`}
                />
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
          {/* Robot status card */}
          {robot && (
            <div className="gem-card p-4">
              <h3 className="font-display text-gem-gold text-sm mb-3">
                {lang === 'ar' ? 'حالة الروبوت' : lang === 'fr' ? 'État du robot' : 'Robot Status'}
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gem-muted">Status</span>
                  <span className={`font-medium capitalize ${robot.status === 'navigating' ? 'text-green-400' : 'text-gem-text'}`}>
                    {robot.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gem-muted">Battery</span>
                  <span className="text-gem-text">{robot.battery.toFixed(0)}%</span>
                </div>
              </div>
              {robot.status === 'navigating' && (
                <button
                  onClick={() => stopNavigation().then(() => getRobotStatus().then(setRobot))}
                  className="gem-btn-ghost w-full mt-3 text-sm py-2"
                >
                  {lang === 'ar' ? 'إيقاف التنقل' : lang === 'fr' ? 'Arrêter' : 'Stop Navigation'}
                </button>
              )}
            </div>
          )}

          {/* Selected exhibit */}
          {selected ? (
            <div className="gem-card p-4">
              <h3 className="font-display text-gem-gold text-sm mb-2">{selected.title}</h3>
              <p className="text-gem-muted text-xs mb-3">
                {lang === 'ar' ? 'القاعة' : lang === 'fr' ? 'Salle' : 'Hall'} {selected.hall_id}
              </p>
              <Link to={`/exhibits/${selected.id}`} className="gem-btn-primary w-full block text-center text-sm py-2">
                {lang === 'ar' ? 'عرض التفاصيل' : lang === 'fr' ? 'Voir détails' : 'View Details'}
              </Link>
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
