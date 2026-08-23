import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { RunSummary } from '../types'
import { comparisonExperimentMeta, formatDuration, formatMetric, groupExperimentStats, reportCohortKey } from '../lib/format'
import { useLocale } from '../lib/i18n'

function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: Record<string, unknown> }> }) {
  const { tr } = useLocale()
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="chart-tooltip">
      <strong>{String(point.name || point.label || '')}</strong>
      {point.strategyLabel != null && <span>{String(point.strategyLabel)}</span>}
      {point.accuracy != null && <span>{tr('Accuracy', '正確度')} {formatMetric(Number(point.accuracy))}</span>}
      {point.tokens != null && <span>{tr('Mean input tokens', '平均入力トークン')} {Math.round(Number(point.tokens)).toLocaleString()}</span>}
      {point.seconds != null && <span>{tr('Mean pass', '平均パス')} {formatDuration(Number(point.seconds))}</span>}
      {point.coverage != null && <span>{tr('Coverage', 'カバレッジ')} {formatMetric(Number(point.coverage))}</span>}
    </div>
  )
}

type ParetoSeries = {
  experiment: string
  label: string
  color: string
  points: Array<Record<string, number | string>>
  mean: { x: number; y: number; name: string } | null
}

// Per-strategy Pareto data: a faint cloud of per-report pass means plus one
// bold mean point per strategy. The efficient frontier connects the strategy
// means no other strategy beats on both axes at once.
function paretoSeries(runs: RunSummary[], value: (run: RunSummary[]) => number | null, extra: 'seconds' | 'tokens'): ParetoSeries[] {
  const experiments = ['no_ocr', 'ocr', 'intelligent_scan'] as const
  return experiments.map((experiment) => {
    const meta = comparisonExperimentMeta[experiment]
    const eligible = runs.filter((run) => run.experiment === experiment && run.accuracy != null && reportCohortKey(run))
    const groups: Record<string, RunSummary[]> = {}
    for (const run of eligible) (groups[`${reportCohortKey(run)}::${run.strategy}`] ||= []).push(run)
    const points = Object.values(groups).map((passRuns) => {
      const metric = value(passRuns)
      const accuracy = passRuns.map((run) => Number(run.accuracy)).filter(Number.isFinite)
      if (metric == null || metric <= 0 || !accuracy.length) return null
      const first = passRuns[0]
      return {
        x: metric,
        y: accuracy.reduce((sum, item) => sum + item, 0) / accuracy.length,
        accuracy: accuracy.reduce((sum, item) => sum + item, 0) / accuracy.length,
        [extra]: metric,
        name: `${first.company || first.pdf_file} · FY${first.fiscal_year || '—'}`,
        strategyLabel: meta.label,
      }
    }).filter((point): point is NonNullable<typeof point> => point != null)
    const mean = points.length ? {
      x: points.reduce((sum, point) => sum + Number(point.x), 0) / points.length,
      y: points.reduce((sum, point) => sum + Number(point.y), 0) / points.length,
      name: meta.label,
    } : null
    return { experiment, label: meta.label, color: meta.color, points, mean }
  }).filter((entry) => entry.points.length)
}

function paretoFrontier(series: ParetoSeries[]) {
  const means = series.filter((entry) => entry.mean != null).map((entry) => ({ ...entry.mean!, color: entry.color }))
    .sort((left, right) => left.x - right.x)
  const frontier: typeof means = []
  let best = -Infinity
  for (const point of means) {
    if (point.y > best) { frontier.push(point); best = point.y }
  }
  return frontier
}

function ParetoChart({ series, xLabel, xTickFormatter, extra }: {
  series: ParetoSeries[]
  xLabel: string
  xTickFormatter: (value: number) => string
  extra: 'seconds' | 'tokens'
}) {
  const { tr } = useLocale()
  const frontier = paretoFrontier(series)
  return (
    <div className="chart-frame dither-chart">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart margin={{ top: 18, right: 42, bottom: 34, left: 12 }}>
          <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
          <XAxis type="number" dataKey="x" scale="log" domain={['auto', 'auto']} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} tickFormatter={xTickFormatter} label={{ value: xLabel, position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
          <YAxis type="number" dataKey="y" unit="%" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Exact accuracy', '完全一致率'), angle: -90, position: 'insideLeft', offset: 0, fill: 'var(--muted)', fontSize: 10 }} />
          <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
          {frontier.length > 1 && <Line data={frontier} dataKey="y" type="linear" stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="6 5" dot={false} activeDot={false} isAnimationActive={false} legendType="none" tooltipType="none" />}
          {series.map((entry) => (
            <Scatter key={`cloud-${entry.experiment}`} name={entry.label} data={entry.points} fill={entry.color} fillOpacity={0.28} shape="circle" isAnimationActive={false} />
          ))}
          {series.map((entry) => entry.mean && (
            <Scatter key={`mean-${entry.experiment}`} data={[{ ...entry.mean, accuracy: entry.mean.y, [extra]: entry.mean.x, strategyLabel: tr('Strategy mean', '戦略平均') }]} fill={entry.color} stroke="var(--surface)" strokeWidth={2} isAnimationActive={false}>
              <LabelList dataKey="name" position="top" fill="var(--text)" fontSize={11} fontWeight={650} />
            </Scatter>
          ))}
        </ComposedChart>
      </ResponsiveContainer>
      {!series.length && <div className="chart-empty">{tr('No source-verified strategy data yet.', '元資料検証済みの戦略比較データはまだありません。')}</div>}
    </div>
  )
}

export function AccuracySpeedChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  const mean = (passRuns: RunSummary[], field: keyof RunSummary, fallback?: keyof RunSummary) => {
    const values = passRuns.map((run) => run[field] ?? (fallback ? run[fallback] : null)).filter((value) => value != null).map(Number).filter(Number.isFinite)
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
  }
  const series = paretoSeries(runs, (passRuns) => mean(passRuns, 'total_seconds', 'extract_seconds'), 'seconds')
  return (
    <div className="accuracy-quadrant">
      {!!series.length && <div className="quadrant-key-row curve-legend">{series.map((entry) => <span className="curve-legend-item" key={entry.experiment}><i style={{ background: entry.color }} />{entry.label} · {entry.points.length} {tr('reports', 'レポート')}</span>)}</div>}
      <ParetoChart series={series} extra="seconds" xLabel={tr('End-to-end pass time per report (seconds, log scale)', 'レポート別パス総時間（秒・対数スケール）')} xTickFormatter={(value) => `${value >= 10 ? Math.round(value) : value.toFixed(1)}s`} />
    </div>
  )
}


export function TokenAccuracyChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  const armStats = groupExperimentStats(runs)
  const mean = (passRuns: RunSummary[], field: keyof RunSummary, fallback?: keyof RunSummary) => {
    const values = passRuns.map((run) => run[field] ?? (fallback ? run[fallback] : null)).filter((value) => value != null).map(Number).filter(Number.isFinite)
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
  }
  const series = paretoSeries(runs, (passRuns) => mean(passRuns, 'input_tokens', 'approx_input_tokens'), 'tokens')
  return (
    <div className="accuracy-quadrant">
      {!!series.length && <div className="quadrant-key-row curve-legend">{series.map((entry) => {
        const arm = armStats.find((stat) => stat.key === entry.experiment)
        return <span className="curve-legend-item" key={entry.experiment}><i style={{ background: entry.color }} />{entry.label}{arm?.inputTokens != null ? ` · ${Math.round(arm.inputTokens).toLocaleString()} ${tr('tok', 'トークン')}` : ''}{arm?.p50Seconds != null ? ` · P50 ${formatDuration(arm.p50Seconds)}` : ''}</span>
      })}</div>}
      <ParetoChart series={series} extra="tokens" xLabel={tr('Model input tokens per report (log scale — fewer is better)', 'レポート別入力トークン（対数・少ないほど良い）')} xTickFormatter={(value) => value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value))} />
    </div>
  )
}

export function SpeedBenchmarkChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // Worst-case document cost per strategy: the largest model input a strategy
  // ever had to send, with the worst end-to-end pass alongside it. Multiples
  // are relative to the intelligent scanning gate, whose input stays bounded
  // no matter how large the filing is.
  const experiments = ['no_ocr', 'ocr', 'intelligent_scan'] as const
  const data = experiments.map((experiment) => {
    const meta = comparisonExperimentMeta[experiment]
    const eligible = runs.filter((run) => run.experiment === experiment)
    const tokens = eligible.map((run) => run.input_tokens ?? run.approx_input_tokens).filter((value) => value != null).map(Number).filter((value) => Number.isFinite(value) && value > 0)
    const seconds = eligible.map((run) => run.total_seconds ?? run.extract_seconds).filter((value) => value != null).map(Number).filter((value) => Number.isFinite(value) && value > 0)
    if (!tokens.length) return null
    return { key: experiment, label: meta.label, color: meta.color, worstTokens: Math.max(...tokens), worstSeconds: seconds.length ? Math.max(...seconds) : null, passes: eligible.length }
  }).filter((item): item is NonNullable<typeof item> => item != null)
  const baseline = data.find((item) => item.key === 'intelligent_scan') || data[0]
  const maxTokens = Math.max(1, ...data.map((item) => item.worstTokens))
  const formatTokens = (value: number) => value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value))

  return (
    <div className="speed-benchmark">
      {data.map((item, index) => {
        const ratio = item.worstTokens / Number(baseline?.worstTokens || 1)
        const isBaseline = item.key === baseline?.key
        return (
          <div className="speed-row" key={item.key}>
            <div className="speed-label"><strong>{item.label}</strong><span>{formatTokens(item.worstTokens)} {tr('tok', 'トークン')}{item.worstSeconds != null ? ` · ${tr('worst pass', '最悪パス')} ${formatDuration(item.worstSeconds)}` : ''}</span></div>
            <div className="speed-track"><i style={{ width: `${Math.max(6, item.worstTokens / maxTokens * 100)}%`, background: item.color, opacity: Math.max(.72, 1 - index * .06) }} /></div>
            <div className="speed-value">
              <strong>{isBaseline ? '1.0×' : `${ratio.toFixed(ratio >= 10 ? 0 : 1)}×`}</strong>
              <span>{isBaseline ? tr('baseline', '基準') : tr('more input', '入力増')}</span>
            </div>
          </div>
        )
      })}
      {!data.length && <div className="chart-empty">{tr('No source-verified pass data yet.', '元資料検証済みのパスデータはまだありません。')}</div>}
    </div>
  )
}

export function CoverageDonut({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  const scored = runs.filter((run) => run.accuracy != null || run.coverage != null)
  const mean = (key: 'accuracy' | 'coverage') => {
    const values = scored.map((run) => run[key]).filter((value) => value != null).map(Number).filter(Number.isFinite)
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0
  }
  const exact = Math.min(100, Math.max(0, mean('accuracy')))
  const coverage = Math.min(100, Math.max(exact, mean('coverage')))
  const segments = [
    { label: tr('Exact match', '完全一致'), value: exact, color: '#2a78d6' },
    { label: tr('Covered, not exact', '取得済み・不一致'), value: Math.max(0, coverage - exact), color: '#eda100' },
    { label: tr('Uncovered', '未取得'), value: Math.max(0, 100 - coverage), color: '#e3e8ef' },
  ]
  const radius = 47
  const circumference = 2 * Math.PI * radius
  let offset = 0

  if (!scored.length) return <div className="coverage-empty-state"><strong>{tr('No scored runs yet', '評価済み実行はまだありません')}</strong><span>{tr('Coverage composition will appear after a source-verified run completes.', '元資料検証済みの実行完了後にカバレッジ構成が表示されます。')}</span></div>

  return (
    <div className="coverage-donut-wrap">
      <div className="coverage-donut">
        <svg viewBox="0 0 120 120" role="img" aria-label={`${formatMetric(coverage)} ${tr('mean field coverage', '平均フィールドカバレッジ')}`}>
          <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--surface-soft)" strokeWidth="14" />
          {segments.map((segment) => {
            const length = segment.value / 100 * circumference
            const currentOffset = offset
            offset += length
            return <circle key={segment.label} cx="60" cy="60" r={radius} fill="none" stroke={segment.color} strokeWidth="14" strokeDasharray={`${length} ${circumference - length}`} strokeDashoffset={-currentOffset} transform="rotate(-90 60 60)" />
          })}
        </svg>
        <div><strong>{formatMetric(coverage)}</strong><span>{tr('coverage', 'カバレッジ')}</span></div>
      </div>
      <div className="coverage-legend">
        {segments.map((segment) => <div key={segment.label}><i style={{ background: segment.color }} /><span>{segment.label}</span><strong>{formatMetric(segment.value)}</strong></div>)}
      </div>
    </div>
  )
}

export function ParserAccuracyChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  const data = groupExperimentStats(runs).filter((item) => item.passes && item.accuracy != null)
  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 12, right: 46, bottom: 8, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} strokeDasharray="2 5" />
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis type="category" dataKey="label" width={76} tick={{ fill: 'var(--text)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-raised)' }} />
          <Bar dataKey="accuracy" radius={[0, 7, 7, 0]} barSize={18}>{data.map((item) => <Cell key={item.key} fill={item.color} />)}
            <LabelList dataKey="accuracy" position="right" formatter={(value: unknown) => formatMetric(Number(value))} fill="var(--muted)" fontSize={11} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {!data.length && <div className="chart-empty">{tr('No scored strategy runs yet.', '評価済みの戦略実行はまだありません。')}</div>}
    </div>
  )
}
