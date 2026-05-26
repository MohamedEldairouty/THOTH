import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import {
  getExhibit, startNavigation, getNavState,
  getCurrentTourRun,
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
  const navigateTo = useNavigate()

  const [exhibit, setExhibit] = useState<ExhibitLocalized | null>(null)
  const [loading, setLoading] = useState(true)
  const [navigating, setNavigating] = useState(false)
  const [navState, setNavState] = useState<NavState | null>(null)
  const [tourRun, setTourRun] = useState<TourRun | null>(null)

  // Load exhibit details
  useEffect(() => {
    if (!id) return
    setLoading(true)
    getExhibit(Number(id), lang).then(setExhibit).finally(() => setLoading(false))
  }, [id, lang])

  // Poll nav state + active tour so we can disable controls live
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const [ns, tr] = await Promise.all([getNavState(lang), getCurrentTourRun()])
        if (!alive) return
        setNavState(ns); setTourRun(tr)
      } catch { /* ignore */ }
    }
    tick()
    const i = setInterval(tick, 1500)
    return () => { alive = false; clearInterval(i) }
  }, [lang])

  const inTour = tourRun?.status === 'moving' || tourRun?.status === 'arrived'
  // Only treat a single-exhibit nav as "blocking" while it's still moving.
  // Once the robot has arrived, the visitor is free to pick a new destination —
  // we just don't bother flipping the "arrived" row to cancelled until they
  // start a new nav (NavigationService.start() does that).
  const navInProgress = navState?.active && navState.status === 'in_progress'
  const isMyTarget = !!navInProgress && Number(id) === navState!.exhibit_id
  const someoneElseIsTarget = !!navInProgress && !isMyTarget
  const buttonDisabled = navigating || inTour || someoneElseIsTarget || isMyTarget

  const handleNavigate = async () => {
    if (!exhibit || buttonDisabled) return
    setNavigating(true)
    try {
      await startNavigation(exhibit.id, lang)
      // Move to the dedicated NavigationPage so the visitor follows the
      // robot on the map + sees the narration there.
      navigateTo('/navigate')
    } catch (e: any) {
      console.error(e)
      setNavigating(false)
    }
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

  const navDisabledReason =
    inTour ? t.onTourMsg
    : someoneElseIsTarget ? `THOTH is navigating to ${navState!.exhibit_title}`
    : isMyTarget ? 'Already navigating here.'
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

          {/* Banners */}
          {inTour && (
            <div className="mb-6 px-4 py-2 rounded-lg border border-gem-gold/30 bg-gem-gold/5 text-gem-gold/80 text-sm">
              ⓘ {t.onTourMsg}
            </div>
          )}
          {someoneElseIsTarget && navInProgress && (
            <div className="mb-6 px-4 py-2 rounded-lg border border-blue-400/30 bg-blue-400/5 text-blue-200 text-sm">
              ⓘ THOTH is currently navigating to {navState!.exhibit_title}.
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
