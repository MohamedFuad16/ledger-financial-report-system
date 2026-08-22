import { useMemo, useState } from 'react'
import { BookOpen, Search } from 'lucide-react'
import type { SchemaRow } from '../types'
import { formatMoney } from '../lib/format'
import { Badge, Card, EmptyState, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

export function SchemaPage({ rows }: { rows: SchemaRow[] }) {
  const { tr, schemaText } = useLocale()
  const years = useMemo(() => Array.from(new Set(rows.flatMap((row) => Object.keys(row.golden_answers)))).sort(), [rows])
  const [year, setYear] = useState('2022')
  const [query, setQuery] = useState('')
  const filtered = rows.filter((row) => `${row.item} ${row.classification} ${row.subclassification} ${row.description} ${schemaText(row.item)} ${schemaText(row.classification)} ${schemaText(row.subclassification)} ${schemaText(row.description)}`.toLowerCase().includes(query.toLowerCase()))
  const grouped = filtered.reduce<Record<string, SchemaRow[]>>((groups, row) => {
    ;(groups[row.classification] ||= []).push(row)
    return groups
  }, {})

  return (
    <div className="page">
      <header className="page-header"><div><Badge tone="blue">{tr('Fixed output contract', '固定出力契約')}</Badge><h1>{tr('Benchmark target schema', 'ベンチマーク対象スキーマ')}</h1><p>{tr('The canonical 27-row asset taxonomy sent to every strategy, with year-specific reference values used only after extraction.', '全戦略に送る27行の標準資産分類です。年度別参照値は抽出後の評価にのみ使用します。')}</p></div></header>
      <div className="schema-summary">
        <Card><span>{tr('Rows', '行')}</span><strong>{rows.length}</strong><small>{tr('Immutable order', '固定順序')}</small></Card>
        <Card><span>{tr('Reference years', '参照年度')}</span><strong>{years.length}</strong><small>{years.length ? `FY${years[0]}–FY${years.at(-1)}` : '—'}</small></Card>
        <Card><span>{tr('Units', '単位')}</span><strong>{tr('M source currency', '元通貨の百万単位')}</strong><small>{tr('Declared per report', 'レポートごとに宣言')}</small></Card>
        <Card><span>{tr('Confidence', '信頼度')}</span><strong>≥ 0.80</strong><small>{tr('Acceptance threshold', '採用しきい値')}</small></Card>
      </div>
      <Card className="schema-card">
        <SectionHeading eyebrow={tr('Schema browser', 'スキーマブラウザー')} title={tr('Asset-side balance sheet', '資産側貸借対照表')} description={tr('Reference answers never enter the model prompt.', '参照回答がモデルプロンプトに入ることはありません。')} />
        <div className="table-toolbar">
          <label className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={tr('Search schema rows', 'スキーマ行を検索')} /></label>
          <label className="year-field"><span>{tr('Reference year', '参照年度')}</span><select value={year} onChange={(event) => setYear(event.target.value)}>{years.map((value) => <option key={value} value={value}>FY{value}</option>)}</select></label>
        </div>
        {!filtered.length ? <EmptyState icon={<BookOpen size={20} />} title={tr('No matching rows', '一致する行がありません')} description={tr('Try a different schema term.', '別のスキーマ用語を試してください。')} /> : (
          <div className="schema-groups">
            {Object.entries(grouped).map(([classification, group]) => group && (
              <section key={classification}>
                <div className="schema-group-title"><h3>{schemaText(classification)}</h3><Badge>{group.length} {tr('rows', '行')}</Badge></div>
                <div className="table-wrap">
                  <table className="schema-table"><thead><tr><th>{tr('Target item', '対象項目')}</th><th>{tr('Subclassification', '下位分類')}</th><th>{tr('Definition', '定義')}</th><th>FY{year} {tr('answer', '回答')}</th></tr></thead><tbody>{group.map((row) => <tr key={row.item}><td><strong>{schemaText(row.item)}</strong></td><td>{schemaText(row.subclassification) || '—'}</td><td>{schemaText(row.description)}</td><td className="numeric"><strong>{formatMoney(row.golden_answers[year])}</strong></td></tr>)}</tbody></table>
                </div>
              </section>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
