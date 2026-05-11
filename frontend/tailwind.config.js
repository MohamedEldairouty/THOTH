/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Grand Egyptian Museum palette
        'gem-navy': '#0a0e1a',
        'gem-dark': '#111827',
        'gem-card': '#1a2235',
        'gem-gold': '#c9a84c',
        'gem-gold-light': '#e8c96a',
        'gem-gold-dim': '#8a6f2e',
        'gem-accent': '#d4af37',
        'gem-text': '#e8e0d0',
        'gem-muted': '#8b8070',
      },
      fontFamily: {
        display: ['"Cinzel"', 'serif'],
        body: ['"Inter"', 'sans-serif'],
        arabic: ['"Noto Sans Arabic"', 'sans-serif'],
      },
      backgroundImage: {
        'gem-gradient': 'linear-gradient(135deg, #0a0e1a 0%, #1a1430 50%, #0a0e1a 100%)',
        'gold-gradient': 'linear-gradient(90deg, #c9a84c 0%, #e8c96a 50%, #c9a84c 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(20px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        shimmer: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
