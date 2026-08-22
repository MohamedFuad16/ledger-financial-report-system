import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { RunSummary } from '../types'
import { formatDuration, formatMetric, groupExperimentStats } from '../lib/format'
import { useLocale } from '../lib/i18n'

function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: Record<string, unknown> }> }) {
  const { tr } = useLocale()
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="chart-tooltip">
      <strong>{String(point.name || point.label || '')}</strong>
      {point.accuracy != null && <span>{tr('Accuracy', '正確度')} {formatMetric(Number(point.accuracy))}</span>}
      {point.x != null && <span>{tr('Mean pass', '平均パス')} {formatDuration(Number(point.x))}</span>}
      {point.coverage != null && <span>{tr('Coverage', 'カバレッジ')} {formatMetric(Number(point.coverage))}</span>}
    </div>
  )
}

export function AccuracySpeedChart({ runs }: { runs: RunSummary[] }) {
  const { tr } = useLocale()
  const data = groupExperimentStats(runs)
    .filter((arm) => arm.accuracy != null && arm.totalSeconds != null && arm.totalSeconds > 0)
    .map((arm) => ({ x: arm.totalSeconds as number, y: arm.accuracy as number, accuracy: arm.accuracy, coverage: arm.coverage, name: arm.label, color: arm.color }))
  const sortedTimes = data.map((item) => item.x).sort((a, b) => a - b)
  const splitTime = sortedTimes.length ? sortedTimes[Math.floor(sortedTimes.length / 2)] : 1
  const minTime = sortedTimes[0] || .1
  return (
    <div className="accuracy-quadrant">
      {!!data.length && <div className="quadrant-key-row"><span className="quadrant-label quadrant-best">{tr('Best zone · fast + accurate', '最適ゾーン・高速＋高精度')}</span><span className="quadrant-label quadrant-slow">{tr('Accurate, slower', '高精度・低速')}</span></div>}
      <div className="chart-frame dither-chart">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 24, bottom: 34, left: 12 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="2 5" />
            <ReferenceArea x1={minTime} x2={splitTime} y1={50} y2={100} fill="#2563eb" fillOpacity={.08} strokeOpacity={0} />
            <XAxis type="number" dataKey="x" name={tr('Mean pass time', '平均パス時間')} unit="s" scale="log" domain={['auto', 'auto']} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Mean end-to-end pass time (seconds)', '平均パス総時間（秒）'), position: 'insideBottom', offset: -18, fill: 'var(--muted)', fontSize: 10 }} />
            <YAxis type="number" dataKey="y" name={tr('Accuracy', '正確度')} unit="%" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--line-strong)' }} tickLine={false} label={{ value: tr('Exact accuracy', '完全一致率'), angle: -90, position: 'insideLeft', offset: 0, fill: 'var(--muted)', fontSize: 10 }} />
            <ReferenceLine x={splitTime} stroke="var(--line-strong)" strokeDasharray="5 5" />
            <ReferenceLine y={50} stroke="var(--line-strong)" strokeDasharray="5 5" />
            <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter data={data} line={{ stroke: '#64748b', strokeWidth: 2, strokeOpacity: .55 }} stroke="var(--surface)" strokeWidth={3}>{data.map((point) => <Cell key={point.name} fill={point.color} />)}</Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        {!data.length && <div className="chart-empty">{tr('No source-verified OCR/no-OCR timing data yet.', '元資料検証済みのOCR有無比較データはまだありません。')}</div>}
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
      {!data.length && <div className="chart-empty">{tr('No scored OCR/no-OCR runs yet.', '評価済みのOCR有無実行はまだありません。')}</div>}
    </div>
  )
}
