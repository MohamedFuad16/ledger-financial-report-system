import { ArrowRight, Gauge, Layers3, SearchCheck } from 'lucide-react'
import type { PanelKey, RunSummary } from '../types'
import { type BenchmarkExperiment, formatDuration, formatMetric, groupParserStats, matchedParserCohort, parserMetricLeaders, reportCohortKey } from '../lib/format'
import { AccuracySpeedChart, CoverageDonut, ParserAccuracyChart, SpeedBenchmarkChart } from '../components/Charts'
import { RunTable } from '../components/RunTable'
import { Badge, Button, Card, MetricCard, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

export function DashboardPage({
  runs,
  loading,
  onNavigate,
}: {
  runs: RunSummary[]
  loading: boolean
  onNavigate: (key: PanelKey) => void
}) {
  const { tr } = useLocale()
  const experiment: BenchmarkExperiment = 'ocr'
  const armRuns = runs.filter((run) => run.experiment === experiment)
  const benchmarkRuns = matchedParserCohort(runs, experiment)
  const stats = groupParserStats(runs, experiment).filter((entry) => entry.runs)
  const average = (key: keyof RunSummary) => {
    const values = stats.map((entry) => entry[key as keyof typeof entry]).filter((value) => value != null).map(Number).filter(Number.isFinite)
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
  }
  const fastest = stats.length ? stats.reduce((a, b) => Number(a.extractSeconds ?? Infinity) <= Number(b.extractSeconds ?? Infinity) ? a : b) : null
  const accuracyLeaders = parserMetricLeaders(stats, 'accuracy')
  const accuracyLeader = accuracyLeaders[0] || null
  const tiedAccuracyLabel = accuracyLeaders.map((entry) => entry.short).join(tr(' and ', '・'))
  const completeReportCount = new Set(benchmarkRuns.map(reportCohortKey)).size
  const hasUnverifiedReports = armRuns.some((run) => run.gold_status === 'human_review_required')
  const conclusion = fastest && accuracyLeader && completeReportCount
    ? accuracyLeaders.length > 1
      ? tr(`${fastest.short} is fastest; ${tiedAccuracyLabel} are tied for exact accuracy at ${formatMetric(accuracyLeader.accuracy)}.`, `${fastest.short} が最速で、${tiedAccuracyLabel} が完全一致率 ${formatMetric(accuracyLeader.accuracy)} で同率首位です。`)
      : fastest.key === accuracyLeader.key
      ? tr(`${fastest.short} is currently the fastest and most accurate parser for this project.`, `${fastest.short} が現在このプロジェクトで最速かつ最も正確なパーサーです。`)
      : tr(`${fastest.short} is fastest; ${accuracyLeader.short} leads exact accuracy.`, `${fastest.short} が最速で、${accuracyLeader.short} が完全一致率で首位です。`)
    : tr('Run the benchmark to identify the leading parser.', 'ベンチマークを実行して最良のパーサーを確認します。')

  return (
    <div className="page dashboard-page">
      <header className="page-header dashboard-header">
        <div>
          <h1>{tr('Financial Report System', '財務レポートシステム')}</h1>
          <p>{tr('Extract, verify, and benchmark the asset side of an Annual Report across document-representation strategies.', '年次報告書の資産項目を抽出・検証し、文書表現戦略ごとにベンチマークします。')}</p>
        </div>
        <div className="dashboard-header-actions">
          <Button onClick={() => onNavigate('strategy1')}>{tr('Run an extraction', '抽出を実行')} <ArrowRight size={16} /></Button>
        </div>
      </header>

      <div className="metric-grid">
        <MetricCard label={tr('Best exact accuracy', '最高完全一致率')} value={formatMetric(accuracyLeader?.accuracy)} detail={accuracyLeader ? `${tiedAccuracyLabel} · ${accuracyLeader.runs} ${tr('matched reports', '対応レポート')}` : tr('Awaiting a matched parser cohort', '対応するパーサー比較を待っています')} />
        <MetricCard label={tr('Mean field coverage', '平均フィールドカバレッジ')} value={formatMetric(average('coverage'))} detail={tr('Fields returned above confidence gate', '信頼度基準を超えて取得された項目')} />
        <MetricCard label={tr('Matched reports', '対応レポート')} value={completeReportCount.toLocaleString()} detail={tr('Every parser in this arm completed the same report', 'この条件の全パーサーが同じレポートを完了')} />
        <MetricCard label={tr('Fastest parser', '最速パーサー')} value={fastest?.short || '—'} detail={fastest ? `${formatDuration(fastest.extractSeconds)} ${tr('mean parse time', '平均解析時間')}` : tr('No timing data yet', '時間データはまだありません')} />
      </div>

      <SectionHeading eyebrow={tr('Benchmark tracks', 'ベンチマーク条件')} title={tr('Extraction strategies', '抽出戦略')} description={tr('Each strategy changes one boundary while preserving the output contract.', '出力契約を保ったまま、各戦略で一つの境界だけを変更します。')} />
      <div className="strategy-grid dashboard-strategy-grid">
        {[
          { number: '01', title: tr('OCR-enabled parser bake-off', 'OCR有効パーサーベイクオフ'), body: tr('The same four parsers: adaptive OCR where page detection exists, otherwise OCR is compulsory.', '同じ4パーサーで、ページ判定がある場合は適応OCR、ない場合はOCRを必須化します。'), status: tr('Active', '有効'), tone: 'blue' as const, panel: 'strategy1' as PanelKey, icon: Layers3 },
          { number: '02', title: tr('No-OCR parser control', 'OCRなしパーサー対照実験'), body: tr('PyPDF, PyMuPDF4LLM, pdf-inspector, and Docling with OCR disabled.', 'PyPDF、PyMuPDF4LLM、pdf-inspector、DoclingをOCRなしで比較します。'), status: tr('Active', '有効'), tone: 'green' as const, panel: 'strategy2' as PanelKey, icon: Gauge },
          { number: '03', title: tr('Schema-guided page filtering', 'スキーマ誘導ページフィルタリング'), body: tr('Rank complete Markdown pages against the 27-field schema, reject obvious noise, and send only the evidence packet to the same LLM.', 'Markdownの完全なページを27項目のスキーマで順位付けし、明らかなノイズを除外して根拠ページだけを同じLLMに送ります。'), status: tr('Planned', '計画中'), tone: 'amber' as const, panel: 'strategy3' as PanelKey, icon: SearchCheck },
        ].map((strategy) => {
          const Icon = strategy.icon
          return (
            <Card className="strategy-card" key={strategy.number}>
              <div className="strategy-card-top"><span>{strategy.number}</span><Badge tone={strategy.tone}>{strategy.status}</Badge></div>
              <div className="strategy-icon"><Icon size={18} /></div>
              <h3>{strategy.title}</h3>
              <p>{strategy.body}</p>
              <button onClick={() => onNavigate(strategy.panel)}>{tr('Open strategy', '戦略を開く')} <ArrowRight size={14} /></button>
            </Card>
          )
        })}
      </div>

      <div className="benchmark-analytics">
        <Card className="chart-card speed-card">
          <SectionHeading eyebrow={tr('Speed benchmark', '速度ベンチマーク')} title={tr('Relative parser speed', 'パーサー相対速度')} description={tr('Strategy 1 is the 1.0× baseline. Higher multiples finish the same extraction faster.', '戦略1を1.0倍の基準とし、倍率が高いほど同じ抽出を速く完了します。')} />
          {loading ? <div className="chart-skeleton" /> : <SpeedBenchmarkChart runs={benchmarkRuns} experiment={experiment} />}
        </Card>
        <Card className="chart-card coverage-card">
          <SectionHeading eyebrow={tr('Quality composition', '品質構成')} title={tr('Accuracy versus coverage', '正確度とカバレッジ')} description={tr('Coverage says a field was returned; exact accuracy says it matched the gold value.', 'カバレッジは項目の取得率、完全一致率は正解値との一致を示します。')} />
          {loading ? <div className="chart-skeleton" /> : <CoverageDonut runs={benchmarkRuns} />}
        </Card>
      </div>

      <div className="dashboard-layout benchmark-frontier">
        <Card className="chart-card chart-card-wide">
          <SectionHeading eyebrow={tr('Parser frontier', 'パーサーフロンティア')} title={tr('Speed × accuracy quadrant', '速度 × 正確度クアドラント')} description={tr('The blue upper-left quadrant is the target: at least 50% accuracy with lower parse time.', '青い左上領域が目標です。50%以上の正確度と短い解析時間を示します。')} />
          {loading ? <div className="chart-skeleton" /> : <AccuracySpeedChart runs={benchmarkRuns} />}
        </Card>
        <Card className="chart-card accuracy-card">
          <SectionHeading eyebrow={tr('Benchmark', 'ベンチマーク')} title={tr('Mean exact accuracy', '平均完全一致率')} description={tr('Scored rows only, grouped by parser.', '評価対象行をパーサー別に集計しています。')} />
          {loading ? <div className="chart-skeleton" /> : <ParserAccuracyChart runs={benchmarkRuns} experiment={experiment} />}
        </Card>
      </div>

      <div className="dashboard-lower">
        <Card className="method-card conclusion-card">
          <SectionHeading eyebrow={tr('Current conclusion', '現在の結論')} title={conclusion} description={tr('This conclusion is calculated from the completed benchmark runs currently stored in the workspace.', 'この結論は、ワークスペースに保存された完了済みベンチマークから算出されます。')} />
          {hasUnverifiedReports && <p className="benchmark-caveat">{tr('Some completed runs use reports whose candidate answers have not been human approved. They remain visible for speed and coverage analysis, but they do not contribute to exact-accuracy leadership.', '完了済み実行の一部は候補回答が人による承認前です。速度とカバレッジの分析には表示されますが、完全一致率の首位判定には含まれません。')}</p>}
        </Card>
      </div>

      <Card className="recent-card">
        <SectionHeading eyebrow={tr('Library', 'ライブラリ')} title={tr('Recent experiment runs', '最近の実験実行')} description={tr('The most recent completed predictions across every parser.', '全パーサーの最新完了結果です。')} action={<Button variant="secondary" onClick={() => onNavigate('history')}>{tr('View all', 'すべて表示')} <ArrowRight size={15} /></Button>} />
        <RunTable runs={runs.slice(0, 6)} compact />
      </Card>
    </div>
  )
}
