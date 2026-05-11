import { Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'

const COPY = {
  en: {
    greeting: 'Welcome to the Grand Egyptian Museum',
    subtitle: 'I am THOTH — your intelligent museum guide. Explore 5,000 years of ancient Egyptian history.',
    startTour: 'Start Tour',
    browseExhibits: 'Browse Exhibits',
    askThoth: 'Ask THOTH',
    viewMap: 'View Museum Map',
  },
  ar: {
    greeting: 'مرحباً بكم في المتحف المصري الكبير',
    subtitle: 'أنا تحوت — مرشدك الذكي في المتحف. استكشف 5000 عام من تاريخ مصر القديمة.',
    startTour: 'ابدأ الجولة',
    browseExhibits: 'تصفح المعروضات',
    askThoth: 'اسأل تحوت',
    viewMap: 'عرض خريطة المتحف',
  },
  fr: {
    greeting: 'Bienvenue au Grand Musée Égyptien',
    subtitle: "Je suis THOTH — votre guide intelligent du musée. Explorez 5 000 ans d'histoire de l'Égypte ancienne.",
    startTour: 'Commencer la visite',
    browseExhibits: 'Parcourir les expositions',
    askThoth: 'Demandez à THOTH',
    viewMap: 'Voir le plan du musée',
  },
}

export default function HomePage() {
  const { lang } = useLanguage()
  const t = COPY[lang]

  return (
    <div className="relative min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center overflow-hidden">

      {/* GEM wallpaper */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: 'url(/assets/gem_wallpaper.jpg)' }}
      />
      {/* Dark overlay */}
      <div className="absolute inset-0 bg-gem-navy/60" />
      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-gem-navy to-transparent" />

      {/* Main content — glassmorphism card */}
      <div className="relative z-10 w-full max-w-3xl px-6 animate-fade-in">
        <div className="bg-gem-navy/60 backdrop-blur-md border border-gem-gold/25 rounded-3xl px-8 py-10 text-center shadow-[0_8px_60px_rgba(0,0,0,0.6)]">

          {/* Logo */}
          <div className="flex justify-center mb-5">
            <img
              src="/assets/logo.png"
              alt="THOTH Logo"
              className="h-20 w-auto drop-shadow-[0_0_24px_rgba(201,168,76,0.7)]"
            />
          </div>

          {/* Title */}
          <h1 className="font-display text-gem-gold text-3xl md:text-5xl font-bold mb-4 tracking-wider">
            {t.greeting}
          </h1>

          {/* Gold divider */}
          <div className="flex items-center gap-3 my-5 justify-center">
            <div className="h-px w-16 bg-gem-gold/40" />
            <span className="text-gem-gold/60 text-lg">𓀃</span>
            <div className="h-px w-16 bg-gem-gold/40" />
          </div>

          {/* Subtitle */}
          <p className="text-gem-text/90 text-lg md:text-xl mb-8 leading-relaxed">
            {t.subtitle}
          </p>

          {/* Action buttons */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Link to="/exhibits" className="gem-btn-primary text-center text-sm">
              {t.startTour}
            </Link>
            <Link to="/exhibits" className="gem-btn-primary text-center text-sm">
              {t.browseExhibits}
            </Link>
            <Link to="/chat" className="gem-btn-primary text-center text-sm">
              {t.askThoth}
            </Link>
            <Link to="/map" className="gem-btn-primary text-center text-sm">
              {t.viewMap}
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom divider */}
      <div className="relative z-10 mt-16 text-gem-gold/20 text-2xl tracking-widest select-none">
        𓃀 𓇋 𓏏 𓄂 𓅓 𓏏 𓃀 𓇋 𓏏
      </div>
    </div>
  )
}
