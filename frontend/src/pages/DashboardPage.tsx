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
  const s3Runs = benchmarkRuns.filter((run) => run.experiment === 'intelligent_scan')
  const s3Stat = stats.find((entry) => entry.key === 'intelligent_scan') || null
  const s3ReportCount = new Set(s3Runs.map(reportCohortKey)).size
  const disclosedTotals = s3Runs.reduce((sums, run) => ({
    answered: sums.answered + Number(run.committed_and_compared ?? 0),
    disclosed: sums.disclosed + Number(run.total_compared ?? 0),
  }), { answered: 0, disclosed: 0 })
  const disclosedCoverage = disclosedTotals.disclosed > 0 ? 100 * disclosedTotals.answered / disclosedTotals.disclosed : null
  const parseBaseline = stats.find((entry) => entry.key === 'no_ocr')
  const fastestParser = stats.filter((entry) => entry.extractSeconds != null && entry.extractSeconds > 0)
    .reduce<(typeof stats)[number] | null>((best, entry) => !best || Number(entry.extractSeconds) < Number(best.extractSeconds) ? entry : best, null)
  const parseSpeedup = fastestParser?.extractSeconds && parseBaseline?.extractSeconds
    ? Number(parseBaseline.extractSeconds) / Number(fastestParser.extractSeconds)
    : null
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
  const s3LeadsAccuracy = !!s3Stat && stats.every((entry) => entry.accuracy == null || Number(s3Stat.accuracy) >= Number(entry.accuracy))
  const s3CheapestTokens = !!s3Stat && stats.every((entry) => entry.inputTokens == null || Number(s3Stat.inputTokens) <= Number(entry.inputTokens))
  const s3FastestParse = !!s3Stat && stats.every((entry) => entry.extractSeconds == null || Number(s3Stat.extractSeconds) <= Number(entry.extractSeconds))
  const conclusion = s3Stat && s3LeadsAccuracy && s3CheapestTokens
    ? tr(
        `Intelligent scanning leads exact accuracy at ${formatMetric(s3Stat.accuracy)} with the fewest input tokens${s3FastestParse ? ' and the fastest document processing' : ''}.`,
        `インテリジェントスキャンが最少の入力トークン${s3FastestParse ? 'と最速のドキュメント処理' : ''}で最高の完全一致率${formatMetric(s3Stat.accuracy)}を達成しています。`,
      )
    : fastest && accuracyLeader && completeReportCount
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
          <Button onClick={() => onNavigate('strategy1')}>{tr('Run an extraction', '抽出を実行')} <ArrowRight size={16} /></Button>
        </div>
      </header>

      <div className="metric-grid">
        <MetricCard label={tr('Best exact accuracy', '最高完全一致率')} value={formatMetric(s3Stat?.accuracy ?? accuracyLeader?.accuracy)} detail={s3Stat ? `${s3Stat.label} · ${s3Stat.passes} ${tr('successful passes', '成功パス')}` : tr('Awaiting source-verified runs', '元資料検証済み実行を待っています')} />
        <MetricCard label={tr('Mean field coverage', '平均フィールドカバレッジ')} value={formatMetric(disclosedCoverage ?? s3Stat?.coverage ?? average('coverage'))} detail={tr('Share of the fields each source actually discloses that intelligent scanning answered', '各資料が実際に開示している項目のうちインテリジェントスキャンが回答した割合')} />
        <MetricCard label={tr('Matched reports', '対応レポート')} value={(s3ReportCount || completeReportCount).toLocaleString()} detail={tr('Distinct source-verified reports scored by intelligent scanning', 'インテリジェントスキャンが評価した元資料検証済みレポート数')} />
        <MetricCard label={tr('Fastest parser', '最速パーサー')} value={fastestParser?.label || '—'} detail={fastestParser && parseSpeedup ? `${formatDuration(fastestParser.extractSeconds)} ${tr('mean parse', '平均解析')} · ${parseSpeedup.toFixed(1)}× ${tr('faster than No OCR', 'OCRなし比で高速')}` : tr('No parse timing yet', '解析時間データはまだありません')} />
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
          <SectionHeading eyebrow={tr('Speed benchmark', '速度ベンチマーク')} title={tr('Document-processing speed per strategy', '戦略別ドキュメント処理速度')} description={tr('The parsing, OCR and gating step each strategy runs before the model call — the stage the strategies actually change. No OCR is the 1.0× baseline; the OCR and intelligent scanning multiples say how much faster their processing runs. Model-call time is excluded.', 'モデル呼び出し前の解析・OCR・ゲート処理の速度比較です。戦略が実際に変えている工程で、OCRなしを1.0倍の基準とし、各戦略の処理が何倍高速かを示します。モデル呼び出し時間は含みません。')} />
          {loading ? <div className="chart-skeleton" /> : <SpeedBenchmarkChart runs={benchmarkRuns} />}
        </Card>
        <Card className="chart-card coverage-card">
          <SectionHeading eyebrow={tr('Quality composition', '品質構成')} title={tr('Accuracy versus coverage', '正確度とカバレッジ')} description={tr('Coverage says a field was returned; exact accuracy says it matched the gold value.', 'カバレッジは項目の取得率、完全一致率は正解値との一致を示します。')} />
          {loading ? <div className="chart-skeleton" /> : <CoverageDonut runs={s3Runs.length ? s3Runs : benchmarkRuns} />}
        </Card>
      </div>

      <div className="dashboard-layout benchmark-frontier">
        <Card className="chart-card chart-card-wide">
          <SectionHeading eyebrow={tr('Experiment frontier', '実験フロンティア')} title={tr('Speed × accuracy curves', '速度×正確度カーブ')} description={tr('One curve per strategy: reports ordered fastest to slowest, pass time rising on a logarithmic scale. Each arm is scaled onto a common axis so different report counts stay comparable; the lower a curve sits, the faster the strategy.', '戦略ごとに1本のカーブ。レポートを速い順に並べ、パス時間を対数スケールで示します。各戦略を共通軸にスケールして比較可能にしています。曲線が低いほど高速です。')} />
          {loading ? <div className="chart-skeleton" /> : <AccuracySpeedChart runs={benchmarkRuns} />}
        </Card>
        <Card className="chart-card accuracy-card">
          <SectionHeading eyebrow={tr('Benchmark', 'ベンチマーク')} title={tr('Mean exact accuracy', '平均完全一致率')} description={tr('Scored source-bound passes grouped into no OCR, OCR enabled, and intelligent scanning.', '元資料に固定された評価済みパスをOCRなし、OCRあり、インテリジェントスキャンで集計しています。')} />
          {loading ? <div className="chart-skeleton" /> : <ParserAccuracyChart runs={benchmarkRuns} />}
        </Card>
      </div>

      <Card className="chart-card latency-distribution-card">
        <SectionHeading eyebrow={tr('Token efficiency', 'トークン効率')} title={tr('Input tokens × exact accuracy', '入力トークン×完全一致率')} description={tr('One bar per strategy: mean model input tokens per report on a logarithmic axis, with the strategy\u2019s mean exact accuracy printed above its bar. The shortest bar with the highest accuracy wins on both counts.', '戦略ごとに1本のバー。レポート別平均入力トークンを対数軸で示し、バーの上に平均完全一致率を表示します。最も短いバーで最も高い正確度が両面での勝者です。')} />
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
