import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { getExhibits, getCategories, getHalls } from '../services/api'
import type { ExhibitLocalized, CategoryLocalized, HallLocalized } from '../types'

export default function ExhibitsPage() {
  const { lang } = useLanguage()
  const [exhibits, setExhibits] = useState<ExhibitLocalized[]>([])
  const [categories, setCategories] = useState<CategoryLocalized[]>([])
  const [halls, setHalls] = useState<HallLocalized[]>([])
  const [search, setSearch] = useState('')
  const [categoryId, setCategoryId] = useState<number | undefined>()
  const [hallId, setHallId] = useState<number | undefined>()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getCategories(lang), getHalls(lang)]).then(([cats, hs]) => {
      setCategories(cats)
      setHalls(hs)
    })
  }, [lang])

  useEffect(() => {
    setLoading(true)
    getExhibits(lang, { category_id: categoryId, hall_id: hallId, search: search || undefined })
      .then(setExhibits)
      .finally(() => setLoading(false))
  }, [lang, categoryId, hallId, search])

  return (
    <div className="max-w-7xl mx-auto px-4 py-10 animate-fade-in">
      <h1 className="gem-section-title mb-8">
        {lang === 'ar' ? 'المعروضات' : lang === 'fr' ? 'Expositions' : 'Exhibits'}
      </h1>

      {/* Filters */}
      <div className="gem-card p-4 mb-8 flex flex-wrap gap-3">
        <input
          type="text"
          className="gem-input max-w-xs"
          placeholder={lang === 'ar' ? 'بحث...' : lang === 'fr' ? 'Rechercher...' : 'Search...'}
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="gem-input max-w-xs"
          value={categoryId ?? ''}
          onChange={e => setCategoryId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">{lang === 'ar' ? 'كل الفئات' : lang === 'fr' ? 'Toutes catégories' : 'All Categories'}</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select
          className="gem-input max-w-xs"
          value={hallId ?? ''}
          onChange={e => setHallId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">{lang === 'ar' ? 'كل القاعات' : lang === 'fr' ? 'Toutes salles' : 'All Halls'}</option>
          {halls.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="gem-card h-64 animate-shimmer" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {exhibits.map(exhibit => (
            <Link key={exhibit.id} to={`/exhibits/${exhibit.id}`}>
              <div className="gem-card overflow-hidden group hover:border-gem-gold/50 transition-all duration-300 hover:-translate-y-1">
                <div className="h-48 bg-gem-dark overflow-hidden">
                  {exhibit.image_url ? (
                    <img
                      src={exhibit.image_url}
                      alt={exhibit.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-5xl text-gem-gold/20">𓅓</div>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-display text-gem-gold font-semibold mb-2 line-clamp-1">{exhibit.title}</h3>
                  {exhibit.era && (
                    <span className="text-xs text-gem-muted border border-gem-gold/20 px-2 py-0.5 rounded-full">
                      {exhibit.era}
                    </span>
                  )}
                  <p className="text-gem-muted text-sm mt-2 line-clamp-2">{exhibit.short_description}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && exhibits.length === 0 && (
        <p className="text-center text-gem-muted py-20 text-lg">
          {lang === 'ar' ? 'لا توجد معروضات' : lang === 'fr' ? 'Aucune exposition trouvée' : 'No exhibits found'}
        </p>
      )}
    </div>
  )
}
