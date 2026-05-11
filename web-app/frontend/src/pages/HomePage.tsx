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
    <div className="relative min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center overflow-hidden px-4">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gem-gradient opacity-80 pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gem-gold/5 rounded-full blur-3xl pointer-events-none" />

      {/* Hieroglyph strip */}
      <div className="relative z-10 mb-8 text-gem-gold/30 text-4xl tracking-widest select-none">
        𓃀 𓇋 𓏏 𓄂 𓅓 𓏏 𓃀 𓇋 𓏏
      </div>

      {/* Main content */}
      <div className="relative z-10 text-center max-w-3xl animate-fade-in">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gem-gold/10 border border-gem-gold/40 flex items-center justify-center text-4xl">
          𓅓
        </div>
        <h1 className="font-display text-gem-gold text-3xl md:text-5xl font-bold mb-4 tracking-wider">
          {t.greeting}
        </h1>
        <p className="text-gem-muted text-lg md:text-xl mb-10 leading-relaxed">
          {t.subtitle}
        </p>

        {/* Action buttons */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link to="/exhibits" className="gem-btn-primary text-center">
            {t.startTour}
          </Link>
          <Link to="/exhibits" className="gem-btn-ghost text-center">
            {t.browseExhibits}
          </Link>
          <Link to="/chat" className="gem-btn-ghost text-center">
            {t.askThoth}
          </Link>
          <Link to="/map" className="gem-btn-ghost text-center">
            {t.viewMap}
          </Link>
        </div>
      </div>

      {/* Bottom divider */}
      <div className="relative z-10 mt-16 text-gem-gold/20 text-2xl tracking-widest select-none">
        ─── 𓆣 ─── 𓋴 ─── 𓆣 ───
      </div>
    </div>
  )
}
