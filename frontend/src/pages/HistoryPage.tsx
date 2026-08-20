import { Search, SlidersHorizontal, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { RunSummary } from '../types'
import { parserMeta } from '../lib/format'
import { RunTable } from '../components/RunTable'
import { Badge, Button, Card, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

export function HistoryPage({ runs, onDeleteRun, onDeleteRuns, onDeleteAllRuns }: { runs: RunSummary[]; onDeleteRun: (run: RunSummary) => void; onDeleteRuns: (runs: RunSummary[]) => void; onDeleteAllRuns: () => void }) {
  const { tr } = useLocale()
  const [query, setQuery] = useState('')
  const [parser, setParser] = useState('all')
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const filtered = useMemo(() => runs.filter((run) => {
    const matchesParser = parser === 'all' || run.strategy === parser
    const haystack = `${run.run_id} ${run.pdf_file} ${run.fiscal_year} FY${run.fiscal_year} ${run.model}`.toLowerCase()
    return matchesParser && haystack.includes(query.toLowerCase())
  }), [runs, parser, query])
  useEffect(() => setSelectedRunIds((current) => current.filter((id) => runs.some((run) => run.run_id === id))), [runs])

  return (
    <div className="page">
      <header className="page-header"><div><Badge>{tr('Experiment library', '実験ライブラリ')}</Badge><h1>{tr('Run history', '実行履歴')}</h1><p>{tr('Every extraction, parser decision, timing record, and benchmark score in one searchable ledger.', 'すべての抽出、パーサー選択、時間記録、ベンチマークスコアを検索できます。')}</p></div></header>
      <Card className="history-card">
        <SectionHeading eyebrow={tr('Records', '記録')} title={tr(`${filtered.length} experiment${filtered.length === 1 ? '' : 's'}`, `${filtered.length}件の実験`)} description={tr('Open any row to review the extracted table and source evidence.', '任意の行を開いて抽出表と出典証拠を確認できます。')} />
        <div className="table-toolbar">
          <label className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={tr('Search file, year, model, or run ID', 'ファイル、年度、モデル、実行IDを検索')} /></label>
          <label className="select-field"><SlidersHorizontal size={15} /><select value={parser} onChange={(event) => setParser(event.target.value)}><option value="all">{tr('All parsers', 'すべてのパーサー')}</option>{Object.entries(parserMeta).map(([key, meta]) => <option key={key} value={key}>{meta.short}</option>)}</select></label>
          <div className="history-bulk-actions">
            <Button variant="ghost" disabled={!selectedRunIds.length} onClick={() => onDeleteRuns(runs.filter((run) => selectedRunIds.includes(run.run_id)))}><Trash2 size={14} /> {tr(`Delete selected (${selectedRunIds.length})`, `選択項目を削除（${selectedRunIds.length}）`)}</Button>
            <Button variant="ghost" disabled={!runs.length} onClick={onDeleteAllRuns}><Trash2 size={14} /> {tr('Delete all runs', 'すべての実行を削除')}</Button>
          </div>
        </div>
        <RunTable
          runs={filtered}
          onDelete={onDeleteRun}
          selectable
          selectedRunIds={selectedRunIds}
          onSelectionChange={setSelectedRunIds}
          emptyTitle={query || parser !== 'all' ? tr('No matching experiments', '一致する実験がありません') : undefined}
          emptyDescription={query || parser !== 'all' ? tr('Try a broader search or select a different parser.', '検索範囲を広げるか別のパーサーを選択してください。') : undefined}
        />
      </Card>
    </div>
  )
}
