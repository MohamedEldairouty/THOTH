import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { getExhibit, startNavigation } from '../services/api'
import type { ExhibitLocalized } from '../types'

export default function ExhibitDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { lang } = useLanguage()
  const navigate = useNavigate()
  const [exhibit, setExhibit] = useState<ExhibitLocalized | null>(null)
  const [loading, setLoading] = useState(true)
  const [navigating, setNavigating] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getExhibit(Number(id), lang)
      .then(setExhibit)
      .finally(() => setLoading(false))
  }, [id, lang])

  const handleNavigate = async () => {
    if (!exhibit) return
    setNavigating(true)
    try {
      await startNavigation(exhibit.id)
      navigate('/map')
    } finally {
      setNavigating(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="gem-card h-96 animate-shimmer" />
      </div>
    )
  }

  if (!exhibit) {
    return (
      <div className="text-center py-20 text-gem-muted">
        <p className="text-xl">Exhibit not found</p>
        <Link to="/exhibits" className="gem-btn-ghost inline-block mt-4">← Back</Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 animate-fade-in">
      <Link to="/exhibits" className="text-gem-gold/60 hover:text-gem-gold text-sm mb-6 inline-block transition-colors">
        ← {lang === 'ar' ? 'العودة' : lang === 'fr' ? 'Retour' : 'Back to Exhibits'}
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
            <div className="flex gap-3 flex-wrap">
              <button
                onClick={handleNavigate}
                disabled={navigating}
                className="gem-btn-primary disabled:opacity-50"
              >
                {navigating
                  ? '...'
                  : lang === 'ar' ? 'التنقل هنا' : lang === 'fr' ? 'Naviguer ici' : 'Navigate Here'}
              </button>
              <Link
                to={`/chat?exhibit=${exhibit.id}`}
                className="gem-btn-ghost"
              >
                {lang === 'ar' ? 'اسأل تحوت' : lang === 'fr' ? 'Demandez THOTH' : 'Ask THOTH'}
              </Link>
            </div>
          </div>

          <div className="gem-divider" />

          {/* Description */}
          <p className="text-gem-text leading-relaxed text-lg">
            {exhibit.full_description || exhibit.short_description}
          </p>

          {/* Audio player placeholder */}
          {exhibit.audio_url && (
            <div className="mt-6 p-4 gem-card border-gem-gold/20">
              <p className="text-gem-muted text-sm mb-2">
                {lang === 'ar' ? 'الشرح الصوتي' : lang === 'fr' ? 'Narration audio' : 'Audio Narration'}
              </p>
              <audio controls src={exhibit.audio_url} className="w-full" />
            </div>
          )}

          {/* Video placeholder */}
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
