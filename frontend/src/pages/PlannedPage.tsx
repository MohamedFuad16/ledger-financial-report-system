import { ArrowRight, CheckCircle2, Database, Search, Sparkles } from 'lucide-react'
import type { PanelKey } from '../types'
import { Badge, Button, Card } from '../components/ui'
import { useLocale } from '../lib/i18n'

export function PlannedPage({ strategy, onNavigate }: { strategy: 3 | 4; onNavigate: (key: PanelKey) => void }) {
  const { tr } = useLocale()
  const rag = strategy === 3
  const steps = rag
    ? [{ icon: Search, title: tr('Locate', '特定'), text: tr('Find the balance sheet and accounting notes with deterministic page candidates.', '貸借対照表と会計注記の候補ページを決定的に特定します。') }, { icon: Database, title: tr('Retrieve', '検索'), text: tr('Build a small evidence packet instead of sending the whole report.', 'レポート全体ではなく小さな証拠パケットを作成します。') }, { icon: Sparkles, title: tr('Extract', '抽出'), text: tr('Apply the same 27-row contract to grounded context.', '根拠付きコンテキストに同じ27行契約を適用します。') }]
    : [{ icon: CheckCircle2, title: tr('Verify', '検証'), text: tr('Identify failed or skipped subtotal identities.', '失敗またはスキップした小計恒等式を特定します。') }, { icon: Sparkles, title: tr('Reflect', '再考'), text: tr('Re-ask only about implicated rows and missing evidence.', '関係する行と不足証拠だけを再質問します。') }, { icon: CheckCircle2, title: tr('Reconcile', '照合'), text: tr('Accept a correction only when the deterministic checks improve.', '決定的検証が改善した場合のみ修正を採用します。') }]
  return (
    <div className="page planned-page">
      <header className="page-header"><div><Badge>{tr('Strategy', '戦略')} 0{strategy} · {tr('Planned', '予定')}</Badge><h1>{rag ? tr('Hybrid retrieval & RAG', 'ハイブリッド検索とRAG') : tr('Agentic accounting & verification', 'エージェント会計検証')}</h1><p>{rag ? tr('Reduce context cost and improve obscure-note coverage by retrieving only the evidence the schema needs.', 'スキーマに必要な証拠だけを検索し、コンテキストコストを削減して注記のカバレッジを高めます。') : tr('Turn validation failures into a focused correction loop without changing values by guesswork.', '推測で値を変えず、検証失敗を集中修正ループに変換します。')}</p></div></header>
      <Card className="planned-hero">
        <div className="planned-grid-art" aria-hidden="true">{Array.from({ length: 49 }, (_, index) => <i key={index} />)}</div>
        <span>{tr('Research boundary', '研究境界')}</span>
        <h2>{rag ? tr('Can targeted evidence beat a 130k-token whole-report prompt?', '対象証拠は13万トークンの全レポートプロンプトを上回れるか？') : tr('Can deterministic checks guide a safe second pass?', '決定的検証で安全な第2パスを導けるか？')}</h2>
        <p>{tr('The output model, confidence gate, benchmark, and evidence contract remain unchanged so the result stays comparable to Strategies 1 and 2.', '出力モデル、信頼度ゲート、ベンチマーク、証拠契約を変えず、戦略1・2との比較可能性を保ちます。')}</p>
      </Card>
      <div className="planned-flow">{steps.map((step, index) => { const Icon = step.icon; return <Card key={step.title}><span>0{index + 1}</span><div className="strategy-icon"><Icon size={18} /></div><h3>{step.title}</h3><p>{step.text}</p>{index < steps.length - 1 && <ArrowRight className="flow-arrow" size={18} />}</Card> })}</div>
      <div className="planned-cta"><div><strong>{tr('Build on the verified baseline', '検証済みベースラインを基に構築')}</strong><p>{tr('Review the active experiments and current failure taxonomy first.', 'まず有効な実験と現在の失敗分類を確認してください。')}</p></div><Button onClick={() => onNavigate('dashboard')}>{tr('Return to overview', '概要に戻る')} <ArrowRight size={15} /></Button></div>
    </div>
  )
}
