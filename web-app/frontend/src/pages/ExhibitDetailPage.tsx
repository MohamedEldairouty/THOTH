import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import clsx from 'clsx'
import { useLanguage } from '../hooks/useLanguage'
import {
  getExhibit, startNavigation, getNavState, getNavNarration,
  getCurrentTourRun, stopNavigation,
  type Narration,
} from '../services/api'
import type { ExhibitLocalized, NavState, TourRun } from '../types'

const T = {
  en: {
    back: '← Back to Exhibits',
    navigate: 'Navigate Here',
    askThoth: 'Ask THOTH',
    audioNarration: 'Audio Narration',
    onTourMsg: 'Robot is busy with a tour — finish or cancel it first.',
    heading: 'THOTH is heading to',
    arrived: 'THOTH has arrived',
    movingMsg: 'THOTH is on the way.',
    arrivedMsg: 'THOTH is here — listen, then ask any questions.',
    narrationLabel: 'THOTH is speaking',
    replay: 'Replay narration',
    stopAudio: 'Stop audio',
    askExhibit: 'Ask about this exhibit',
    stopNav: 'Stop navigation',
    backExhibits: '← Back to exhibits',
  },
  ar: {
    back: '← العودة إلى المعروضات',
    navigate: 'التنقل هنا',
    askThoth: 'اسأل تحوت',
    audioNarration: 'الشرح الصوتي',
    onTourMsg: 'الروبوت مشغول في جولة — أنهها أو ألغها أولاً.',
    heading: 'تحوت متجه إلى',
    arrived: 'تحوت وصل',
    movingMsg: 'تحوت في الطريق.',
    arrivedMsg: 'تحوت هنا — استمع ثم اسأل ما تريد.',
    narrationLabel: 'تحوت يتحدث',
    replay: 'إعادة الشرح',
    stopAudio: 'إيقاف الصوت',
    askExhibit: 'اسأل عن هذا المعروض',
    stopNav: 'إيقاف التنقل',
    backExhibits: '← العودة إلى المعروضات',
  },
  fr: {
    back: '← Retour aux expositions',
    navigate: 'Naviguer ici',
    askThoth: 'Demander à THOTH',
    audioNarration: 'Narration audio',
    onTourMsg: 'Le robot est occupé avec une visite — terminez ou annulez-la d\'abord.',
    heading: 'THOTH se dirige vers',
    arrived: 'THOTH est arrivé',
    movingMsg: 'THOTH est en route.',
    arrivedMsg: 'THOTH est là — écoutez puis posez vos questions.',
    narrationLabel: 'THOTH parle',
    replay: 'Rejouer la narration',
    stopAudio: 'Arrêter l\'audio',
    askExhibit: 'Poser une question',
    stopNav: 'Arrêter la navigation',
    backExhibits: '← Retour aux expositions',
  },
}

export default function ExhibitDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { lang } = useLanguage()
  const t = T[lang]

  const [exhibit, setExhibit] = useState<ExhibitLocalized | null>(null)
  const [loading, setLoading] = useState(true)
  const [navigating, setNavigating] = useState(false)
  const [navState, setNavState] = useState<NavState | null>(null)
  const [tourRun, setTourRun] = useState<TourRun | null>(null)
  const [narration, setNarration] = useState<Narration | null>(null)
  const [playing, setPlaying] = useState(false)

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const narratedFor = useRef<number | null>(null)

  // ── audio helpers (same pattern as TourRunPage) ─────────────────────
  const stopAudio = () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; audioRef.current = null }
    setPlaying(false)
  }
  const playAudio = (b64: string) => {
    stopAudio()
    const el = new Audio(`data:audio/mp3;base64,${b64}`)
    audioRef.current = el
    el.onended = () => { audioRef.current = null; setPlaying(false) }
    el.play().then(() => setPlaying(true)).catch(() => setPlaying(false))
  }

  // Load exhibit details
  useEffect(() => {
    if (!id) return
    setLoading(true)
    getExhibit(Number(id), lang).then(setExhibit).finally(() => setLoading(false))
  }, [id, lang])

  // Poll nav state + active tour so we can disable/enable controls live
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const [ns, tr] = await Promise.all([getNavState(lang), getCurrentTourRun()])
        if (!alive) return
        setNavState(ns)
        setTourRun(tr)
      } catch { /* ignore */ }
    }
    tick()
    const i = setInterval(tick, 700)
    return () => { alive = false; clearInterval(i) }
  }, [lang])

  // Clean up audio on unmount
  useEffect(() => () => stopAudio(), [])

  // When THIS exhibit is the active nav target and the robot just arrived,
  // fetch narration in the current language and auto-play.
  useEffect(() => {
    if (!navState?.active) {
      narratedFor.current = null
      setNarration(null)
      return
    }
    if (Number(id) !== navState.exhibit_id) return
    if (navState.status !== 'arrived') {
      setNarration(null)
      return
    }
    if (narratedFor.current === navState.request_id) return
    narratedFor.current = navState.request_id
    let alive = true
    getNavNarration(navState.request_id, lang, true).then(n => {
      if (!alive || !n) return
      setNarration(n)
      if (n.audio_base64) playAudio(n.audio_base64)
    }).catch(() => {})
    return () => { alive = false }
  }, [navState?.active && navState.status, navState && (navState.active ? navState.request_id : null), id, lang])

  const inTour = tourRun?.status === 'moving' || tourRun?.status === 'arrived'
  const isMyTarget = navState?.active && Number(id) === navState.exhibit_id
  const someoneElseIsTarget = navState?.active && !isMyTarget
  const buttonDisabled = navigating || inTour || someoneElseIsTarget || (isMyTarget === true)

  const handleNavigate = async () => {
    if (!exhibit || buttonDisabled) return
    setNavigating(true)
    try {
      await startNavigation(exhibit.id, lang)
    } catch (e: any) {
      console.error(e)
    } finally {
      setNavigating(false)
    }
  }

  const handleStopNav = async () => {
    stopAudio()
    setNarration(null)
    await stopNavigation()
  }

  if (loading) {
    return <div className="max-w-4xl mx-auto px-4 py-10"><div className="gem-card h-96 animate-shimmer" /></div>
  }
  if (!exhibit) {
    return (
      <div className="text-center py-20 text-gem-muted">
        <p className="text-xl">Exhibit not found</p>
        <Link to="/exhibits" className="gem-btn-ghost inline-block mt-4">{t.back}</Link>
      </div>
    )
  }

  // Disabled-reason tooltip for the Navigate button
  const navDisabledReason =
    inTour ? t.onTourMsg
    : someoneElseIsTarget ? `THOTH is navigating to ${navState!.exhibit_title}`
    : null

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 animate-fade-in">
      <Link to="/exhibits" className="text-gem-gold/60 hover:text-gem-gold text-sm mb-6 inline-block transition-colors">
        {t.back}
      </Link>

      <div className="gem-card overflow-hidden">
        {/* Hero image */}
        <div className="h-72 md:h-96 bg-gem-dark">
          {exhibit.image_url ? (
            <img src={exhibit.image_url} alt={exhibit.title} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-8xl text-gem-gold/20">𓅓</div>
          )}
        </div>

        <div className="p-6 md:p-8">
          {/* Header */}
          <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
            <div>
              <h1 className="font-display text-gem-gold text-3xl font-bold mb-2">{exhibit.title}</h1>
              {exhibit.era && (
                <span className="text-sm text-gem-muted border border-gem-gold/30 px-3 py-1 rounded-full">
                  {exhibit.era}
                </span>
              )}
            </div>
            <div className="flex gap-3 flex-wrap items-center">
              <button
                onClick={handleNavigate}
                disabled={buttonDisabled}
                title={navDisabledReason ?? ''}
                className="gem-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {navigating ? '...' : t.navigate}
              </button>
              <Link
                to={`/chat?exhibit=${exhibit.id}`}
                className="gem-btn-ghost"
              >
                🎤 {t.askThoth}
              </Link>
            </div>
          </div>

          {/* In-tour banner (informational, non-blocking) */}
          {inTour && (
            <div className="mb-6 px-4 py-2 rounded-lg border border-gem-gold/30 bg-gem-gold/5 text-gem-gold/80 text-sm">
              ⓘ {t.onTourMsg}
            </div>
          )}

          {/* Inline navigation panel — shown only when robot is navigating to THIS exhibit */}
          {isMyTarget && navState!.status !== 'cancelled' && (
            <div className="mb-6 gem-card p-4 border-gem-gold/40 bg-gem-gold/[0.02]">
              <div className="flex items-center gap-2 mb-3">
                <div className={clsx(
                  "w-2 h-2 rounded-full",
                  navState!.status === 'arrived' ? "bg-gem-gold animate-pulse" : "bg-blue-400 animate-pulse"
                )} />
                <span className="text-gem-gold font-display text-sm uppercase tracking-wider">
                  {navState!.status === 'arrived' ? t.arrived : `${t.heading} ${exhibit.title}`}
                </span>
              </div>
              <p className="text-gem-muted text-sm mb-3">
                {navState!.status === 'arrived' ? t.arrivedMsg : t.movingMsg}
              </p>

              {/* Narration (only after arrival) */}
              {narration && (
                <div className="mb-3 p-3 rounded border border-gem-gold/20">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={clsx("w-2 h-2 rounded-full", playing ? "bg-gem-gold animate-pulse" : "bg-gem-gold/40")} />
                    <span className="text-gem-gold text-xs font-display uppercase tracking-wider">
                      {t.narrationLabel}
                    </span>
                  </div>
                  <p className="text-gem-text text-sm leading-relaxed mb-2">{narration.narration}</p>
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

              <div className="flex flex-wrap gap-2">
                {navState!.status === 'arrived' && (
                  <Link
                    to={`/chat?exhibit=${exhibit.id}&returnTo=exhibit`}
                    className="gem-btn-ghost text-sm"
                  >
                    🎤 {t.askExhibit}
                  </Link>
                )}
                <button
                  onClick={handleStopNav}
                  className="text-gem-muted hover:text-red-400 text-xs transition-colors ml-auto"
                >
                  ✕ {t.stopNav}
                </button>
              </div>
            </div>
          )}

          <div className="gem-divider" />

          {/* Description */}
          <p className="text-gem-text leading-relaxed text-lg">
            {exhibit.full_description || exhibit.short_description}
          </p>

          {/* Audio player placeholder */}
          {exhibit.audio_url && (
            <div className="mt-6 p-4 gem-card border-gem-gold/20">
              <p className="text-gem-muted text-sm mb-2">{t.audioNarration}</p>
              <audio controls src={exhibit.audio_url} className="w-full" />
            </div>
          )}

          {exhibit.video_url && (
            <div className="mt-4">
              <video controls src={exhibit.video_url} className="w-full rounded-xl" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
