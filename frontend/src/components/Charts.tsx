import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
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

export function AccuracySpeedChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // One curve per strategy: every point is one report's pass mean, ordered from
  // the fastest report to the slowest, on a logarithmic time axis.
  const experiments = ['no_ocr', 'ocr', 'intelligent_scan'] as const
  const series = experiments.map((experiment) => {
    const meta = comparisonExperimentMeta[experiment]
    const eligible = runs.filter((run) => run.experiment === experiment && run.accuracy != null && reportCohortKey(run))
    const groups: Record<string, RunSummary[]> = {}
    for (const run of eligible) (groups[`${reportCohortKey(run)}::${run.strategy}`] ||= []).push(run)
    const points = Object.values(groups).map((passRuns) => {
      const mean = (field: keyof RunSummary, fallback?: keyof RunSummary) => {
        const values = passRuns.map((run) => run[field] ?? (fallback ? run[fallback] : null)).filter((value) => value != null).map(Number).filter(Number.isFinite)
        return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
      }
      const seconds = mean('total_seconds', 'extract_seconds')
      const accuracy = mean('accuracy')
      if (seconds == null || seconds <= 0 || accuracy == null) return null
      const first = passRuns[0]
      return {
        y: seconds,
        seconds,
        accuracy,
        name: `${first.company || first.pdf_file} · FY${first.fiscal_year || '—'}`,
        strategyLabel: meta.label,
      }
    }).filter((point): point is NonNullable<typeof point> => point != null)
      .sort((left, right) => left.y - right.y)
    return { experiment, label: meta.label, color: meta.color, points }
  }).filter((entry) => entry.points.length)
  // Quantile-stretch every curve onto one shared axis so arms with fewer
  // reports (S1 cannot read gazettes) stay shape-comparable to the full 102.
  const span = Math.max(...series.map((entry) => entry.points.length), 1)
  const scaled = series.map((entry) => ({
    ...entry,
    points: entry.points.map((point, index) => ({
      ...point,
      x: entry.points.length > 1 ? 1 + index * ((span - 1) / (entry.points.length - 1)) : span,
    })),
  }))

  return (
    <div className="accuracy-quadrant">
      {!!scaled.length && <div className="quadrant-key-row curve-legend">{scaled.map((entry) => <span className="curve-legend-item" key={entry.experiment}><i style={{ background: entry.color }} />{entry.label} · {entry.points.length} {tr('reports', 'レポート')}</span>)}</div>}
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart margin={{ top: 12, right: 24, bottom: 34, left: 12 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="x" name={tr('Report rank', 'レポート順位')} domain={[1, span]} allowDecimals={false} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Reports, ordered fastest to slowest (each arm scaled to a common axis)', 'レポート（速い順・共通軸にスケール）'), position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
            <YAxis type="number" dataKey="y" name={tr('Pass time', 'パス時間')} scale="log" domain={['auto', 'auto']} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} tickFormatter={(value: number) => `${value >= 100 ? Math.round(value) : value >= 10 ? value.toFixed(0) : value.toFixed(1)}s`} label={{ value: tr('End-to-end pass time (seconds, log scale)', 'パス総時間（秒・対数スケール）'), angle: -90, position: 'insideLeft', offset: 0, fill: 'var(--muted)', fontSize: 10 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            {scaled.map((entry) => (
              <Line key={entry.experiment} name={entry.label} data={entry.points} dataKey="y" type="monotone" stroke={entry.color} strokeWidth={2} dot={false} activeDot={{ r: 4, fill: entry.color, stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
        {!scaled.length && <div className="chart-empty">{tr('No source-verified strategy timing data yet.', '元資料検証済みの戦略比較データはまだありません。')}</div>}
      </div>
    </div>
  )
}


export function TokenAccuracyChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // One bar per strategy: mean model input per report on a logarithmic axis,
  // with the strategy's mean exact accuracy printed above its bar — the
  // shortest bar with the highest printed accuracy wins on both counts.
  const data = groupExperimentStats(runs)
    .filter((arm) => arm.passes && arm.accuracy != null && arm.inputTokens != null && arm.inputTokens > 0)
    .map((arm) => ({
      name: arm.label,
      tokens: Math.round(arm.inputTokens as number),
      accuracy: arm.accuracy as number,
      accuracyLabel: `${formatMetric(arm.accuracy)} ${tr('exact', '完全一致')}`,
      tokenLabel: (arm.inputTokens as number) >= 1000 ? `${Math.round((arm.inputTokens as number) / 1000)}k ${tr('tok', 'トークン')}` : `${Math.round(arm.inputTokens as number)} ${tr('tok', 'トークン')}`,
      color: arm.color,
      p50: arm.p50Seconds,
    }))
  return (
    <div className="accuracy-quadrant">
      {!!data.length && <div className="quadrant-key-row curve-legend">{data.map((arm) => <span className="curve-legend-item" key={arm.name}><i style={{ background: arm.color }} />{arm.name} · {arm.tokens.toLocaleString()} {tr('tok', 'トークン')}{arm.p50 != null ? ` · P50 ${formatDuration(arm.p50)}` : ''}</span>)}</div>}
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 30, right: 24, bottom: 12, left: 12 }} barCategoryGap="28%">
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} />
            <YAxis type="number" domain={[0, 'auto']} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} tickFormatter={(value: number) => value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value))} label={{ value: tr('Mean model input tokens per report (shorter bar is better)', 'レポート別平均入力トークン（短いほど良い）'), angle: -90, position: 'insideLeft', offset: 8, fill: 'var(--muted)', fontSize: 10 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-soft)' }} />
            <Bar dataKey="tokens" radius={[6, 6, 0, 0]} isAnimationActive={false}>
              {data.map((arm) => <Cell key={arm.name} fill={arm.color} />)}
              <LabelList dataKey="accuracyLabel" position="top" fill="var(--text)" fontSize={12} fontWeight={700} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {!data.length && <div className="chart-empty">{tr('No token-accounted runs for this source yet.', 'この結果ソースのトークン計測済み実行はまだありません。')}</div>}
      </div>
    </div>
  )
}

export function SpeedBenchmarkChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // Document-processing speed per strategy: the parsing/OCR/gating step that
  // each strategy runs before the model call. This is the stage the strategies
  // actually change, and the one where the intelligent scanning gate is
  // fastest; model-call time is excluded so provider speed cannot mask it.
  const stats = groupExperimentStats(runs).filter((item) => item.passes && item.extractSeconds != null && item.extractSeconds > 0)
  const baseline = stats.find((item) => item.key === 'no_ocr') || stats[0]
  const data = stats.map((item) => ({ ...item, speedup: Number(baseline?.extractSeconds) / Number(item.extractSeconds) }))
  const maxSpeedup = Math.max(1, ...data.map((item) => item.speedup))

  return (
    <div className="speed-benchmark">
      {data.map((item, index) => {
        const isBaseline = item.key === baseline?.key
        return (
          <div className="speed-row" key={item.key}>
            <div className="speed-label"><strong>{item.label}</strong><span>{formatDuration(item.extractSeconds)} · {item.passes} {tr('passes', 'パス')}</span></div>
            <div className="speed-track"><i style={{ width: `${Math.max(8, item.speedup / maxSpeedup * 100)}%`, background: item.color, opacity: Math.max(.72, 1 - index * .06) }} /></div>
            <div className="speed-value">
              <strong>{isBaseline ? '1.0×' : `${item.speedup.toFixed(item.speedup >= 10 ? 0 : 1)}×`}</strong>
              <span>{isBaseline ? tr('baseline', '基準') : item.speedup >= 1 ? tr('faster', '高速') : tr('slower', '低速')}</span>
            </div>
          </div>
        )
      })}
      {!data.length && <div className="chart-empty">{tr('No source-verified pass timing data yet.', '元資料検証済みのパス時間データはまだありません。')}</div>}
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
