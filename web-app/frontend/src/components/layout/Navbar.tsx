import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { useLanguage } from '../../hooks/useLanguage'
import type { Language } from '../../types'

const NAV_LINKS = [
  { to: '/', label: { en: 'Home', ar: 'الرئيسية', fr: 'Accueil' } },
  { to: '/exhibits', label: { en: 'Exhibits', ar: 'المعروضات', fr: 'Expositions' } },
  { to: '/map', label: { en: 'Map', ar: 'الخريطة', fr: 'Carte' } },
  { to: '/chat', label: { en: 'Ask THOTH', ar: 'اسأل تحوت', fr: 'Demandez THOTH' } },
]

const LANGS: Language[] = ['en', 'ar', 'fr']

export default function Navbar() {
  const { lang, setLang } = useLanguage()
  const { pathname } = useLocation()

  return (
    <nav className="sticky top-0 z-50 bg-gem-navy/90 backdrop-blur border-b border-gem-gold/20">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <img src="/assets/logo.png" alt="THOTH" className="h-8 w-auto" />
          <span className="font-display text-gem-gold text-xl font-bold tracking-widest hidden sm:block">
            THOTH
          </span>
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(link => (
            <Link
              key={link.to}
              to={link.to}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                pathname === link.to
                  ? 'text-gem-gold bg-gem-gold/10'
                  : 'text-gem-muted hover:text-gem-text hover:bg-gem-card'
              )}
            >
              {link.label[lang]}
            </Link>
          ))}
        </div>

        {/* Language switcher */}
        <div className="flex items-center gap-1">
          {LANGS.map(l => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={clsx(
                'px-3 py-1 rounded-lg text-xs font-semibold uppercase transition-colors',
                lang === l
                  ? 'bg-gem-gold text-gem-navy'
                  : 'text-gem-muted hover:text-gem-gold border border-gem-gold/20 hover:border-gem-gold/50'
              )}
            >
              {l}
            </button>
          ))}
        </div>
      </div>
    </nav>
  )
}
