import { useEffect, useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import clsx from 'clsx'
import { useLanguage } from '../hooks/useLanguage'
import {
  getCurrentTourRun, advanceTour, cancelTour,
  getMapOverview, getRobotStatus, getNarration,
  type TourRun, type MapOverview as MapOv, type Narration,
} from '../services/api'
import type { RobotStatus, MapConfig } from '../types'

const T = {
  en: {
    none: 'No active tour. Pick one from Start Tour.',
    start: 'Start a Tour',
    heading: 'Heading to',
    arrived: 'Standing in front of',
    next: 'Up next',
    final: 'Final exhibit',
    continueBtn: 'Continue to next exhibit',
    finishBtn: 'Finish tour',
    movingMsg: 'THOTH is on the way.',
    arrivedMsg: 'THOTH has arrived — listen, then ask any questions.',
    ask: 'Ask THOTH about this exhibit',
    narrationLabel: 'THOTH is speaking',
    replay: 'Replay narration',
    stopAudio: 'Stop audio',
    cancel: 'Cancel tour',
    cancelled: 'Tour cancelled.',
    completed: 'Tour complete. Thank you for visiting!',
    backTour: 'Back to tour menu',
    autoReturn: 'Returning to the main menu in a moment…',
    legendVisited: 'Visited',
    legendCurrent: 'Current',
    legendPending: 'Upcoming',
    legendRobot: 'THOTH',
  },
  ar: {
    none: 'لا توجد جولة نشطة. اختر واحدة من ابدأ الجولة.',
    start: 'ابدأ جولة',
    heading: 'متجه إلى',
    arrived: 'نحن أمام',
    next: 'التالي',
    final: 'المعروض الأخير',
    continueBtn: 'الانتقال إلى المعروض التالي',
    finishBtn: 'إنهاء الجولة',
    movingMsg: 'تحوت في الطريق.',
    arrivedMsg: 'تحوت وصل — استمع ثم اسأل ما تريد.',
    ask: 'اسأل تحوت عن هذا المعروض',
    narrationLabel: 'تحوت يتحدث',
    replay: 'إعادة الشرح',
    stopAudio: 'إيقاف الصوت',
    cancel: 'إلغاء الجولة',
    cancelled: 'تم إلغاء الجولة.',
    completed: 'اكتملت الجولة. شكراً لزيارتك!',
    backTour: 'العودة إلى قائمة الجولات',
    autoReturn: 'العودة إلى القائمة الرئيسية بعد لحظات…',
    legendVisited: 'تمت زيارته',
    legendCurrent: 'الحالي',
    legendPending: 'قادم',
    legendRobot: 'تحوت',
  },
  fr: {
    none: 'Aucune visite active. Choisissez-en une depuis Commencer la visite.',
    start: 'Commencer une visite',
    heading: 'En route vers',
    arrived: 'Devant',
    next: 'Prochain',
    final: 'Dernière exposition',
    continueBtn: 'Continuer vers la prochaine exposition',
    finishBtn: 'Terminer la visite',
    movingMsg: 'THOTH est en route.',
    arrivedMsg: 'THOTH est arrivé — écoutez puis posez vos questions.',
    ask: 'Demander à THOTH',
    narrationLabel: 'THOTH parle',
    replay: 'Rejouer la narration',
    stopAudio: 'Arrêter l\'audio',
    cancel: 'Annuler la visite',
    cancelled: 'Visite annulée.',
    completed: 'Visite terminée. Merci de votre visite !',
    backTour: 'Retour au menu des visites',
    autoReturn: 'Retour au menu principal dans un instant…',
    legendVisited: 'Visité',
    legendCurrent: 'Actuel',
    legendPending: 'À venir',
    legendRobot: 'THOTH',
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
  const [narration, setNarration] = useState<Narration | null>(null)
  const [playing, setPlaying] = useState(false)

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const lastNarratedStop = useRef<{ runId: number; index: number } | null>(null)

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ''
      audioRef.current = null
    }
    setPlaying(false)
  }

  const playAudio = (base64: string) => {
    stopAudio()
    const el = new Audio(`data:audio/mp3;base64,${base64}`)
    audioRef.current = el
    el.onended = () => { audioRef.current = null; setPlaying(false) }
    el.play().then(() => setPlaying(true)).catch(() => setPlaying(false))
  }

  useEffect(() => { getMapOverview().then(setMap) }, [])
  useEffect(() => () => stopAudio(), [])

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

  // On arrival at a new stop, fetch + auto-play narration (in current language)
  useEffect(() => {
    if (!run || run.status !== 'arrived') return
    const stamp = { runId: run.id, index: run.current_stop_index }
    const prev = lastNarratedStop.current
    if (prev && prev.runId === stamp.runId && prev.index === stamp.index) return
    lastNarratedStop.current = stamp

    let alive = true
    setNarration(null)
    getNarration(run.id, true).then(n => {
      if (!alive || !n) return
      setNarration(n)
      if (n.audio_base64) playAudio(n.audio_base64)
    }).catch(() => {})
    return () => { alive = false }
  }, [run?.id, run?.status, run?.current_stop_index])

  // When robot starts moving again, clear narration + audio
  useEffect(() => {
    if (run && run.status !== 'arrived') {
      setNarration(null)
      stopAudio()
    }
  }, [run?.status])

  // Auto-redirect to /tour after completed / cancelled (4s grace period)
  useEffect(() => {
    if (!run) return
    if (run.status !== 'completed' && run.status !== 'cancelled') return
    const id = setTimeout(() => nav('/tour'), 4000)
    return () => clearTimeout(id)
  }, [run?.status])

  const handleContinue = async () => {
    if (!run) return
    stopAudio()
    setNarration(null)
    setBusy(true)
    try {
      const r = await advanceTour(run.id)
      setRun(r)
    } finally { setBusy(false) }
  }

  const handleCancel = async () => {
    if (!run) return
    stopAudio()
    setBusy(true)
    try {
      await cancelTour(run.id)
      // Don't navigate immediately — show "Tour cancelled" card briefly
      const r = await getCurrentTourRun()
      setRun(r)
    } finally { setBusy(false) }
  }

  if (run === undefined) {
    return <div className="text-center text-gem-muted py-20">…</div>
  }
  if (run === null) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center animate-fade-in">
        <div className="text-gem-gold/40 text-5xl mb-4">𓅓</div>
        <p className="text-gem-text mb-6">{t.none}</p>
        <Link to="/tour" className="gem-btn-primary">{t.start}</Link>
      </div>
    )
  }

  const isFinal = run.current_stop_index + 1 >= run.total_stops
  const cfg = map?.map_config

  // Tour finished / cancelled — celebratory card, then auto-redirect
  if (run.status === 'completed' || run.status === 'cancelled') {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center animate-fade-in">
        <div className="text-gem-gold text-5xl mb-3">{run.status === 'completed' ? '𓋹' : '𓋴'}</div>
        <h2 className="font-display text-gem-gold text-2xl mb-2">
          {run.status === 'completed' ? t.completed : t.cancelled}
        </h2>
        <p className="text-gem-muted text-sm mb-6 italic">{t.autoReturn}</p>
        <Link to="/tour" className="gem-btn-primary inline-block">{t.backTour}</Link>
      </div>
    )
  }

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LEFT: Map with full route */}
        <div className="lg:col-span-2 gem-card p-4">
          <div className="relative w-full aspect-[17/8] bg-gem-dark rounded-xl overflow-hidden border border-gem-gold/20">
            <img
              src="/assets/museum_map.png"
              alt="Map"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              draggable={false}
            />

            {/* ALL tour stops, color-coded by state */}
            {cfg && run.all_stops.map((stop) => {
              if (stop.x_position == null || stop.y_position == null) return null
              const isVisited = stop.sequence_order < run.current_stop_index
              const isCurrent = stop.sequence_order === run.current_stop_index
              const pos = worldToPercent(stop.x_position, stop.y_position, cfg)
              return (
                <div key={stop.exhibit_id} style={pos} className="absolute -translate-x-1/2 -translate-y-1/2 z-10">
                  {isCurrent && (
                    <div className="absolute -inset-2 rounded-full border-2 border-gem-gold animate-ping" />
                  )}
                  <div
                    className={clsx(
                      'rounded-full border-2 flex items-center justify-center text-[10px] font-bold relative',
                      isCurrent && 'bg-gem-gold border-gem-navy text-gem-navy w-6 h-6 shadow-[0_0_10px_rgba(201,168,76,0.7)]',
                      isVisited && 'bg-gem-gold/30 border-gem-gold/60 text-gem-gold w-5 h-5',
                      !isCurrent && !isVisited && 'bg-gem-navy border-gem-gold/50 text-gem-gold/70 w-5 h-5',
                    )}
                    title={stop.exhibit_title}
                  >
                    {isVisited ? '✓' : stop.sequence_order + 1}
                  </div>
                </div>
              )
            })}

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

          {/* Status + legend */}
          <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
            <p className="text-gem-muted text-xs">
              {run.status === 'moving' ? t.movingMsg : t.arrivedMsg}
            </p>
            <div className="flex items-center gap-3 text-[10px] text-gem-muted">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gem-gold/30 border border-gem-gold/60"/>{t.legendVisited}</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gem-gold border border-gem-navy"/>{t.legendCurrent}</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gem-navy border border-gem-gold/50"/>{t.legendPending}</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-blue-400 border border-white"/>{t.legendRobot}</span>
            </div>
          </div>
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

          {run.status === 'arrived' && (
            <>
              {narration && (
                <div className="gem-card p-4 border-gem-gold/40">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={clsx(
                      "w-2 h-2 rounded-full",
                      playing ? "bg-gem-gold animate-pulse" : "bg-gem-gold/40"
                    )} />
                    <span className="text-gem-gold text-xs font-display uppercase tracking-wider">
                      {t.narrationLabel}
                    </span>
                  </div>
                  <p className="text-gem-text text-sm leading-relaxed mb-3">
                    {narration.narration}
                  </p>
                  {narration.audio_base64 && (
                    <button
                      onClick={() => playing ? stopAudio() : playAudio(narration.audio_base64!)}
                      className="text-gem-gold/70 hover:text-gem-gold text-xs inline-flex items-center gap-1.5 transition-colors"
                    >
                      {playing ? (
                        <><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg> {t.stopAudio}</>
                      ) : (
                        <><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> {t.replay}</>
                      )}
                    </button>
                  )}
                </div>
              )}

              <Link
                to={`/chat?exhibit=${run.current_exhibit_id}&returnTo=tour`}
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
    </div>
  )
}
