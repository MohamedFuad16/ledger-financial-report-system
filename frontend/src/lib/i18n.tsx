import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'

export type Locale = 'en' | 'ja'

type LocaleContextValue = {
  locale: Locale
  setLocale: (locale: Locale) => void
  tr: (english: string, japanese: string) => string
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

function initialLocale(): Locale {
  try {
    const saved = window.localStorage?.getItem('ledger-locale')
    if (saved === 'en' || saved === 'ja') return saved
  } catch {
    // Storage can be unavailable in embedded or privacy-restricted browsers.
  }
  return typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('ja') ? 'ja' : 'en'
}

export function LocaleProvider({ children }: PropsWithChildren) {
  const [locale, setLocale] = useState<Locale>(initialLocale)

  useEffect(() => {
    try {
      window.localStorage?.setItem('ledger-locale', locale)
    } catch {
      // The in-memory locale still works when persistence is unavailable.
    }
    document.documentElement.lang = locale
  }, [locale])

  const value = useMemo<LocaleContextValue>(() => ({
    locale,
    setLocale,
    tr: (english, japanese) => locale === 'ja' ? japanese : english,
  }), [locale])

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale() {
  const context = useContext(LocaleContext)
  if (!context) throw new Error('useLocale must be used inside LocaleProvider')
  return context
}
