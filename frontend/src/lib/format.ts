import type { MetricValue, RunSummary } from '../types'

export const parserMeta: Record<string, { short: string; label: string; color: string }> = {
  s1: { short: 'PyPDF', label: 'No OCR · PyPDF', color: '#2563eb' },
  's1-pymupdf': { short: 'PyMuPDF', label: 'No OCR · PyMuPDF4LLM', color: '#10b981' },
  's1-docling': { short: 'Docling', label: 'No OCR · Docling', color: '#ef4444' },
  's1-inspector': { short: 'Inspector', label: 'No OCR · pdf-inspector', color: '#f59e0b' },
  's2-pypdf': { short: 'PyPDF', label: 'OCR · PyPDF', color: '#2563eb' },
  s2: { short: 'PyMuPDF', label: 'OCR · PyMuPDF4LLM', color: '#10b981' },
  's2-docling': { short: 'Docling', label: 'OCR · Docling', color: '#ef4444' },
  's2-inspector': { short: 'Inspector', label: 'OCR · pdf-inspector', color: '#f59e0b' },
  s3: { short: 'Inspector Gate', label: 'Strategy 3 · pdf-inspector + intelligent scanning gate', color: '#8b5cf6' },
}

export type BenchmarkExperiment = 'no_ocr' | 'ocr' | 'intelligent_scan'
export type StrategyPageKind = 's1' | 's2' | 's3'

export const experimentStrategies: Record<BenchmarkExperiment, string[]> = {
  no_ocr: ['s1', 's1-pymupdf', 's1-inspector', 's1-docling'],
  ocr: ['s2-pypdf', 's2', 's2-inspector', 's2-docling'],
  intelligent_scan: ['s3'],
}

export const comparisonExperimentMeta = {
  no_ocr: { label: 'No OCR', color: '#2563eb' },
  ocr: { label: 'OCR enabled', color: '#10b981' },
  intelligent_scan: { label: 'Intelligent scanning', color: '#8b5cf6' },
} as const

export function experimentForStrategyPage(kind: StrategyPageKind): BenchmarkExperiment {
  if (kind === 's1') return 'no_ocr'
  if (kind === 's2') return 'ocr'
  return 'intelligent_scan'
}

export function extractionJobBelongsToStrategyPage(scope: StrategyPageKind, kind: StrategyPageKind) {
  return scope === kind
}

export function runBelongsToStrategyPage(run: RunSummary, kind: StrategyPageKind) {
  const experiment = experimentForStrategyPage(kind)
  return run.experiment === experiment && experimentStrategies[experiment].includes(run.strategy)
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
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  if (seconds < 1) return '<1 s'
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} s`
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.round(seconds % 60)
  return remainder === 60 ? `${minutes + 1} min` : `${minutes} min ${remainder} s`
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
  const company = String(run.company || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '')
  const digest = String(run.source_pdf_sha256 || '').trim().toLowerCase()
  return file ? `${company || 'unknown'}::${year}::${digest || file}` : ''
}

/**
 * Return only reports represented by every parser that has scored data.
 * Repeated runs stay in the cohort, but parser statistics first average those
 * repeats per report so rerunning one parser cannot silently weight it more.
 */
export function matchedParserCohort(runs: RunSummary[], experiment: BenchmarkExperiment = 'no_ocr') {
  const strategies = experimentStrategies[experiment]
  const scored = runs.filter((run) => run.experiment === experiment && strategies.includes(run.strategy) && run.accuracy != null && reportCohortKey(run))
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

export function groupParserStats(runs: RunSummary[], experiment: BenchmarkExperiment = 'no_ocr') {
  const cohort = matchedParserCohort(runs, experiment)
  return experimentStrategies[experiment].map((key) => {
    const meta = parserMeta[key]
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

/**
 * Compare the three locked extraction arms. Repeated executions of the
 * same parser/report are averaged first, so reruns cannot silently outweigh a
 * different report. Timing is end-to-end when available, with parse time only
 * as a compatibility fallback for older artifacts.
 */
export function groupExperimentStats(runs: RunSummary[]) {
  return (['no_ocr', 'ocr', 'intelligent_scan'] as const).map((experiment) => {
    const eligible = runs.filter((run) => run.experiment === experiment && reportCohortKey(run))
    const passGroups = Object.values(eligible.reduce<Record<string, RunSummary[]>>((groups, run) => {
      const key = `${reportCohortKey(run)}::${run.strategy}`
      ;(groups[key] ||= []).push(run)
      return groups
    }, {}))
    const passMeans = passGroups.map((passRuns) => {
      const mean = (field: keyof RunSummary, fallback?: keyof RunSummary) => {
        const values = passRuns.map((run) => run[field] ?? (fallback ? run[fallback] : null)).filter((value) => value != null).map(Number).filter(Number.isFinite)
        return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
      }
      return {
        totalSeconds: mean('total_seconds', 'extract_seconds'),
        accuracy: mean('accuracy'),
        coverage: mean('coverage'),
      }
    })
    const average = (field: keyof typeof passMeans[number]) => {
      const values = passMeans.map((item) => item[field]).filter((value): value is number => value != null)
      return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
    }
    return {
      key: experiment,
      ...comparisonExperimentMeta[experiment],
      passes: passGroups.length,
      reports: new Set(eligible.map(reportCohortKey)).size,
      totalSeconds: average('totalSeconds'),
      accuracy: average('accuracy'),
      coverage: average('coverage'),
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
