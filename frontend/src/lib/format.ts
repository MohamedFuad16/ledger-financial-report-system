import type { MetricValue, RunSummary } from '../types'

export const parserMeta: Record<string, { short: string; label: string; color: string }> = {
  s1: { short: 'PyPDF', label: 'Strategy 1 · PyPDF', color: '#2563eb' },
  s2: { short: 'PyMuPDF', label: 'Strategy 2 · PyMuPDF4LLM', color: '#10b981' },
  's2-docling': { short: 'Docling', label: 'Strategy 2 · Docling', color: '#ef4444' },
  's2-inspector': { short: 'Inspector', label: 'Strategy 2 · pdf-inspector', color: '#f59e0b' },
}

export function parserFor(key?: string) {
  return parserMeta[key || ''] || { short: key || 'Unknown', label: key || 'Unknown', color: '#777' }
}

export function formatMetric(value: MetricValue, suffix = '%') {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? '—'
    : `${Number(value).toFixed(1)}${suffix}`
}

export function formatNumber(value: MetricValue, digits = 0) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? '—'
    : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits })
}

export function formatMoney(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  const absolute = Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 1 })
  return value < 0 ? `(${absolute})` : absolute
}

export function formatDuration(value: MetricValue) {
  if (value === null || value === undefined) return '—'
  const seconds = Number(value)
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

export function displayDate(run: RunSummary) {
  const rawStamp = run.timestamp || run.run_id
  const stamp = rawStamp.match(/\d{8}T\d{6}Z/)?.[0]
  if (!stamp) return '—'
  const compact = stamp.replace(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z/, '$1-$2-$3T$4:$5:$6Z')
  const date = new Date(compact)
  return Number.isNaN(date.getTime())
    ? stamp
    : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date)
}

export function displayReportName(name?: string, fiscalYear?: string | number | null) {
  const original = (name || '').split(/[\\/]/).pop() || ''
  const year = String(fiscalYear || original.match(/(?:19|20)\d{2}/)?.[0] || '').match(/(?:19|20)\d{2}/)?.[0]
  if (!year) return original || 'Annual report'
  const company = original
    .replace(/\.pdf$/i, '')
    .replace(/^\d{8}T\d{6}Z_\d{3}_/, '')
    .replace(/annual[\s_-]*report|form[\s_-]*10[\s_-]*k/gi, '_')
    .replace(/(?:19|20)\d{2}/g, '_')
    .replace(/[^A-Za-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'Unknown_Company'
  return `${company}_annual_report_${year}.pdf`
}

export function reportCohortKey(run: RunSummary) {
  const file = (run.pdf_file || '').split(/[\\/]/).pop()?.trim().toLowerCase()
  const year = String(run.fiscal_year || run.detected_fiscal_year || '').match(/(?:19|20)\d{2}/)?.[0] || ''
  return file ? `${file}::${year}` : ''
}

/**
 * Return only reports represented by every parser that has scored data.
 * Repeated runs stay in the cohort, but parser statistics first average those
 * repeats per report so rerunning one parser cannot silently weight it more.
 */
export function matchedParserCohort(runs: RunSummary[]) {
  const scored = runs.filter((run) => run.accuracy != null && reportCohortKey(run))
  const strategies = [...new Set(scored.map((run) => run.strategy))]
  if (!strategies.length) return []
  const strategiesByReport = scored.reduce<Map<string, Set<string>>>((groups, run) => {
    const key = reportCohortKey(run)
    const present = groups.get(key) || new Set<string>()
    present.add(run.strategy)
    groups.set(key, present)
    return groups
  }, new Map())
  const matchedReports = new Set(
    [...strategiesByReport.entries()]
      .filter(([, present]) => strategies.every((strategy) => present.has(strategy)))
      .map(([key]) => key),
  )
  return scored.filter((run) => matchedReports.has(reportCohortKey(run)))
}

export function groupParserStats(runs: RunSummary[]) {
  const cohort = matchedParserCohort(runs)
  return Object.entries(parserMeta).map(([key, meta]) => {
    const relevant = cohort.filter((run) => run.strategy === key)
    const byReport = Object.values(relevant.reduce<Record<string, RunSummary[]>>((groups, run) => {
      const report = reportCohortKey(run)
      ;(groups[report] ||= []).push(run)
      return groups
    }, {}))
    const average = (field: keyof RunSummary) => {
      const reportMeans = byReport.map((reportRuns) => {
        const values = reportRuns.map((run) => run[field]).filter((value) => value != null).map(Number).filter(Number.isFinite)
        return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
      }).filter((value): value is number => value != null)
      return reportMeans.length ? reportMeans.reduce((sum, value) => sum + value, 0) / reportMeans.length : null
    }
    return {
      key,
      ...meta,
      runs: byReport.length,
      observations: relevant.length,
      accuracy: average('accuracy'),
      coverage: average('coverage'),
      precision: average('precision'),
      extractSeconds: average('extract_seconds'),
    }
  })
}

export function parserMetricLeaders(
  stats: ReturnType<typeof groupParserStats>,
  field: 'accuracy' | 'coverage' | 'precision',
) {
  const available = stats.filter((entry) => entry[field] != null && Number.isFinite(Number(entry[field])))
  if (!available.length) return []
  const displayed = (value: number | null) => Math.round(Number(value) * 10) / 10
  const maximum = Math.max(...available.map((entry) => displayed(entry[field])))
  return available.filter((entry) => displayed(entry[field]) === maximum)
}
