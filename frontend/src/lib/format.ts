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

export function groupParserStats(runs: RunSummary[]) {
  return Object.entries(parserMeta).map(([key, meta]) => {
    const relevant = runs.filter((run) => run.strategy === key && run.accuracy != null)
    const average = (field: keyof RunSummary) => {
      const values = relevant.map((run) => run[field]).filter((value) => value != null).map(Number).filter(Number.isFinite)
      return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
    }
    return {
      key,
      ...meta,
      runs: relevant.length,
      accuracy: average('accuracy'),
      coverage: average('coverage'),
      precision: average('precision'),
      extractSeconds: average('extract_seconds'),
    }
  })
}
