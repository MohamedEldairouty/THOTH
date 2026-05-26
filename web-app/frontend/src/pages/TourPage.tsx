import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { useLanguage } from '../hooks/useLanguage'
import {
  listTours, getExhibits, startTour, getCurrentTourRun,
  type TourSummary,
} from '../services/api'
import type { ExhibitLocalized } from '../types'

const T = {
  en: {
    title: 'Start Your Tour',
    subtitle: 'Choose a curated route or build your own.',
    preset: 'Curated Tours',
    custom: 'Build Custom Tour',
    customHint: 'Pick exhibits in the order you want to visit them.',
    selected: 'Selected',
    start: 'Start Tour',
    minutes: 'min',
    stops: 'stops',
    customName: 'Custom Tour',
    cancel: 'Clear',
    resume: 'A tour is already running — open it',
    blocked: 'Finish or cancel the active tour before starting a new one.',
  },
  ar: {
    title: 'ابدأ جولتك',
    subtitle: 'اختر جولة منسقة أو ابنِ جولتك الخاصة.',
    preset: 'جولات منسقة',
    custom: 'بناء جولة مخصصة',
    customHint: 'اختر المعروضات بالترتيب الذي تريد زيارته.',
    selected: 'المحدد',
    start: 'ابدأ الجولة',
    minutes: 'دقيقة',
    stops: 'محطات',
    customName: 'جولة مخصصة',
    cancel: 'مسح',
    resume: 'هناك جولة قيد التشغيل — افتحها',
    blocked: 'أنهِ أو ألغِ الجولة الحالية قبل بدء جولة جديدة.',
  },
  fr: {
    title: 'Commencer votre visite',
    subtitle: 'Choisissez un parcours organisé ou créez le vôtre.',
    preset: 'Visites organisées',
    custom: 'Visite personnalisée',
    customHint: "Choisissez les expositions dans l'ordre où vous voulez les visiter.",
    selected: 'Sélectionnés',
    start: 'Commencer',
    minutes: 'min',
    stops: 'arrêts',
    customName: 'Visite personnalisée',
    cancel: 'Effacer',
    resume: 'Une visite est déjà en cours — l\'ouvrir',
    blocked: 'Terminez ou annulez la visite en cours avant d\'en commencer une nouvelle.',
  },
}

export default function TourPage() {
  const { lang } = useLanguage()
  const t = T[lang]
  const nav = useNavigate()

  const [presets, setPresets] = useState<TourSummary[]>([])
  const [exhibits, setExhibits] = useState<ExhibitLocalized[]>([])
  const [picked, setPicked] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [activeRun, setActiveRun] = useState<boolean>(false)

  useEffect(() => {
    listTours(lang).then(setPresets)
    getExhibits(lang).then(setExhibits)
    // Re-poll every 2s so the page enables itself when the previous tour ends.
    const tick = () => getCurrentTourRun().then(r => setActiveRun(!!r)).catch(() => {})
    tick()
    const id = setInterval(tick, 2000)
    return () => clearInterval(id)
  }, [lang])

  const togglePick = (id: number) => {
    setPicked(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])
  }

  const launchPreset = async (tour_id: number) => {
    setBusy(true)
    try {
      await startTour({ tour_id, language: lang })
      nav('/tour/run')
    } finally { setBusy(false) }
  }

  const launchCustom = async () => {
    if (picked.length === 0) return
    setBusy(true)
    try {
      await startTour({ exhibit_ids: picked, language: lang })
      nav('/tour/run')
    } finally { setBusy(false) }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 animate-fade-in">
      <h1 className="gem-section-title mb-1">{t.title}</h1>
      <p className="text-gem-muted mb-6">{t.subtitle}</p>

      {activeRun && (
        <div className="gem-card mb-6 p-4 flex items-center justify-between border-gem-gold/50">
          <span className="text-gem-text">{t.resume}</span>
          <button className="gem-btn-primary" onClick={() => nav('/tour/run')}>
            {lang === 'ar' ? 'فتح' : lang === 'fr' ? 'Ouvrir' : 'Open'} →
          </button>
        </div>
      )}

      {/* ── Preset tours ── */}
      <h2 className="font-display text-gem-gold text-xl mb-3">{t.preset}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
        {presets.map(p => (
          <div key={p.id} className="gem-card p-5 flex flex-col gap-3">
            <h3 className="font-display text-gem-gold text-lg">{p.name}</h3>
            <p className="text-gem-muted text-sm flex-1">{p.description}</p>
            <div className="flex items-center gap-3 text-xs text-gem-muted/80">
              <span>📍 {p.stop_count} {t.stops}</span>
              {p.estimated_minutes && <span>⏱ {p.estimated_minutes} {t.minutes}</span>}
            </div>
            <button
              className="gem-btn-primary w-full disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={busy || activeRun}
              title={activeRun ? t.blocked : ''}
              onClick={() => launchPreset(p.id)}
            >
              {t.start}
            </button>
          </div>
        ))}
      </div>

      {/* ── Custom tour builder ── */}
      <h2 className="font-display text-gem-gold text-xl mb-1">{t.custom}</h2>
      <p className="text-gem-muted text-sm mb-4">{t.customHint}</p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
        {exhibits.map(ex => {
          const idx = picked.indexOf(ex.id)
          const active = idx >= 0
          return (
            <button
              key={ex.id}
              onClick={() => togglePick(ex.id)}
              className={clsx(
                'gem-card text-left p-3 flex flex-col gap-1 transition-all relative',
                active ? 'border-gem-gold ring-2 ring-gem-gold/40' : 'hover:border-gem-gold/40'
              )}
            >
              {active && (
                <span className="absolute -top-2 -right-2 bg-gem-gold text-gem-navy font-bold rounded-full w-7 h-7 flex items-center justify-center text-sm shadow-md">
                  {idx + 1}
                </span>
              )}
              <div className="text-gem-text font-medium text-sm">{ex.title}</div>
              {ex.era && <div className="text-gem-muted text-xs">{ex.era}</div>}
            </button>
          )
        })}
      </div>

      <div className="flex items-center justify-between gap-3">
        <span className="text-gem-muted text-sm">
          {t.selected}: <span className="text-gem-gold font-medium">{picked.length}</span>
        </span>
        <div className="flex gap-2">
          {picked.length > 0 && (
            <button className="gem-btn-ghost" onClick={() => setPicked([])}>
              {t.cancel}
            </button>
          )}
          <button
            className="gem-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={busy || picked.length === 0 || activeRun}
            title={activeRun ? t.blocked : ''}
            onClick={launchCustom}
          >
            {t.start}  ({picked.length})
          </button>
        </div>
      </div>
    </div>
  )
}
