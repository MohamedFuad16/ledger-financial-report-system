export type DisplayCurrency = 'USD' | 'JPY'

export interface CurrencyPreference {
  currency: DisplayCurrency
  jpyPerUsd: number
}

const DEFAULT_JPY_PER_USD = 150

export function currencyPreference(): CurrencyPreference {
  try {
    const currency = window.localStorage.getItem('ledger-output-currency') === 'JPY' ? 'JPY' : 'USD'
    const storedRate = Number(window.localStorage.getItem('ledger-jpy-per-usd'))
    return { currency, jpyPerUsd: Number.isFinite(storedRate) && storedRate > 0 ? storedRate : DEFAULT_JPY_PER_USD }
  } catch {
    return { currency: 'USD', jpyPerUsd: DEFAULT_JPY_PER_USD }
  }
}

export function saveCurrencyPreference(preference: CurrencyPreference) {
  window.localStorage.setItem('ledger-output-currency', preference.currency)
  window.localStorage.setItem('ledger-jpy-per-usd', String(preference.jpyPerUsd))
}

export function convertCurrency(value: number | null | undefined, source: string, target: DisplayCurrency, jpyPerUsd: number) {
  if (value == null) return null
  const normalizedSource = String(source || 'USD').toUpperCase()
  if (normalizedSource === target) return value
  if (normalizedSource === 'JPY' && target === 'USD') return value / jpyPerUsd
  if (normalizedSource === 'USD' && target === 'JPY') return value * jpyPerUsd
  return value
}

export function restoreNativeCurrency(value: number | null, nativeCurrency: string, preference: CurrencyPreference) {
  if (value == null) return null
  const normalizedNative = String(nativeCurrency || 'USD').toUpperCase()
  if (normalizedNative === preference.currency) return value
  if (normalizedNative === 'JPY' && preference.currency === 'USD') return value * preference.jpyPerUsd
  if (normalizedNative === 'USD' && preference.currency === 'JPY') return value / preference.jpyPerUsd
  return value
}
