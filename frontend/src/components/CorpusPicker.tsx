import { Check, ChevronDown, ChevronRight, FileText, Files, Search } from 'lucide-react'
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
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set())
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return [...documents]
      .filter((document) => !needle || `${document.company} ${document.filename} ${document.fiscal_year}`.toLowerCase().includes(needle))
      .sort((left, right) => left.company.localeCompare(right.company) || right.fiscal_year - left.fiscal_year)
  }, [documents, query])
  const groups = useMemo(() => Object.values(visible.reduce<Record<string, CorpusDocument[]>>((result, document) => {
    ;(result[document.company] ||= []).push(document)
    return result
  }, {})), [visible])

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

  const toggleCompany = (company: string) => setExpandedCompanies((current) => {
    const next = new Set(current)
    if (next.has(company)) next.delete(company)
    else next.add(company)
    return next
  })

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
          {groups.flatMap((companyDocuments) => {
            const company = companyDocuments[0].company
            const selectedCount = companyDocuments.filter((document) => selected.includes(document.sha256)).length
            const expanded = expandedCompanies.has(company) || Boolean(query.trim())
            const rows = [<button className="corpus-company-picker-row" type="button" onClick={() => toggleCompany(company)} aria-expanded={expanded} key={`company-${company}`}>
              {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
              <span><strong>{company}</strong><small>{companyDocuments.length} {tr(companyDocuments.length === 1 ? 'fiscal year' : 'fiscal years', '年度')}</small></span>
              {selectedCount > 0 && <Badge tone="blue">{selectedCount} {tr('selected', '選択')}</Badge>}
            </button>]
            if (!expanded) return rows
            return rows.concat(companyDocuments.map((document) => {
              const checked = selected.includes(document.sha256)
              const disabled = document.screened === 'unreadable'
              return <button className={`corpus-document-row corpus-company-year-option ${checked ? 'is-selected' : ''}`} disabled={disabled} onClick={() => toggle(document)} key={document.sha256}>
                <span className="corpus-document-check">{checked && <Check size={14} strokeWidth={3} />}</span>
                <span className="corpus-document-copy"><strong>FY{document.fiscal_year}</strong><small>{document.filename}</small></span>
                <Badge tone={document.verification_status === 'human_review_required' ? 'amber' : document.screened === 'unreadable' ? 'red' : 'green'}>{document.verification_status === 'assignment_supplied' ? tr('Assignment gold', '課題正解') : document.verification_status === 'human_verified' || document.verification_status === 'independently_verified' ? tr('Verified', '確認済み') : document.screened === 'unreadable' ? tr('Unreadable', '読取不可') : tr('Review', '確認')}</Badge>
              </button>
            }))
          })}
        </div>
      )}
      <p className="corpus-picker-status">{tr(`${selected.length} stored report${selected.length === 1 ? '' : 's'} selected`, `${selected.length}件の保存済みレポートを選択`)}</p>
    </div>
  )
}
