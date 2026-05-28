/**
 * NavigationPage — shown after the visitor taps "Navigate Here" on an
 * exhibit detail page.  Mirrors the TourRunPage experience (map + robot +
 * narration + Ask Questions) but for a single, non-tour goal.
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { useLanguage } from '../hooks/useLanguage'
import {
  getNavState, getNavNarration, stopNavigation,
  getMapOverview, getMapExhibits, getRobotStatus,
  type Narration,
} from '../services/api'
import type {
  MapOverview as MapOv, MapExhibitMarker, MapConfig, RobotStatus, NavState, Language,
} from '../types'

const T = {
  en: {
    heading: 'THOTH is heading to',
    arrived: 'Standing in front of',
    movingMsg: 'THOTH is on the way.',
    arrivedMsg: 'THOTH has arrived — listen, then ask any questions.',
    narrationLabel: 'THOTH is speaking',
    replay: 'Replay narration',
    pause: 'Pause narration',
    askExhibit: 'Ask about this exhibit',
    stopNav: 'Stop navigation',
    backExhibits: '← Back to exhibits',
    none: 'No navigation in progress.',
    findOne: 'Browse exhibits',
    langInNarration: 'Speak in',
    legendTarget: 'Target',
    legendRobot: 'THOTH',
    legendOther: 'Other exhibits',
  },
  ar: {
    heading: 'تحوت متجه إلى',
    arrived: 'نحن أمام',
    movingMsg: 'تحوت في الطريق.',
    arrivedMsg: 'تحوت وصل — استمع ثم اسأل ما تريد.',
    narrationLabel: 'تحوت يتحدث',
    replay: 'إعادة الشرح',
    pause: 'إيقاف الشرح',
    askExhibit: 'اسأل عن هذا المعروض',
    stopNav: 'إيقاف التنقل',
    backExhibits: '← العودة إلى المعروضات',
    none: 'لا توجد رحلة جارية.',
    findOne: 'تصفح المعروضات',
    langInNarration: 'التحدث بـ',
    legendTarget: 'الهدف',
    legendRobot: 'تحوت',
    legendOther: 'معروضات أخرى',
  },
  fr: {
    heading: 'THOTH se dirige vers',
    arrived: 'Devant',
    movingMsg: 'THOTH est en route.',
    arrivedMsg: 'THOTH est arrivé — écoutez puis posez vos questions.',
    narrationLabel: 'THOTH parle',
    replay: 'Rejouer la narration',
    pause: 'Pause narration',
    askExhibit: 'Poser une question',
    stopNav: 'Arrêter la navigation',
    backExhibits: '← Retour aux expositions',
    none: 'Aucune navigation en cours.',
    findOne: 'Parcourir les expositions',
    langInNarration: 'Parler en',
    legendTarget: 'Cible',
    legendRobot: 'THOTH',
    legendOther: 'Autres expositions',
  },
}

function worldToPercent(wx: number, wy: number, cfg: MapConfig) {
  const px = (wx - cfg.origin_x) / cfg.resolution
  const py = cfg.height_px - (wy - cfg.origin_y) / cfg.resolution
  return { left: `${(px / cfg.width_px) * 100}%`, top: `${(py / cfg.height_px) * 100}%` }
}

export default function NavigationPage() {
  const { lang } = useLanguage()
  const t = T[lang]
  const nav = useNavigate()

  const [state, setState] = useState<NavState | null>(null)
  const [map, setMap] = useState<MapOv | null>(null)
  const [markers, setMarkers] = useState<MapExhibitMarker[]>([])
  const [robot, setRobot] = useState<RobotStatus | null>(null)

  const [narration, setNarration] = useState<Narration | null>(null)
  const [narrationLang, setNarrationLang] = useState<Language>(lang)
  const [playing, setPlaying] = useState(false)

  // Persistent ONE-element audio (mobile autoplay friendly).
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const narratedFor = useRef<number | null>(null)
  const mountedRef = useRef(true)

  const ensureAudio = (): HTMLAudioElement => {
    if (audioRef.current) return audioRef.current
    const el = new Audio()
    el.preload = 'auto'
    el.addEventListener('play',  () => setPlaying(true))
    el.addEventListener('pause', () => setPlaying(false))
    el.addEventListener('ended', () => setPlaying(false))
    audioRef.current = el
    return el
  }

  const stopAudio = () => {
    const el = audioRef.current
    if (el) {
      el.pause()
      el.removeAttribute('src')
      try { el.load() } catch {}
    }
    setPlaying(false)
  }

  const playAudio = (b64: string) => {
    if (!mountedRef.current) return
    const el = ensureAudio()
    el.pause()
    el.src = `data:audio/mp3;base64,${b64}`
    el.play().catch(() => setPlaying(false))
  }

  // Initial map data
  useEffect(() => {
    Promise.all([getMapOverview(), getMapExhibits(lang)]).then(([m, mx]) => { setMap(m); setMarkers(mx) })
  }, [lang])

  // Poll nav state + robot every 600ms
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const [s, r] = await Promise.all([getNavState(lang), getRobotStatus()])
        if (!alive) return
        setState(s); setRobot(r)
      } catch { /* ignore */ }
    }
    tick()
    const i = setInterval(tick, 600)
    return () => { alive = false; clearInterval(i) }
  }, [lang])

  // Sync narration language with UI language when user changes the global one
  useEffect(() => { setNarrationLang(lang) }, [lang])

  // Auto-fetch narration when robot arrives
  useEffect(() => {
    if (!state?.active || state.status !== 'arrived') return
    if (narratedFor.current === state.request_id) return
    narratedFor.current = state.request_id
    let alive = true
    getNavNarration(state.request_id, narrationLang, true).then(n => {
      if (!alive || !n) return
      setNarration(n)
      if (n.audio_base64) playAudio(n.audio_base64)
    })
    return () => { alive = false }
  }, [state?.active && state.status, state && (state.active ? state.request_id : null)])

  // When the user picks a different narration language, re-fetch
  const replayInLang = async (l: Language) => {
    if (!state?.active || state.status !== 'arrived') return
    setNarrationLang(l)
    stopAudio()
    const n = await getNavNarration(state.request_id, l, true)
    if (!n) return
    setNarration(n)
    if (n.audio_base64) playAudio(n.audio_base64)
  }

  const handleStop = async () => {
    stopAudio()
    setNarration(null)
    await stopNavigation()
    nav('/exhibits')
  }

  useEffect(() => () => { mountedRef.current = false; stopAudio() }, [])

  const cfg = map?.map_config

  if (!state) return <div className="text-center text-gem-muted py-20">…</div>

  if (!state.active) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center animate-fade-in">
        <div className="text-gem-gold/40 text-5xl mb-4">𓅓</div>
        <p className="text-gem-text mb-6">{t.none}</p>
        <Link to="/exhibits" className="gem-btn-primary">{t.findOne}</Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 animate-fade-in">
      {/* Header */}
      <div className="mb-4 flex items-end justify-between flex-wrap gap-2">
        <h1 className="font-display text-gem-gold text-2xl">
          {state.status === 'arrived' ? t.arrived : t.heading}{' '}
          <span className="text-gem-text">{state.exhibit_title}</span>
        </h1>
        <Link to="/exhibits" className="text-gem-gold/60 hover:text-gem-gold text-sm">
          {t.backExhibits}
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT: map */}
        <div className="lg:col-span-2 gem-card p-4">
          <div className="relative w-full aspect-[17/8] bg-gem-dark rounded-xl overflow-hidden border border-gem-gold/20">
            <img src="/assets/museum_map.png" alt="Map"
                 className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                 draggable={false} />

            {/* All other exhibits, dim */}
            {cfg && markers.map(m => {
              if (m.id === state.exhibit_id) return null
              const pos = worldToPercent(m.x, m.y, cfg)
              return (
                <div key={m.id} style={pos}
                     className="absolute -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-gem-gold/30 border border-gem-gold/40 z-10"
                     title={m.title} />
              )
            })}

            {/* Target marker: pulsing + bright */}
            {cfg && state.target_x != null && state.target_y != null && (
              <div style={worldToPercent(state.target_x, state.target_y, cfg)}
                   className="absolute -translate-x-1/2 -translate-y-1/2 z-15">
                <div className="absolute -inset-2.5 rounded-full border-2 border-gem-gold animate-ping pointer-events-none" />
                <div className="relative w-7 h-7 rounded-full bg-gem-gold border-2 border-gem-navy shadow-[0_0_16px_rgba(201,168,76,0.95)]" />
              </div>
            )}

            {/* Robot */}
            {cfg && robot && (
              <div style={{
                ...worldToPercent(robot.current_x, robot.current_y, cfg),
                transition: 'left 600ms linear, top 600ms linear',
              }}
                   className="absolute -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-blue-400 border-2 border-white animate-pulse shadow-[0_0_12px_rgba(96,165,250,0.8)] z-20" />
            )}
          </div>

          <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
            <p className="text-gem-muted text-xs">
              {state.status === 'arrived' ? t.arrivedMsg : t.movingMsg}
            </p>
            <div className="flex items-center gap-3 text-[10px] text-gem-muted">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gem-gold border border-gem-navy"/>{t.legendTarget}</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-blue-400 border border-white"/>{t.legendRobot}</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gem-gold/30 border border-gem-gold/40"/>{t.legendOther}</span>
            </div>
          </div>
        </div>

        {/* RIGHT: exhibit + actions */}
        <div className="flex flex-col gap-4">
          <div className="gem-card overflow-hidden">
            {state.exhibit_image && (
              <div className="h-44 bg-gem-dark">
                <img src={state.exhibit_image} alt="" className="w-full h-full object-cover" />
              </div>
            )}
            <div className="p-4">
              <h3 className="font-display text-gem-gold text-lg mb-1">{state.exhibit_title}</h3>
            </div>
          </div>

          {state.status === 'arrived' && (
            <>
              {narration && (
                <div className="gem-card p-4 border-gem-gold/40">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <div className={clsx("w-2 h-2 rounded-full", playing ? "bg-gem-gold animate-pulse" : "bg-gem-gold/40")} />
                      <span className="text-gem-gold text-xs font-display uppercase tracking-wider">
                        {t.narrationLabel}
                      </span>
                    </div>
                    {/* Language picker for narration only */}
                    <div className="flex gap-1">
                      {(['en', 'ar', 'fr'] as const).map(l => (
                        <button key={l}
                                onClick={() => replayInLang(l)}
                                className={clsx(
                                  "text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold transition-colors",
                                  narrationLang === l
                                    ? "bg-gem-gold text-gem-navy"
                                    : "text-gem-gold/60 hover:text-gem-gold border border-gem-gold/30"
                                )}
                                title={`${t.langInNarration} ${l.toUpperCase()}`}>
                          {l}
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="text-gem-text text-sm leading-relaxed mb-3">{narration.narration}</p>
                  {narration.audio_base64 && (
                    <button
                      onClick={() => {
                        if (audioRef.current && playing) { audioRef.current.pause() }
                        else if (audioRef.current) { audioRef.current.play().catch(() => {}) }
                        else { playAudio(narration.audio_base64!) }
                      }}
                      className="text-gem-gold/70 hover:text-gem-gold text-xs inline-flex items-center gap-1.5 transition-colors"
                    >
                      {playing ? (
                        <><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg> {t.pause}</>
                      ) : (
                        <><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> {t.replay}</>
                      )}
                    </button>
                  )}
                </div>
              )}

              <Link to={`/chat?exhibit=${state.exhibit_id}&returnTo=navigate`}
                    className="gem-btn-primary w-full text-center">
                🎤 {t.askExhibit}
              </Link>
            </>
          )}

          {state.status === 'in_progress' && (
            <div className="gem-card p-4 text-center">
              <div className="text-gem-gold mb-2 animate-pulse">⊙</div>
              <p className="text-gem-muted text-sm">{t.movingMsg}</p>
            </div>
          )}

          <button onClick={handleStop}
                  className="text-gem-muted hover:text-red-400 text-xs text-center mt-2 transition-colors">
            ✕ {t.stopNav}
          </button>
        </div>
      </div>
    </div>
  )
}
