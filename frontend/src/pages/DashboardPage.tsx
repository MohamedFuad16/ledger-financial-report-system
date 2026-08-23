import { ArrowRight, Gauge, Layers3, SearchCheck } from 'lucide-react'
import type { PanelKey, RunSummary } from '../types'
import { formatDuration, formatMetric, groupExperimentStats, reportCohortKey } from '../lib/format'
import { AccuracySpeedChart, CoverageDonut, ParserAccuracyChart, SpeedBenchmarkChart, TokenAccuracyChart } from '../components/Charts'
import { Badge, Button, Card, MetricCard, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'
import { benchmarkSource, benchmarkSourceMeta, runMatchesSource } from '../lib/benchmarkSource'

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
  const source = benchmarkSource()
  const benchmarkRuns = runs.filter((run) =>
    (run.experiment === 'no_ocr' || run.experiment === 'ocr' || run.experiment === 'intelligent_scan')
    && runMatchesSource(run, source))
  const stats = groupExperimentStats(benchmarkRuns).filter((entry) => entry.passes)
  const average = (key: keyof RunSummary) => {
    const values = stats.map((entry) => entry[key as keyof typeof entry]).filter((value) => value != null).map(Number).filter(Number.isFinite)
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
  }
  const fastest = stats.filter((entry) => entry.totalSeconds != null).reduce<(typeof stats)[number] | null>((best, entry) => !best || Number(entry.totalSeconds) < Number(best.totalSeconds) ? entry : best, null)
  const bestAccuracy = Math.max(...stats.map((entry) => Number(entry.accuracy ?? -Infinity)))
  const accuracyLeaders = stats.filter((entry) => Math.round(Number(entry.accuracy) * 10) === Math.round(bestAccuracy * 10))
  const accuracyLeader = accuracyLeaders[0] || null
  const tiedAccuracyLabel = accuracyLeaders.map((entry) => entry.label).join(tr(' and ', '・'))
  const completeReportCount = new Set(benchmarkRuns.map(reportCohortKey)).size
  const hasUnverifiedReports = benchmarkRuns.some((run) => run.gold_status === 'human_review_required')
  const conclusion = fastest && accuracyLeader && completeReportCount
    ? accuracyLeaders.length > 1
      ? tr(`${fastest.label} is faster; ${tiedAccuracyLabel} are tied for exact accuracy at ${formatMetric(accuracyLeader.accuracy)}.`, `${fastest.label} が高速で、${tiedAccuracyLabel} が完全一致率 ${formatMetric(accuracyLeader.accuracy)} で同率首位です。`)
      : fastest.key === accuracyLeader.key
      ? tr(`${fastest.label} currently has the best mean speed and exact accuracy.`, `${fastest.label} が現在、平均速度と完全一致率の両方で首位です。`)
      : tr(`${fastest.label} is faster; ${accuracyLeader.label} leads exact accuracy.`, `${fastest.label} が高速で、${accuracyLeader.label} が完全一致率で首位です。`)
    : tr('Run the benchmark to identify the leading parser.', 'ベンチマークを実行して最良のパーサーを確認します。')

  return (
    <div className="page dashboard-page">
      <header className="page-header dashboard-header">
        <div>
          <h1>{tr('Financial Report System', '財務レポートシステム')}</h1>
          <p>{tr('Extract, verify, and benchmark the asset side of an Annual Report across document-representation strategies.', '年次報告書の資産項目を抽出・検証し、文書表現戦略ごとにベンチマークします。')}</p>
        </div>
        <div className="dashboard-header-actions">
          <button className="benchmark-source-badge" type="button" onClick={() => onNavigate('settings')} title={tr('Change the results source in Settings', '結果ソースは設定で変更できます')}>{tr(benchmarkSourceMeta[source].label, benchmarkSourceMeta[source].labelJa)}</button>
          <Button onClick={() => onNavigate('strategy1')}>{tr('Run an extraction', '抽出を実行')} <ArrowRight size={16} /></Button>
        </div>
      </header>

      <div className="metric-grid">
        <MetricCard label={tr('Best exact accuracy', '最高完全一致率')} value={formatMetric(accuracyLeader?.accuracy)} detail={accuracyLeader ? `${tiedAccuracyLabel} · ${accuracyLeader.passes} ${tr('successful passes', '成功パス')}` : tr('Awaiting source-verified runs', '元資料検証済み実行を待っています')} />
        <MetricCard label={tr('Mean field coverage', '平均フィールドカバレッジ')} value={formatMetric(average('coverage'))} detail={tr('Fields returned by the model; low confidence is flagged for review', 'モデルが返した項目。低信頼度はレビュー対象として表示')} />
        <MetricCard label={tr('Matched reports', '対応レポート')} value={completeReportCount.toLocaleString()} detail={tr('Distinct source-verified reports in the benchmark feed', 'ベンチマークフィード内の元資料検証済みレポート数')} />
        <MetricCard label={tr('Fastest arm', '最速条件')} value={fastest?.label || '—'} detail={fastest ? `${formatDuration(fastest.totalSeconds)} ${tr('mean end-to-end pass time', '平均パス総時間')}` : tr('No timing data yet', '時間データはまだありません')} />
      </div>

      <SectionHeading eyebrow={tr('Benchmark tracks', 'ベンチマーク条件')} title={tr('Extraction strategies', '抽出戦略')} description={tr('Each strategy changes one boundary while preserving the output contract.', '出力契約を保ったまま、各戦略で一つの境界だけを変更します。')} />
      <div className="strategy-grid dashboard-strategy-grid">
        {[
          { number: '01', title: tr('No-OCR parser control', 'OCRなしパーサー対照実験'), body: tr('PyPDF, PyMuPDF4LLM, pdf-inspector, and Docling with OCR disabled.', 'PyPDF、PyMuPDF4LLM、pdf-inspector、DoclingをOCRなしで比較します。'), status: tr('Active', '有効'), tone: 'blue' as const, panel: 'strategy1' as PanelKey, icon: Gauge },
          { number: '02', title: tr('OCR-enabled parser bake-off', 'OCR有効パーサーベイクオフ'), body: tr('The same four parsers: adaptive OCR where page detection exists, otherwise OCR is compulsory.', '同じ4パーサーで、ページ判定がある場合は適応OCR、ない場合はOCRを必須化します。'), status: tr('Active', '有効'), tone: 'green' as const, panel: 'strategy2' as PanelKey, icon: Layers3 },
          { number: '03', title: tr('Intelligent scanning gate', 'インテリジェントスキャニングゲート'), body: tr('pdf-inspector selectively replaces OCR-routed pages, then scores unified complete pages and sends only the top three to five to the LLM.', 'pdf-inspectorがOCR対象ページだけを置換し、統合された完全ページを採点して上位3〜5ページだけをLLMに送ります。'), status: tr('Active', '有効'), tone: 'amber' as const, panel: 'strategy3' as PanelKey, icon: SearchCheck },
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
          <SectionHeading eyebrow={tr('Speed benchmark', '速度ベンチマーク')} title={tr('Mean pass speed across three strategies', '3戦略の平均パス速度')} description={tr('No OCR, OCR enabled, and intelligent scanning are averaged independently across successful end-to-end passes; No OCR is the 1.0× baseline.', 'OCRなし、OCRあり、インテリジェントスキャンを成功した総パス時間で個別集計し、OCRなしを1.0倍の基準とします。')} />
          {loading ? <div className="chart-skeleton" /> : <SpeedBenchmarkChart runs={benchmarkRuns} />}
        </Card>
        <Card className="chart-card coverage-card">
          <SectionHeading eyebrow={tr('Quality composition', '品質構成')} title={tr('Accuracy versus coverage', '正確度とカバレッジ')} description={tr('Coverage says a field was returned; exact accuracy says it matched the gold value.', 'カバレッジは項目の取得率、完全一致率は正解値との一致を示します。')} />
          {loading ? <div className="chart-skeleton" /> : <CoverageDonut runs={benchmarkRuns} />}
        </Card>
      </div>

      <div className="dashboard-layout benchmark-frontier">
        <Card className="chart-card chart-card-wide">
          <SectionHeading eyebrow={tr('Experiment frontier', '実験フロンティア')} title={tr('Three-strategy speed × accuracy curves', '3戦略：速度×正確度カーブ')} description={tr('One curve per strategy: each point is one report, ordered fastest to slowest on a logarithmic time axis. Upper-left is faster and more accurate.', '戦略ごとに1本のカーブを描画します。各点は1レポートで、対数時間軸に沿って高速側から並びます。左上ほど高速かつ高精度です。')} />
          {loading ? <div className="chart-skeleton" /> : <AccuracySpeedChart runs={benchmarkRuns} />}
        </Card>
        <Card className="chart-card accuracy-card">
          <SectionHeading eyebrow={tr('Benchmark', 'ベンチマーク')} title={tr('Mean exact accuracy', '平均完全一致率')} description={tr('Scored source-bound passes grouped into no OCR, OCR enabled, and intelligent scanning.', '元資料に固定された評価済みパスをOCRなし、OCRあり、インテリジェントスキャンで集計しています。')} />
          {loading ? <div className="chart-skeleton" /> : <ParserAccuracyChart runs={benchmarkRuns} />}
        </Card>
      </div>

      <Card className="chart-card latency-distribution-card">
        <SectionHeading eyebrow={tr('Token efficiency', 'トークン効率')} title={tr('Input tokens × exact accuracy', '入力トークン×完全一致率')} description={tr('One point per strategy: mean model input per report on a logarithmic axis against mean exact accuracy, with each strategy\u2019s P50 pass time in the key. Upper-left wins on both cost and correctness.', '戦略ごとに1点、レポート別平均入力トークン（対数軸）と平均完全一致率を示します。凡例に各戦略のP50パス時間を併記。左上ほどコストと正確性の両方で優れています。')} />
        {loading ? <div className="chart-skeleton" /> : <TokenAccuracyChart runs={benchmarkRuns} />}
      </Card>

      <div className="dashboard-lower">
        <Card className="method-card conclusion-card">
          <SectionHeading eyebrow={tr('Current conclusion', '現在の結論')} title={conclusion} description={tr('This conclusion is calculated from the completed benchmark runs currently stored in the workspace.', 'この結論は、ワークスペースに保存された完了済みベンチマークから算出されます。')} />
          {hasUnverifiedReports && <p className="benchmark-caveat">{tr('Some completed runs use reports whose candidate answers have not been human approved. They remain visible for speed and coverage analysis, but they do not contribute to exact-accuracy leadership.', '完了済み実行の一部は候補回答が人による承認前です。速度とカバレッジの分析には表示されますが、完全一致率の首位判定には含まれません。')}</p>}
        </Card>
      </div>

    </div>
  )
}
