import { ArrowRight, CheckCircle2, Database, Gauge, Layers3 } from 'lucide-react'
import type { PanelKey, RunSummary } from '../types'
import { formatDuration, formatMetric, groupParserStats, matchedParserCohort } from '../lib/format'
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
  const benchmarkRuns = matchedParserCohort(runs)
  const scored = benchmarkRuns.filter((run) => run.accuracy != null)
  const average = (key: keyof RunSummary) => {
    const source = key === 'accuracy' || key === 'coverage' ? scored : runs
    const values = source.map((run) => run[key]).filter((value) => value != null).map(Number).filter(Number.isFinite)
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
  }
  const stats = groupParserStats(runs).filter((entry) => entry.runs)
  const fastest = stats.length ? stats.reduce((a, b) => Number(a.extractSeconds ?? Infinity) <= Number(b.extractSeconds ?? Infinity) ? a : b) : null
  const accuracyLeader = stats.length ? stats.reduce((a, b) => Number(a.accuracy ?? -Infinity) >= Number(b.accuracy ?? -Infinity) ? a : b) : null
  const conclusion = fastest && accuracyLeader
    ? fastest.key === accuracyLeader.key
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
          <Button onClick={() => onNavigate('strategy2')}>{tr('Run an extraction', '抽出を実行')} <ArrowRight size={16} /></Button>
        </div>
      </header>

      <div className="metric-grid">
        <MetricCard label={tr('Best exact accuracy', '最高完全一致率')} value={formatMetric(accuracyLeader?.accuracy)} detail={accuracyLeader ? `${accuracyLeader.short} · ${accuracyLeader.runs} ${tr('matched reports', '対応レポート')}` : tr('Awaiting a matched parser cohort', '対応するパーサー比較を待っています')} />
        <MetricCard label={tr('Mean field coverage', '平均フィールドカバレッジ')} value={formatMetric(average('coverage'))} detail={tr('Fields returned above confidence gate', '信頼度基準を超えて取得された項目')} />
        <MetricCard label={tr('Completed experiments', '完了した実験')} value={runs.length.toLocaleString()} detail={`${new Set(runs.map((run) => run.fiscal_year).filter(Boolean)).size} ${tr('fiscal years in the library', '会計年度を保存')}`} />
        <MetricCard label={tr('Fastest parser', '最速パーサー')} value={fastest?.short || '—'} detail={fastest ? `${formatDuration(fastest.extractSeconds)} ${tr('mean parse time', '平均解析時間')}` : tr('No timing data yet', '時間データはまだありません')} />
      </div>

      <SectionHeading eyebrow={tr('Research tracks', '研究トラック')} title={tr('Extraction strategies', '抽出戦略')} description={tr('Each strategy changes one boundary while preserving the output contract.', '出力契約を保ったまま、各戦略で一つの境界だけを変更します。')} />
      <div className="strategy-grid dashboard-strategy-grid">
        {[
          { number: '01', title: tr('Direct LLM baseline', 'LLM直接抽出ベースライン'), body: tr('Raw page-by-page PyPDF text. The intentionally plain control condition.', 'PyPDFのページ単位の生テキストを使う基本対照条件です。'), status: tr('Active', '有効'), tone: 'green' as const, panel: 'strategy1' as PanelKey, icon: Gauge },
          { number: '02', title: tr('Representation bake-off', '文書表現ベイクオフ'), body: tr('PyMuPDF4LLM, Docling, and pdf-inspector on the same report and prompt.', '同一レポートとプロンプトで複数パーサーを比較します。'), status: tr('Active', '有効'), tone: 'blue' as const, panel: 'strategy2' as PanelKey, icon: Layers3 },
          { number: '03', title: tr('Hybrid retrieval & RAG', 'ハイブリッド検索とRAG'), body: tr('Retrieve the balance sheet and relevant notes before extraction.', '抽出前に貸借対照表と関連注記を検索します。'), status: tr('Planned', '予定'), tone: 'neutral' as const, panel: 'strategy3' as PanelKey, icon: Database },
          { number: '04', title: tr('Agentic accounting', 'エージェント会計検証'), body: tr('Re-ask only about rows implicated by failed identities.', '不一致に関係する行だけを再確認します。'), status: tr('Planned', '予定'), tone: 'neutral' as const, panel: 'strategy4' as PanelKey, icon: CheckCircle2 },
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
          {loading ? <div className="chart-skeleton" /> : <SpeedBenchmarkChart runs={benchmarkRuns} />}
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
          {loading ? <div className="chart-skeleton" /> : <ParserAccuracyChart runs={benchmarkRuns} />}
        </Card>
      </div>

      <div className="dashboard-lower">
        <Card className="method-card conclusion-card">
          <SectionHeading eyebrow={tr('Current conclusion', '現在の結論')} title={conclusion} description={tr('This conclusion is calculated from the completed benchmark runs currently stored in the workspace.', 'この結論は、ワークスペースに保存された完了済みベンチマークから算出されます。')} />
        </Card>
      </div>

      <Card className="recent-card">
        <SectionHeading eyebrow={tr('Library', 'ライブラリ')} title={tr('Recent experiment runs', '最近の実験実行')} description={tr('The most recent completed predictions across every parser.', '全パーサーの最新完了結果です。')} action={<Button variant="secondary" onClick={() => onNavigate('history')}>{tr('View all', 'すべて表示')} <ArrowRight size={15} /></Button>} />
        <RunTable runs={runs.slice(0, 6)} compact />
      </Card>
    </div>
  )
}
