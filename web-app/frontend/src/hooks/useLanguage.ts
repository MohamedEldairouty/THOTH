import { useState, useCallback } from 'react'
import type { Language } from '../types'

const STORAGE_KEY = 'thoth_lang'

export function useLanguage() {
  const [lang, setLangState] = useState<Language>(
    () => (localStorage.getItem(STORAGE_KEY) as Language) || 'en'
  )

  const setLang = useCallback((l: Language) => {
    localStorage.setItem(STORAGE_KEY, l)
    setLangState(l)
    document.documentElement.dir = l === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = l
  }, [])

  return { lang, setLang }
}
