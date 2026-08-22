import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'

export type Locale = 'en' | 'ja'

type LocaleContextValue = {
  locale: Locale
  setLocale: (locale: Locale) => void
  tr: (english: string, japanese: string) => string
  schemaText: (value: string | null | undefined) => string
}

const japaneseSchemaText: Record<string, string> = {
  'Current Assets': '流動資産',
  'Quick Assets': '短期投資',
  'Cash & Cash Equivalents': '現金及び現金同等物',
  'Accounts Receivable - Trade': '売掛金',
  'Other Quick Assets': 'その他の短期投資',
  'Inventories, Net': '棚卸資産',
  'Other Current Assets': 'その他の流動資産',
  'Other Current Assets (subtotal)': 'その他の流動資産（小計）',
  'Marketable Securities': '有価証券',
  'Short-term Loan': '短期貸付金',
  'Advance Payments': '前払金',
  'Fixed Assets': '固定資産',
  'Tangible Assets': '有形固定資産',
  Land: '土地',
  Buildings: '建物',
  'Plant & Machinery': '機械装置',
  'Construction in Progress': '建設仮勘定',
  'Other Equipment': 'その他の設備',
  'Accumulated Depreciation': '減価償却累計額',
  'Intangible Assets': '無形固定資産',
  'Financial Assets': '金融資産',
  Investments: '投資',
  'Long-term Loan': '長期貸付金',
  'Other Financial Assets': 'その他の金融資産',
  'Other Fixed Assets': 'その他の固定資産',
  'Deferred Charges': '繰延資産',
  'Total Assets': '総資産',
  'Quick Assets + Inventories, Net + Other Current Assets': '短期投資、棚卸資産、その他の流動資産の合計。',
  'Cash & Cash Equivalents + Accounts Receivable - Trade + Other Quick Assets': '現金及び現金同等物、売掛金、その他の短期投資の合計。',
  'Cash and assets immediately convertible to cash.': '手元の現金とすぐに現金化できる資産。',
  'Trade receivables arising from sales to customers.': '顧客への売上から生じる営業債権。',
  'Other short-term liquid assets that belong in Quick Assets.': '短期投資に含まれるその他の短期流動資産。',
  'Inventory held for sale or use in production, net of applicable allowances.': '販売または生産のために保有する在庫から必要な評価性引当額を控除した金額。',
  'Marketable Securities + Short-term Loan + Advance Payments + Other Current Assets': '有価証券、短期貸付金、前払金、その他の流動資産の合計。',
  'Current marketable or tradable securities.': '流動資産に分類される市場性のある有価証券。',
  'Loan receivable expected to be collected within one year.': '1年以内に回収予定の貸付金。',
  'Amounts paid in advance that are classified as current assets.': '流動資産に分類される前払額。',
  'Other current assets not classified in the preceding requested fields.': '上記の項目に分類されないその他の流動資産。',
  'Tangible Assets + Intangible Assets + Financial Assets + Other Fixed Assets': '有形固定資産、無形固定資産、金融資産、その他の固定資産の合計。',
  'Land + Buildings + Plant & Machinery + Construction in Progress + Other Equipment + Accumulated Depreciation': '土地、建物、機械装置、建設仮勘定、その他の設備、減価償却累計額の合計。',
  'Owned land classified as tangible fixed assets.': '有形固定資産に分類される所有土地。',
  'Buildings such as offices, factories and warehouses.': '事務所、工場、倉庫などの建物。',
  'Production and operating plant and machinery.': '生産と操業に使用する工場設備および機械。',
  'Tangible assets under construction.': '建設中の有形固定資産。',
  'Other equipment and fixtures classified as tangible fixed assets.': '有形固定資産に分類されるその他の設備・備品。',
  'Cumulative depreciation deducted from tangible assets. Preserve the negative sign.': '有形固定資産から控除する減価償却累計額。負の符号を維持する。',
  'Non-physical long-lived assets.': '物理的実体のない長期資産。',
  'Investments + Long-term Loan + Other Financial Assets': '投資、長期貸付金、その他の金融資産の合計。',
  'Long-term investments classified as financial assets.': '金融資産に分類される長期投資。',
  'Loan receivable expected to be collected after one year.': '1年後以降に回収予定の貸付金。',
  'Other long-term financial assets not classified above.': '上記に分類されないその他の長期金融資産。',
  'Other long-lived assets not classified in tangible, intangible or financial assets.': '有形、無形、金融資産に分類されないその他の長期資産。',
  'Deferred costs recognized across accounting periods.': '複数の会計期間にわたって認識される繰延費用。',
  'Current Assets + Fixed Assets + Deferred Charges': '流動資産、固定資産、繰延資産の合計。',
}

const englishSchemaText = Object.fromEntries(
  Object.entries(japaneseSchemaText).map(([english, japanese]) => [japanese, english]),
)

export function localizeSchemaText(value: string | null | undefined, locale: Locale): string {
  if (!value) return ''
  const english = englishSchemaText[value] || value
  return locale === 'ja' ? japaneseSchemaText[english] || value : english
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
    schemaText: (text) => localizeSchemaText(text, locale),
  }), [locale])

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale() {
  const context = useContext(LocaleContext)
  if (!context) throw new Error('useLocale must be used inside LocaleProvider')
  return context
}
