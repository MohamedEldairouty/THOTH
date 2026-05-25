import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import clsx from 'clsx'
import { useLanguage } from '../hooks/useLanguage'
import {
  getCurrentTourRun, advanceTour, cancelTour,
  getMapOverview, getRobotStatus,
  type TourRun, type MapOverview as MapOv,
} from '../services/api'
import type { RobotStatus, MapConfig } from '../types'

const T = {
  en: {
    none: 'No active tour. Pick one from Start Tour.',
    start: 'Start a Tour',
    heading: 'Heading to',
    arrived: 'Arrived at',
    next: 'Up next',
    final: 'Final exhibit',
    continueBtn: 'Continue to next exhibit',
    finishBtn: 'Finish tour',
    movingMsg: 'THOTH is on the way. Please wait here.',
    arrivedMsg: 'You\'ve arrived. Take a moment, then ask THOTH about this exhibit.',
    ask: 'Ask THOTH about this exhibit',
    cancel: 'Cancel tour',
    cancelled: 'Tour cancelled.',
    completed: 'Tour complete. Thank you!',
    backTour: 'Pick another tour',
  },
  ar: {
    none: 'لا توجد جولة نشطة. اختر واحدة من ابدأ الجولة.',
    start: 'ابدأ جولة',
    heading: 'متجه إلى',
    arrived: 'وصلنا إلى',
    next: 'التالي',
    final: 'المعروض الأخير',
    continueBtn: 'الانتقال إلى المعروض التالي',
    finishBtn: 'إنهاء الجولة',
    movingMsg: 'تحوت في الطريق. يرجى الانتظار هنا.',
    arrivedMsg: 'لقد وصلت. خذ لحظة، ثم اسأل تحوت عن هذا المعروض.',
    ask: 'اسأل تحوت عن هذا المعروض',
    cancel: 'إلغاء الجولة',
    cancelled: 'تم إلغاء الجولة.',
    completed: 'اكتملت الجولة. شكراً لك!',
    backTour: 'اختر جولة أخرى',
  },
  fr: {
    none: 'Aucune visite active. Choisissez-en une depuis Commencer la visite.',
    start: 'Commencer une visite',
    heading: 'En route vers',
    arrived: 'Arrivé à',
    next: 'Prochain',
    final: 'Dernière exposition',
    continueBtn: 'Continuer vers la prochaine exposition',
    finishBtn: 'Terminer la visite',
    movingMsg: 'THOTH est en route. Veuillez attendre ici.',
    arrivedMsg: 'Vous êtes arrivé. Prenez un moment, puis demandez à THOTH.',
    ask: 'Demander à THOTH',
    cancel: 'Annuler la visite',
    cancelled: 'Visite annulée.',
    completed: 'Visite terminée. Merci !',
    backTour: 'Choisir une autre visite',
  },
}

function worldToPercent(wx: number, wy: number, cfg: MapConfig) {
  const px = (wx - cfg.origin_x) / cfg.resolution
  const py = cfg.height_px - (wy - cfg.origin_y) / cfg.resolution
  return { left: `${(px / cfg.width_px) * 100}%`, top: `${(py / cfg.height_px) * 100}%` }
}

export default function TourRunPage() {
  const { lang } = useLanguage()
  const t = T[lang]
  const nav = useNavigate()

  const [run, setRun] = useState<TourRun | null | undefined>(undefined)
  const [map, setMap] = useState<MapOv | null>(null)
  const [robot, setRobot] = useState<RobotStatus | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { getMapOverview().then(setMap) }, [])

  // Poll tour state + robot position every 600ms
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const [r, p] = await Promise.all([getCurrentTourRun(), getRobotStatus()])
        if (!alive) return
        setRun(r)
        setRobot(p)
      } catch { /* ignore */ }
    }
    tick()
    const id = setInterval(tick, 600)
    return () => { alive = false; clearInterval(id) }
  }, [])

  const handleContinue = async () => {
    if (!run) return
    setBusy(true)
    try {
      const r = await advanceTour(run.id)
      setRun(r)
    } finally { setBusy(false) }
  }

  const handleCancel = async () => {
    if (!run) return
    setBusy(true)
    try {
      await cancelTour(run.id)
      nav('/tour')
    } finally { setBusy(false) }
  }

  if (run === undefined) {
    return <div className="text-center text-gem-muted py-20">…</div>
  }
  if (run === null) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <p className="text-gem-text mb-6">{t.none}</p>
        <Link to="/tour" className="gem-btn-primary">{t.start}</Link>
      </div>
    )
  }

  const isFinal = run.current_stop_index + 1 >= run.total_stops
  const cfg = map?.map_config

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 animate-fade-in">
      {/* Header: progress + tour name */}
      <div className="flex items-end justify-between mb-4 flex-wrap gap-2">
        <div>
          <div className="text-gem-muted text-xs uppercase tracking-wider mb-1">{run.tour_name}</div>
          <h1 className="font-display text-gem-gold text-2xl">
            {run.status === 'arrived' ? t.arrived : t.heading}{' '}
            <span className="text-gem-text">{run.current_exhibit_title}</span>
          </h1>
        </div>
        <div className="text-gem-muted text-sm">
          {run.current_stop_index + 1} / {run.total_stops}
        </div>
      </div>

      {/* Progress dots */}
      <div className="flex gap-1.5 mb-6">
        {Array.from({ length: run.total_stops }, (_, i) => (
          <div
            key={i}
            className={clsx(
              'h-1.5 flex-1 rounded-full',
              i < run.current_stop_index ? 'bg-gem-gold' :
              i === run.current_stop_index ? (run.status === 'arrived' ? 'bg-gem-gold' : 'bg-gem-gold/40 animate-pulse')
              : 'bg-gem-gold/15'
            )}
          />
        ))}
      </div>

      {(run.status === 'completed' || run.status === 'cancelled') && (
        <div className="gem-card p-8 text-center">
          <div className="text-gem-gold text-4xl mb-2">𓅓</div>
          <h2 className="font-display text-gem-gold text-xl mb-2">
            {run.status === 'completed' ? t.completed : t.cancelled}
          </h2>
          <Link to="/tour" className="gem-btn-primary inline-block mt-4">{t.backTour}</Link>
        </div>
      )}

      {(run.status === 'moving' || run.status === 'arrived' || run.status === 'pending') && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* LEFT: Map with route preview */}
          <div className="lg:col-span-2 gem-card p-4">
            <div className="relative w-full aspect-[17/8] bg-gem-dark rounded-xl overflow-hidden border border-gem-gold/20">
              <img
                src="/assets/museum_map.png"
                alt="Map"
                className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                draggable={false}
              />
              {/* Target marker */}
              {cfg && run.target_x != null && run.target_y != null && (
                <div
                  style={worldToPercent(run.target_x, run.target_y, cfg)}
                  className="absolute -translate-x-1/2 -translate-y-1/2 w-7 h-7 rounded-full border-2 border-gem-gold animate-ping"
                />
              )}
              {cfg && run.target_x != null && run.target_y != null && (
                <div
                  style={worldToPercent(run.target_x, run.target_y, cfg)}
                  className="absolute -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-gem-gold border-2 border-gem-navy shadow-[0_0_8px_rgba(201,168,76,0.7)] z-10"
                />
              )}
              {/* Robot dot */}
              {cfg && robot && (
                <div
                  style={{
                    ...worldToPercent(robot.current_x, robot.current_y, cfg),
                    transition: 'left 600ms linear, top 600ms linear',
                  }}
                  className="absolute -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-blue-400 border-2 border-white animate-pulse shadow-[0_0_12px_rgba(96,165,250,0.8)] z-20"
                />
              )}
            </div>
            <p className="text-gem-muted text-xs mt-2 text-center">
              {run.status === 'moving' ? t.movingMsg : t.arrivedMsg}
            </p>
          </div>

          {/* RIGHT: Current exhibit card + actions */}
          <div className="flex flex-col gap-4">
            <div className="gem-card overflow-hidden">
              {run.current_exhibit_image && (
                <div className="h-44 bg-gem-dark">
                  <img src={run.current_exhibit_image} alt="" className="w-full h-full object-cover" />
                </div>
              )}
              <div className="p-4">
                <h3 className="font-display text-gem-gold text-lg mb-1">{run.current_exhibit_title}</h3>
                <p className="text-gem-muted text-xs uppercase tracking-wider">
                  {isFinal ? t.final : `${t.next}: ${run.next_exhibit_title ?? '—'}`}
                </p>
              </div>
            </div>

            {/* Action area — depends on status */}
            {run.status === 'arrived' && (
              <>
                <Link
                  to={`/chat?exhibit=${run.current_exhibit_id}`}
                  className="gem-btn-ghost w-full text-center"
                >
                  🎤 {t.ask}
                </Link>
                <button
                  onClick={handleContinue}
                  disabled={busy}
                  className="gem-btn-primary w-full disabled:opacity-50"
                >
                  {isFinal ? t.finishBtn : t.continueBtn} →
                </button>
              </>
            )}
            {run.status === 'moving' && (
              <div className="gem-card p-4 text-center">
                <div className="text-gem-gold mb-2 animate-pulse">⊙</div>
                <p className="text-gem-muted text-sm">{t.movingMsg}</p>
              </div>
            )}

            <button
              onClick={handleCancel}
              className="text-gem-muted hover:text-red-400 text-xs text-center mt-2 transition-colors"
              disabled={busy}
            >
              ✕ {t.cancel}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
