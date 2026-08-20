import { Check, FileText, Files, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { CorpusDocument } from '../types'
import { useLocale } from '../lib/i18n'
import { Badge, EmptyState } from './ui'

export type CorpusSelectionMode = 'single' | 'batch'

export function CorpusPicker({
  documents,
  selected,
  mode,
  onModeChange,
  onSelectionChange,
}: {
  documents: CorpusDocument[]
  selected: string[]
  mode: CorpusSelectionMode
  onModeChange: (mode: CorpusSelectionMode) => void
  onSelectionChange: (ids: string[]) => void
}) {
  const { tr } = useLocale()
  const [query, setQuery] = useState('')
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return [...documents]
      .filter((document) => !needle || `${document.company} ${document.filename} ${document.fiscal_year}`.toLowerCase().includes(needle))
      .sort((left, right) => left.company.localeCompare(right.company) || right.fiscal_year - left.fiscal_year)
  }, [documents, query])

  const toggle = (document: CorpusDocument) => {
    if (document.screened === 'unreadable') return
    const exists = selected.includes(document.sha256)
    if (mode === 'single') onSelectionChange(exists ? [] : [document.sha256])
    else onSelectionChange(exists ? selected.filter((id) => id !== document.sha256) : [...selected, document.sha256])
  }

  const changeMode = (next: CorpusSelectionMode) => {
    onModeChange(next)
    if (next === 'single' && selected.length > 1) onSelectionChange(selected.slice(0, 1))
  }

  return (
    <div className="corpus-picker">
      <div className="corpus-picker-toolbar">
        <label className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={tr('Search company or year', '会社名または年度を検索')} /></label>
        <div className="segmented-control corpus-mode" aria-label={tr('Document selection mode', '文書選択モード')}>
          <button className={mode === 'single' ? 'is-active' : ''} onClick={() => changeMode('single')}><FileText size={14} /> {tr('Single', '単一')}</button>
          <button className={mode === 'batch' ? 'is-active' : ''} onClick={() => changeMode('batch')}><Files size={14} /> {tr('Batch', '一括')}</button>
        </div>
      </div>
      {!visible.length ? (
        <EmptyState icon={<Search size={19} />} title={tr('No available reports', '利用できるレポートがありません')} description={tr('Crawl reports in Report corpus or try another search.', 'レポートコーパスで取得するか、別の検索語をお試しください。')} />
      ) : (
        <div className="corpus-document-list">
          {visible.map((document) => {
            const checked = selected.includes(document.sha256)
            const disabled = document.screened === 'unreadable'
            return (
              <button className={`corpus-document-row ${checked ? 'is-selected' : ''}`} disabled={disabled} onClick={() => toggle(document)} key={document.sha256}>
                <span className="corpus-document-check">{checked && <Check size={14} strokeWidth={3} />}</span>
                <span className="corpus-document-copy"><strong>{document.company}</strong><small>FY{document.fiscal_year} · {document.filename}</small></span>
                <Badge tone={document.screened === 'ok' ? 'green' : document.screened === 'unreadable' ? 'red' : 'amber'}>{document.screened === 'ok' ? tr('Ready', '準備完了') : document.screened === 'review' ? tr('Review', '要確認') : tr('Unreadable', '読取不可')}</Badge>
              </button>
            )
          })}
        </div>
      )}
      <p className="corpus-picker-status">{tr(`${selected.length} stored report${selected.length === 1 ? '' : 's'} selected`, `${selected.length}件の保存済みレポートを選択`)}</p>
    </div>
  )
}
