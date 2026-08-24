import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Line,
  LineChart,
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

export function AccuracySpeedChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // One labeled point per strategy: mean end-to-end pass time against mean
  // exact accuracy. Upper-left is strictly better — the verdict is readable
  // at a glance instead of being buried in per-report curves.
  const data = groupExperimentStats(runs)
    .filter((arm) => arm.passes && arm.accuracy != null && arm.totalSeconds != null && arm.totalSeconds > 0)
    .map((arm) => ({
      x: arm.totalSeconds as number,
      seconds: arm.totalSeconds as number,
      y: arm.accuracy as number,
      accuracy: arm.accuracy as number,
      name: arm.label,
      color: arm.color,
    }))
  const yMin = data.length ? Math.max(0, Math.floor(Math.min(...data.map((point) => point.y)) / 5) * 5 - 5) : 0
  return (
    <div className="accuracy-quadrant">
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 26, right: 70, bottom: 34, left: 12 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="x" domain={[0, (dataMax: number) => Math.ceil((dataMax * 1.12) / 10) * 10]} ticks={Array.from({ length: 1 + Math.ceil((Math.max(...(data.length ? data.map((point) => point.x) : [40])) * 1.12) / 10) }, (_, index) => index * 10)} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} tickFormatter={(value: number) => `${value}s`} label={{ value: tr('Mean end-to-end pass time per report (left is faster)', 'レポート別平均パス総時間（左ほど高速）'), position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
            <YAxis type="number" dataKey="y" unit="%" domain={[yMin, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Exact accuracy', '完全一致率'), angle: -90, position: 'insideLeft', offset: 12, fill: 'var(--muted)', fontSize: 10 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter data={data} isAnimationActive={false} shape={(props: { cx?: number; cy?: number; payload?: { color?: string } }) => (
              <circle cx={props.cx} cy={props.cy} r={9} fill={props.payload?.color || 'var(--text)'} stroke="var(--surface)" strokeWidth={2.5} />
            )}>
              <LabelList dataKey="name" position="top" offset={12} fill="var(--text)" fontSize={11.5} fontWeight={700} />
            </Scatter>
          </ComposedChart>
        </ResponsiveContainer>
        {!data.length && <div className="chart-empty">{tr('No source-verified strategy timing data yet.', '元資料検証済みの戦略比較データはまだありません。')}</div>}
      </div>
      {!!data.length && <div className="quadrant-key-row curve-legend curve-legend-below">{data.map((point) => <span className="curve-legend-item" key={point.name}><i style={{ background: point.color }} />{point.name} · {formatDuration(point.seconds)} · {formatMetric(point.accuracy)}</span>)}</div>}
    </div>
  )
}


export function TokenAccuracyChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // Inverted axes: x is mean model input tokens (0 → 100k), y is exact
  // accuracy (0 → 100%). Each strategy's bar stands at its token cost, so the
  // intelligent scanning gate appears first with the tallest-value story:
  // near-identical accuracy at a fraction of the input.
  const arms = groupExperimentStats(runs)
    .filter((arm) => arm.passes && arm.accuracy != null && arm.inputTokens != null && arm.inputTokens > 0)
  const costliest = Math.max(...arms.map((arm) => Number(arm.inputTokens)), 1)
  const data = arms.map((arm) => {
    const tokens = Math.round(arm.inputTokens as number)
    const saving = 100 * (1 - tokens / costliest)
    return {
      x: tokens,
      tokens,
      y: arm.accuracy as number,
      accuracy: arm.accuracy as number,
      name: arm.label,
      savingLabel: saving < 0.5 ? tr('baseline', '基準') : `${saving.toFixed(0)}% ${tr('fewer tokens', 'トークン削減')}`,
      color: arm.color,
    }
  }).sort((left, right) => left.x - right.x)
  const xMax = Math.ceil((Math.max(100000, ...data.map((point) => point.x)) * 1.12) / 20000) * 20000
  return (
    <div className="accuracy-quadrant">
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 52, right: 56, bottom: 34, left: 12 }} barCategoryGap="30%">
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="x" domain={[0, xMax]} ticks={Array.from({ length: xMax / 20000 + 1 }, (_, index) => index * 20000)} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} tickFormatter={(value: number) => value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value))} label={{ value: tr('Mean model input tokens per report (fewer is better)', 'レポート別平均入力トークン（少ないほど良い）'), position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
            <YAxis type="number" domain={[0, 100]} unit="%" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Exact accuracy', '完全一致率'), angle: -90, position: 'insideLeft', offset: 8, fill: 'var(--muted)', fontSize: 10 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-soft)' }} />
            <Bar dataKey="y" barSize={44} radius={[6, 6, 0, 0]} isAnimationActive={false}>
              {data.map((point) => <Cell key={point.name} fill={point.color} />)}
              <LabelList dataKey="savingLabel" position="top" fill="var(--text)" fontSize={12} fontWeight={700} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {!data.length && <div className="chart-empty">{tr('No token-accounted runs for this source yet.', 'この結果ソースのトークン計測済み実行はまだありません。')}</div>}
      </div>
      {!!data.length && <div className="quadrant-key-row curve-legend curve-legend-below">{data.map((point) => <span className="curve-legend-item" key={point.name}><i style={{ background: point.color }} />{point.name} · {point.tokens >= 1000 ? `${Math.round(point.tokens / 1000)}k` : point.tokens} {tr('tok', 'トークン')} · {formatMetric(point.accuracy)}</span>)}</div>}
    </div>
  )
}

export function SpeedBenchmarkChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  // End-to-end pass speed on the matched cohort: only reports that ALL three
  // strategies completed, so document mix cannot flatter any arm. The fastest
  // strategy is the 1.0x baseline.
  const experiments = ['no_ocr', 'ocr', 'intelligent_scan'] as const
  const byReport: Record<string, Partial<Record<string, number[]>>> = {}
  for (const run of runs) {
    const experiment = run.experiment || ''
    if (!(experiments as readonly string[]).includes(experiment)) continue
    const seconds = Number(run.total_seconds ?? run.extract_seconds)
    const key = reportCohortKey(run)
    if (!key || !Number.isFinite(seconds) || seconds <= 0) continue
    ;((byReport[key] ||= {})[experiment] ||= []).push(seconds)
  }
  const matched = Object.values(byReport).filter((entry) => experiments.every((experiment) => entry[experiment]?.length))
  const data = experiments.map((experiment) => {
    const meta = comparisonExperimentMeta[experiment]
    const perReport = matched.map((entry) => {
      const values = entry[experiment] as number[]
      return values.reduce((sum, value) => sum + value, 0) / values.length
    })
    if (!perReport.length) return null
    return { key: experiment, label: meta.label, color: meta.color, seconds: perReport.reduce((sum, value) => sum + value, 0) / perReport.length, reports: perReport.length }
  }).filter((item): item is NonNullable<typeof item> => item != null)
  const baseline = data.find((item) => item.key === 'no_ocr') || data.reduce<(typeof data)[number] | null>((worst, item) => !worst || item.seconds > worst.seconds ? item : worst, null)

  return (
    <div className="speed-benchmark">
      {data.map((item, index) => {
        const speedup = Number(baseline?.seconds || 1) / item.seconds
        const isBaseline = item.key === baseline?.key
        return (
          <div className="speed-row" key={item.key}>
            <div className="speed-label"><strong>{item.label}</strong><span>{formatDuration(item.seconds)} · {item.reports} {tr('matched reports', '対応レポート')}</span></div>
            <div className="speed-track"><i style={{ width: `${Math.max(8, speedup / Math.max(1, ...data.map((entry) => Number(baseline?.seconds || 1) / entry.seconds)) * 100)}%`, background: item.color, opacity: Math.max(.72, 1 - index * .06) }} /></div>
            <div className="speed-value">
              <strong>{isBaseline ? '1.0×' : `${speedup.toFixed(2)}×`}</strong>
              <span>{isBaseline ? tr('baseline', '基準') : speedup >= 1 ? tr('faster', '高速') : tr('slower', '低速')}</span>
            </div>
          </div>
        )
      })}
      {!data.length && <div className="chart-empty">{tr('No matched-cohort timing data yet.', '対応コホートの時間データはまだありません。')}</div>}
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
