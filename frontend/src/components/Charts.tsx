import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
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
      {point.x != null && <span>{tr('Mean pass', '平均パス')} {formatDuration(Number(point.x))}</span>}
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
        x: seconds,
        y: accuracy,
        accuracy,
        name: `${first.company || first.pdf_file} · FY${first.fiscal_year || '—'}`,
        strategyLabel: meta.label,
      }
    }).filter((point): point is NonNullable<typeof point> => point != null)
      .sort((left, right) => left.x - right.x)
    return { experiment, label: meta.label, color: meta.color, points }
  }).filter((entry) => entry.points.length)

  return (
    <div className="accuracy-quadrant">
      {!!series.length && <div className="quadrant-key-row curve-legend">{series.map((entry) => <span className="curve-legend-item" key={entry.experiment}><i style={{ background: entry.color }} />{entry.label} · {entry.points.length} {tr('reports', 'レポート')}</span>)}</div>}
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 24, bottom: 34, left: 12 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="x" name={tr('Pass time', 'パス時間')} unit="s" scale="log" domain={['auto', 'auto']} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('End-to-end pass time per report (seconds, log scale)', 'レポート別パス総時間（秒・対数スケール）'), position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
            <YAxis type="number" dataKey="y" name={tr('Accuracy', '正確度')} unit="%" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Exact accuracy', '完全一致率'), angle: -90, position: 'insideLeft', offset: 0, fill: 'var(--muted)', fontSize: 10 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            {series.map((entry) => (
              <Scatter key={entry.experiment} name={entry.label} data={entry.points} fill={entry.color} line={{ stroke: entry.color, strokeWidth: 2, strokeOpacity: .75 }} stroke="var(--surface)" strokeWidth={2} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
        {!series.length && <div className="chart-empty">{tr('No source-verified strategy timing data yet.', '元資料検証済みの戦略比較データはまだありません。')}</div>}
      </div>
    </div>
  )
}


export function TokenAccuracyChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // One labeled point per strategy: fewer input tokens is left, higher exact
  // accuracy is up — upper-left wins on both axes at once.
  const data = groupExperimentStats(runs)
    .filter((arm) => arm.passes && arm.accuracy != null && arm.inputTokens != null && arm.inputTokens > 0)
    .map((arm) => ({
      x: arm.inputTokens as number,
      y: arm.accuracy as number,
      accuracy: arm.accuracy,
      name: arm.label,
      color: arm.color,
      p50: arm.p50Seconds,
    }))
  return (
    <div className="accuracy-quadrant">
      {!!data.length && <div className="quadrant-key-row curve-legend">{data.map((point) => <span className="curve-legend-item" key={point.name}><i style={{ background: point.color }} />{point.name} · {Math.round(point.x).toLocaleString()} {tr('tok', 'トークン')}{point.p50 != null ? ` · P50 ${formatDuration(point.p50)}` : ''}</span>)}</div>}
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 40, bottom: 34, left: 12 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="x" name={tr('Mean input tokens', '平均入力トークン')} scale="log" domain={['auto', 'auto']} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} tickFormatter={(value: number) => value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value))} label={{ value: tr('Mean model input tokens per report (log scale — fewer is better)', 'レポート別平均入力トークン（対数・少ないほど良い）'), position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
            <YAxis type="number" dataKey="y" name={tr('Accuracy', '正確度')} unit="%" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Mean exact accuracy', '平均完全一致率'), angle: -90, position: 'insideLeft', offset: 0, fill: 'var(--muted)', fontSize: 10 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter data={data} stroke="var(--surface)" strokeWidth={2}>
              {data.map((point) => <Cell key={point.name} fill={point.color} />)}
              <LabelList dataKey="name" position="top" fill="var(--text)" fontSize={11} fontWeight={650} />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        {!data.length && <div className="chart-empty">{tr('No token-accounted runs for this source yet.', 'この結果ソースのトークン計測済み実行はまだありません。')}</div>}
      </div>
    </div>
  )
}

export function SpeedBenchmarkChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  const stats = groupExperimentStats(runs).filter((item) => item.passes && item.totalSeconds != null && item.totalSeconds > 0)
  const baseline = stats.find((item) => item.key === 'no_ocr') || stats[0]
  const data = stats.map((item) => ({ ...item, speedup: Number(baseline?.totalSeconds) / Number(item.totalSeconds) }))
  const maxSpeedup = Math.max(1, ...data.map((item) => item.speedup))

  const comparison = (speedup: number, isBaseline: boolean) => {
    if (isBaseline) return { value: '1.0×', label: tr('baseline', '基準') }
    if (speedup >= 1) return { value: `${speedup.toFixed(speedup >= 10 ? 0 : 1)}×`, label: tr('faster', '高速') }
    const slower = 1 / speedup
    return { value: `${slower.toFixed(slower >= 10 ? 0 : 1)}×`, label: tr('slower', '低速') }
  }

  return (
    <div className="speed-benchmark">
      {data.map((item, index) => {
        const relative = comparison(item.speedup, item.key === baseline?.key)
        return (
          <div className="speed-row" key={item.key}>
            <div className="speed-label"><strong>{item.label}</strong><span>{formatDuration(item.totalSeconds)} · {item.passes} {tr('passes', 'パス')}</span></div>
            <div className="speed-track"><i style={{ width: `${Math.max(8, item.speedup / maxSpeedup * 100)}%`, background: item.color, opacity: Math.max(.72, 1 - index * .06) }} /></div>
            <div className="speed-value">
              <strong>{relative.value}</strong>
              <span>{relative.label}</span>
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
