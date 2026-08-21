import { ArrowRight, FileSearch2, Filter, Gauge, ShieldCheck } from 'lucide-react'
import type { PanelKey } from '../types'
import { Badge, Button, Card } from '../components/ui'
import { useLocale } from '../lib/i18n'

export function StrategyThreePage({ onNavigate }: { onNavigate: (key: PanelKey) => void }) {
  const { tr } = useLocale()
  const steps = [
    {
      icon: FileSearch2,
      title: tr('Score complete pages', 'ページ全体を評価'),
      text: tr('Split only at existing page markers, then rank every page with schema terms, accounting synonyms, headings, and BM25-style lexical scores.', '既存のページ境界だけで分け、スキーマ用語・会計同義語・見出し・BM25型の語彙スコアで全ページを順位付けします。'),
    },
    {
      icon: Filter,
      title: tr('Keep evidence, reject noise', '根拠を残しノイズを除外'),
      text: tr('Retain the balance sheet, relevant notes, and adjacent pages; remove boilerplate only when deterministic reject patterns and low relevance agree.', '貸借対照表・関連注記・隣接ページを残し、決定的な除外パターンと低関連度が一致した場合だけ定型ページを除外します。'),
    },
    {
      icon: ShieldCheck,
      title: tr('Map and verify', 'マッピングと検証'),
      text: tr('Send the smaller page packet through the same model, 27-row contract, confidence gate, reconciliation, and human verification flow.', '絞り込んだページ群を同じモデル・27行契約・信頼度基準・照合・人手確認フローに通します。'),
    },
  ]

  return (
    <div className="page planned-page strategy-three-page">
      <header className="page-header"><div><Badge>{tr('Strategy', '戦略')} 03 · {tr('Planned', '予定')}</Badge><h1>{tr('Schema-guided page filtering', 'スキーマ誘導ページ選別')}</h1><p>{tr('Reduce model input by selecting relevant Markdown pages before semantic mapping—without a vector store, arbitrary token chunks, or a separate generation system.', 'ベクトルストア、任意のトークン分割、別の生成システムを使わず、意味マッピング前に関連Markdownページを選びモデル入力を削減します。')}</p></div></header>
      <Card className="planned-hero">
        <div className="planned-grid-art" aria-hidden="true">{Array.from({ length: 49 }, (_, index) => <i key={index} />)}</div>
        <span>{tr('Planned experiment', '計画中の実験')}</span>
        <h2>{tr('Can page selection cut tokens without losing any evidence needed by the 27-row schema?', 'ページ選別で27行スキーマに必要な根拠を失わずトークンを削減できるか？')}</h2>
        <p>{tr('The hard requirement is evidence-page recall. Token savings do not count as a win if a balance-sheet note disappears or exact accuracy falls.', '最重要条件は根拠ページの再現率です。貸借対照表注記が欠落したり完全一致率が下がるなら、トークン削減は成功ではありません。')}</p>
      </Card>
      <div className="planned-flow">{steps.map((step, index) => { const Icon = step.icon; return <Card key={step.title}><span>0{index + 1}</span><div className="strategy-icon"><Icon size={18} /></div><h3>{step.title}</h3><p>{step.text}</p>{index < steps.length - 1 && <ArrowRight className="flow-arrow" size={18} />}</Card> })}</div>
      <Card className="strategy-three-guardrails">
        <div><Gauge size={20} /><span><strong>{tr('Acceptance gates', '合格基準')}</strong><small>{tr('Measure evidence-page recall, selected-page ratio, input tokens, latency, cost, field coverage, and exact accuracy against the whole-document control.', '全ページ入力との対照で、根拠ページ再現率・選択ページ比率・入力トークン・遅延・コスト・フィールドカバレッジ・完全一致率を測定します。')}</small></span></div>
        <ul><li>{tr('Always retain the detected balance-sheet page and neighboring pages.', '検出した貸借対照表ページと隣接ページは必ず保持。')}</li><li>{tr('Use positive schema patterns and explicit reject patterns; never reject from a low score alone.', '正のスキーマパターンと明示的除外パターンを併用し、低スコアだけでは除外しない。')}</li><li>{tr('Fall back to the complete document when coverage or selector confidence is below threshold.', 'カバレッジまたは選別信頼度が基準未満なら全文書入力へフォールバック。')}</li></ul>
      </Card>
      <div className="planned-cta"><div><strong>{tr('Status: specification only', '状態：仕様のみ')}</strong><p>{tr('No Strategy 3 extraction endpoint is active yet; this page records the build and evaluation contract.', 'Strategy 3の抽出エンドポイントは未実装です。このページは構築・評価契約を記録します。')}</p></div><Button onClick={() => onNavigate('dashboard')}>{tr('Return to overview', '概要に戻る')} <ArrowRight size={15} /></Button></div>
    </div>
  )
}
