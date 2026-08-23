import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Copy, Download, FileSearch, Table2, X } from 'lucide-react'
import type { RunDetail } from '../types'
import { formatDuration, formatMetric, formatMoney, formatNumber, parserFor } from '../lib/format'
import { useLocale } from '../lib/i18n'
import { Badge, Button, EmptyState, LoadingState } from './ui'
import { convertCurrency, currencyPreference } from '../lib/currency'

function download(name: string, contents: string, type: string) {
  const url = URL.createObjectURL(new Blob([contents], { type }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  anchor.click()
  URL.revokeObjectURL(url)
}

function csvCell(value: unknown) { return `"${String(value ?? '').replaceAll('"', '""')}"` }

function MetricRing({ label, value, color }: { label: string; value: number | null | undefined; color: string }) {
  const numeric = Math.max(0, Math.min(100, Number(value) || 0))
  const radius = 34
  const circumference = 2 * Math.PI * radius
  return (
    <div className="result-metric-ring">
      <svg viewBox="0 0 84 84" aria-hidden="true"><circle cx="42" cy="42" r={radius} /><circle className="value" cx="42" cy="42" r={radius} style={{ stroke: color, strokeDasharray: `${numeric / 100 * circumference} ${circumference}` }} /></svg>
      <div><strong>{formatMetric(value)}</strong><span>{label}</span></div>
    </div>
  )
}

export function RunDrawer({ detail, loading, onClose }: { detail: RunDetail | null; loading: boolean; onClose: () => void }) {
  const { tr } = useLocale()
  return (
    <AnimatePresence initial={false}>
      {(detail || loading) && (
        <motion.section className="run-drawer run-inspector-inline" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} aria-label={tr('Run result sheet', '実行結果シート')}>
          {loading || !detail ? <LoadingState label={tr('Loading result sheet', '結果シートを読み込み中')} detail={tr('Assembling rows and metrics', '行と指標を準備しています')} /> : <ResultSheet detail={detail} onClose={onClose} />}
        </motion.section>
      )}
    </AnimatePresence>
  )
}

function ResultSheet({ detail, onClose }: { detail: RunDetail; onClose: () => void }) {
  const { tr, schemaText } = useLocale()
  const parser = parserFor(detail.strategy)
  const displayCurrency = currencyPreference()
  const answerUnit = `M ${displayCurrency.currency}`
  const exportCsv = () => {
    const header = [tr('Classification', '分類'), tr('Subclassification', '小分類'), tr('Item', '項目'), `${tr('Answer', '回答')} (${answerUnit})`]
    const rows = detail.rows.map((row) => [schemaText(row.classification), schemaText(row.subclassification), schemaText(row.item), row.accepted ? convertCurrency(row.answer_m_usd, detail.currency || 'USD', displayCurrency.currency, displayCurrency.jpyPerUsd) : null])
    download(`${detail.run_id}.csv`, [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\n'), 'text/csv;charset=utf-8')
  }
  return <>
    <header className="drawer-header">
      <div><Badge><Table2 size={13} /> {tr('Result sheet', '結果シート')}</Badge><h2>{detail.pdf_file || detail.run_id}</h2><p><i style={{ background: parser.color }} /> {parser.label} · FY{detail.fiscal_year || '—'} · {detail.model || tr('Unknown model', '不明なモデル')}</p></div>
      <div className="sheet-actions"><Button variant="secondary" onClick={exportCsv}><Download size={15} /> CSV</Button><Button variant="secondary" onClick={() => download(`${detail.run_id}.json`, JSON.stringify(detail, null, 2), 'application/json')}><Download size={15} /> JSON</Button><Button variant="ghost" onClick={onClose}><X size={18} /> {tr('Close table', '表を閉じる')}</Button></div>
    </header>
    <motion.div className="drawer-content" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="result-metric-rings">
        <MetricRing label={tr('Exact accuracy', '完全一致率')} value={detail.metrics.accuracy} color="#2563eb" />
        <MetricRing label={tr('Field coverage', 'フィールドカバレッジ')} value={detail.metrics.coverage} color="#10b981" />
        <MetricRing label={tr('Precision', '適合率')} value={detail.metrics.precision} color="#f59e0b" />
      </div>
      <div className="detail-strip">
        <div><span>{tr('Pages', 'ページ')}</span><strong>{formatNumber(detail.page_count)}</strong></div>
        <div><span>{tr('Estimated tokens', '推定トークン')}</span><strong>{formatNumber(detail.approx_input_tokens)}</strong></div>
        <div><span>{tr('Actual input tokens', '実入力トークン')}</span><strong>{formatNumber(detail.input_tokens ?? detail.usage?.prompt_tokens)}</strong></div>
        <div><span>{tr('Parse time', '解析時間')}</span><strong>{formatDuration(detail.extract_seconds)}</strong></div>
        <div><span>{tr('Total time', '合計時間')}</span><strong>{formatDuration(detail.total_seconds)}</strong></div>
        <Button variant="ghost" onClick={() => navigator.clipboard.writeText(detail.run_id)}><Copy size={14} /> {tr('Copy run ID', '実行IDをコピー')}</Button>
      </div>
      {detail.reconciliation && <section className={`reconciliation-summary ${detail.reconciliation.failed ? 'has-failures' : ''}`}>
        {detail.reconciliation.failed ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
        <div><strong>{detail.reconciliation.failed ? tr(`${detail.reconciliation.failed} balance-sheet identities need attention`, `貸借対照表の恒等式${detail.reconciliation.failed}件を要確認`) : tr('All evaluated balance-sheet identities reconcile', '評価対象の貸借対照表恒等式はすべて一致')}</strong><span>{tr(`${detail.reconciliation.passed} passed · ${detail.reconciliation.skipped} skipped because a component was unavailable`, `${detail.reconciliation.passed}件合格・構成要素不足で${detail.reconciliation.skipped}件スキップ`)}</span></div>
      </section>}
      {detail.evidence_retry?.attempted && <section className={`reconciliation-summary ${detail.evidence_retry.error ? 'has-failures' : ''}`}>
        {detail.evidence_retry.error ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
        <div>
          <strong>{detail.evidence_retry.error
            ? tr('Evidence retry failed — first-pass values kept', '追加根拠の再試行に失敗 — 初回の値を保持')
            : tr(`Evidence retry recovered ${detail.evidence_retry.recovered_rows?.length ?? 0} of ${detail.evidence_retry.missing_rows?.length ?? 0} unanswered rows`, `追加根拠の再試行で未回答${detail.evidence_retry.missing_rows?.length ?? 0}行中${detail.evidence_retry.recovered_rows?.length ?? 0}行を回復`)}</strong>
          <span>{detail.evidence_retry.error
            ? detail.evidence_retry.error
            : tr(`Pages ${(detail.evidence_retry.pages_added || []).join(', ') || '—'} were added in one bounded follow-up call; a retry can only fill nulls, never overwrite a value.`, `ページ${(detail.evidence_retry.pages_added || []).join('、') || '—'}を1回の追加呼び出しで送信。再試行は未回答行のみを補完し、既存の値を上書きしません。`)}</span>
        </div>
      </section>}
      <section className="drawer-section">
        <div className="drawer-section-title"><h3>{tr('Extracted balance-sheet rows', '抽出された貸借対照表項目')}</h3><Badge tone="green">{detail.rows.filter((row) => row.accepted).length}/27 {tr('accepted', '採用')}</Badge></div>
        {detail.rows.length ? <div className="result-table-wrap"><table className="sheet-table"><thead><tr><th>{tr('Classification', '分類')}</th><th>{tr('Subclassification', '小分類')}</th><th>{tr('Item', '項目')}</th><th>{tr('Answer', '回答')} ({answerUnit})</th></tr></thead><tbody>{detail.rows.map((row) => <tr className={!row.accepted ? 'is-rejected' : ''} key={row.item}><td>{schemaText(row.classification) || '—'}</td><td>{schemaText(row.subclassification) || '—'}</td><td><strong>{schemaText(row.item)}</strong></td><td className="numeric"><strong>{row.accepted ? formatMoney(convertCurrency(row.answer_m_usd, detail.currency || 'USD', displayCurrency.currency, displayCurrency.jpyPerUsd)) : '—'}</strong></td></tr>)}</tbody></table></div> : <EmptyState icon={<FileSearch size={20} />} title={tr('No rows', '行がありません')} description={tr('This run has no completed prediction rows.', 'この実行には完了した予測行がありません。')} />}
      </section>
    </motion.div>
  </>
}
