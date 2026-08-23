import { Fragment, useState } from 'react'
import { AlertCircle, Download, FileText, Trash2 } from 'lucide-react'
import type { RunDetail, RunSummary } from '../types'
import { api } from '../lib/api'
import { displayDate, displayReportName, formatDuration, formatMetric, formatNumber, parserFor } from '../lib/format'
import { Badge, Button, EmptyState } from './ui'
import { useLocale } from '../lib/i18n'
import { RunDrawer } from './RunDrawer'

export function RunTable({
  runs,
  onDelete,
  selectable = false,
  selectedRunIds = [],
  onSelectionChange,
  compact = false,
  emptyTitle,
  emptyDescription,
}: {
  runs: RunSummary[]
  onDelete?: (run: RunSummary) => void
  selectable?: boolean
  selectedRunIds?: string[]
  onSelectionChange?: (ids: string[]) => void
  compact?: boolean
  emptyTitle?: string
  emptyDescription?: string
}) {
  const { tr } = useLocale()
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null)
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null)
  const [detailError, setDetailError] = useState('')

  const openRun = async (run: RunSummary) => {
    if (expandedRunId === run.run_id) {
      setExpandedRunId(null); setDetail(null); setDetailError('')
      return
    }
    setExpandedRunId(run.run_id); setDetail(null); setDetailError(''); setLoadingRunId(run.run_id)
    try { setDetail(await api.run(run.run_id)) }
    catch (error) { setDetailError(error instanceof Error ? error.message : tr('Could not load this run.', 'この実行を読み込めませんでした。')) }
    finally { setLoadingRunId(null) }
  }
  const exportRun = async (run: RunSummary) => {
    const detail = await api.run(run.run_id)
    const url = URL.createObjectURL(new Blob([JSON.stringify(detail, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${run.run_id}.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }
  if (!runs.length) {
    return <EmptyState icon={<FileText size={20} />} title={emptyTitle || tr('No experiment runs yet', '実験実行はまだありません')} description={emptyDescription || tr('Completed extractions will appear here with their parser, timing, and benchmark score.', '完了した抽出はパーサー、時間、ベンチマークスコアとともにここに表示されます。')} />
  }

  return (
    <div className="table-wrap">
      <table className="run-table">
        <thead>
          <tr>
            {selectable && <th className="selection-cell"><input type="checkbox" aria-label={tr('Select all visible runs', '表示中の実行をすべて選択')} checked={runs.length > 0 && runs.every((run) => selectedRunIds.includes(run.run_id))} onChange={(event) => onSelectionChange?.(event.target.checked ? runs.map((run) => run.run_id) : [])} /></th>}
            <th>{tr('Experiment', '実験')}</th>
            <th>{tr('Parser', 'パーサー')}</th>
            <th>{tr('Accuracy', '正確度')}</th>
            <th>{tr('Coverage', 'カバレッジ')}</th>
            {!compact && <th>{tr('Pages', 'ページ')}</th>}
            {!compact && <th>{tr('Input tokens', '入力トークン')}</th>}
            {!compact && <th>{tr('Parse time', '解析時間')}</th>}
            {!compact && <th>{tr('Total time', '合計時間')}</th>}
            {!compact && <th>{tr('Consistency', '整合性')}</th>}
            <th aria-label={tr('Actions', '操作')} />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const parser = parserFor(run.strategy)
            const expanded = expandedRunId === run.run_id
            const columnCount = (compact ? 5 : 10) + (selectable ? 1 : 0)
            return (
              <Fragment key={run.run_id}>
              <tr className={expanded ? 'is-expanded' : ''}>
                {selectable && <td className="selection-cell"><input type="checkbox" aria-label={tr(`Select ${run.pdf_file || run.run_id}`, `${run.pdf_file || run.run_id}を選択`)} checked={selectedRunIds.includes(run.run_id)} onChange={(event) => onSelectionChange?.(event.target.checked ? [...selectedRunIds, run.run_id] : selectedRunIds.filter((id) => id !== run.run_id))} /></td>}
                <td>
                  <button className="run-title" onClick={() => openRun(run)} aria-expanded={expanded}>
                    <span className="file-avatar"><FileText size={15} /></span>
                    <span>
                      <strong>{displayReportName(run.pdf_file, run.fiscal_year)}</strong>
                      <small>FY{run.fiscal_year || '—'} · {displayDate(run)}</small>
                    </span>
                  </button>
                </td>
                <td><Badge tone="neutral"><i style={{ background: parser.color }} />{parser.short}</Badge></td>
                <td className="numeric"><strong>{formatMetric(run.accuracy)}</strong></td>
                <td className="numeric">{formatMetric(run.coverage)}</td>
                {!compact && <td className="numeric">{formatNumber(run.page_count)}</td>}
                {!compact && <td className="numeric"><strong>{formatNumber(run.input_tokens ?? run.approx_input_tokens)}</strong><small>{run.input_tokens != null ? tr('actual', '実測') : tr('estimated', '推定')}</small></td>}
                {!compact && <td className="numeric">{formatDuration(run.extract_seconds)}</td>}
                {!compact && <td className="numeric">{formatDuration(run.total_seconds)}</td>}
                {!compact && <td className="numeric">{formatMetric(run.consistency)}</td>}
                <td>
                  <div className="row-actions">
                    <Button variant="secondary" onClick={() => openRun(run)}>{expanded ? tr('Close table', '表を閉じる') : tr('View table', '表を表示')}</Button>
                    <Button variant="ghost" onClick={() => exportRun(run)}><Download size={14} /> {tr('Export', 'エクスポート')}</Button>
                    {onDelete && <Button variant="ghost" onClick={() => onDelete(run)}><Trash2 size={14} /> {tr('Delete', '削除')}</Button>}
                  </div>
                </td>
              </tr>
              {expanded && <tr className="run-expansion-row"><td colSpan={columnCount}>
                {detailError ? <div className="run-expansion-error"><AlertCircle size={17} />{detailError}</div> : <RunDrawer detail={detail} loading={loadingRunId === run.run_id} onClose={() => { setExpandedRunId(null); setDetail(null) }} />}
              </td></tr>}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
