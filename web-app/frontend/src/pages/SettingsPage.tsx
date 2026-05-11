import { useState } from 'react'
import { useLanguage } from '../hooks/useLanguage'
import type { Language } from '../types'
import clsx from 'clsx'

const LANGS: { code: Language; label: string; native: string }[] = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'ar', label: 'Arabic', native: 'العربية' },
  { code: 'fr', label: 'French', native: 'Français' },
]

export default function SettingsPage() {
  const { lang, setLang } = useLanguage()
  const [fontSize, setFontSize] = useState<'normal' | 'large' | 'xlarge'>('normal')
  const [captions, setCaptions] = useState(true)

  const t = {
    en: { title: 'Settings', language: 'Language', display: 'Display', captions: 'Captions', fontSize: 'Font Size', normal: 'Normal', large: 'Large', xlarge: 'Extra Large', accessibility: 'Accessibility' },
    ar: { title: 'الإعدادات', language: 'اللغة', display: 'العرض', captions: 'التعليقات', fontSize: 'حجم الخط', normal: 'عادي', large: 'كبير', xlarge: 'كبير جداً', accessibility: 'إمكانية الوصول' },
    fr: { title: 'Paramètres', language: 'Langue', display: 'Affichage', captions: 'Sous-titres', fontSize: 'Taille police', normal: 'Normal', large: 'Grand', xlarge: 'Très grand', accessibility: 'Accessibilité' },
  }[lang]

  return (
    <div className="max-w-2xl mx-auto px-4 py-10 animate-fade-in">
      <h1 className="gem-section-title mb-8">{t.title}</h1>

      {/* Language */}
      <div className="gem-card p-6 mb-4">
        <h2 className="text-gem-gold font-semibold mb-4">{t.language}</h2>
        <div className="flex gap-3 flex-wrap">
          {LANGS.map(l => (
            <button
              key={l.code}
              onClick={() => setLang(l.code)}
              className={clsx(
                'px-5 py-3 rounded-xl font-medium transition-all',
                lang === l.code
                  ? 'bg-gem-gold text-gem-navy'
                  : 'gem-btn-ghost'
              )}
            >
              <span className="block text-sm">{l.native}</span>
              <span className="block text-xs opacity-70">{l.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Accessibility */}
      <div className="gem-card p-6 mb-4">
        <h2 className="text-gem-gold font-semibold mb-4">{t.accessibility}</h2>

        {/* Captions toggle */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-gem-text">{t.captions}</span>
          <button
            onClick={() => setCaptions(c => !c)}
            className={clsx(
              'w-12 h-6 rounded-full transition-colors relative',
              captions ? 'bg-gem-gold' : 'bg-gem-dark border border-gem-gold/30'
            )}
          >
            <span className={clsx(
              'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all',
              captions ? 'left-6' : 'left-0.5'
            )} />
          </button>
        </div>

        {/* Font size */}
        <div>
          <p className="text-gem-text mb-2">{t.fontSize}</p>
          <div className="flex gap-2">
            {(['normal', 'large', 'xlarge'] as const).map(size => (
              <button
                key={size}
                onClick={() => setFontSize(size)}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm transition-all',
                  fontSize === size ? 'bg-gem-gold text-gem-navy' : 'gem-btn-ghost'
                )}
              >
                {t[size]}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
