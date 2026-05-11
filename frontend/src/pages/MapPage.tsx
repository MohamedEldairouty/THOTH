import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { getMapOverview, getMapExhibits, getRobotStatus, stopNavigation } from '../services/api'
import type { MapOverview, MapExhibitMarker, RobotStatus } from '../types'

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
    const interval = setInterval(() => {
      getRobotStatus().then(setRobot)
    }, 5000)
    return () => clearInterval(interval)
  }, [lang])

  return (
    <div className="max-w-7xl mx-auto px-4 py-10 animate-fade-in">
      <h1 className="gem-section-title mb-6">
        {lang === 'ar' ? 'خريطة المتحف' : lang === 'fr' ? 'Plan du Musée' : 'Museum Map'}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map canvas */}
        <div className="lg:col-span-2 gem-card p-4">
          <div className="relative w-full aspect-[4/3] bg-gem-dark rounded-xl overflow-hidden border border-gem-gold/10">
            {/* Grid lines */}
            <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid" width="10%" height="10%" patternUnits="objectBoundingBox">
                  <path d="M 0 0 L 100 0 L 100 100 L 0 100 Z" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            {/* Exhibit markers */}
            {markers.map(m => (
              <button
                key={m.id}
                onClick={() => setSelected(m)}
                style={{ left: `${m.x}%`, top: `${m.y}%` }}
                className="absolute -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-gem-gold border-2 border-gem-navy hover:scale-150 transition-transform z-10"
                title={m.title}
              />
            ))}

            {/* Robot position */}
            {robot && (
              <div
                style={{ left: `${robot.current_x}%`, top: `${robot.current_y}%` }}
                className="absolute -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-blue-400 border-2 border-white z-20 animate-pulse"
                title="THOTH Robot"
              />
            )}

            <p className="absolute bottom-2 right-3 text-xs text-gem-muted">
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
