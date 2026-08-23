import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, ClipboardCheck, ExternalLink, FileDown, Flame, LoaderCircle, RefreshCw, Save, ScanText, Search, ShieldCheck, Trash2, TriangleAlert, X } from 'lucide-react'
import { api } from '../lib/api'
import type { CorpusDocument, CorpusManifest, CorpusTarget, CorpusVerification, CorpusVerificationRow, SettingsData } from '../types'
import { Badge, Button, Card, EmptyState, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'
import { convertCurrency, currencyPreference, restoreNativeCurrency } from '../lib/currency'
import { englishCompanyNames, showcaseDomains } from '../lib/companies'

function officialHost(url?: string) {
  try { return new URL(url || '').hostname.replace(/^www\./, '') } catch { return '' }
}

// Filing mirrors and gazette hosts are sources, not company identities; their
// favicons must never stand in for a company logo.
const MIRROR_HOSTS = /(?:^|\.)(?:edinet-fsa\.go\.jp|catr\.jp|kanpo\.go\.jp|irbank\.net|xj-storage\.jp|irpocket\.com|swcms\.net)$/

function CompanyLogo({ domain, label }: { domain: string; label: string }) {
  const [failed, setFailed] = useState(false)
  const monogram = (label.trim()[0] || '?').toLocaleUpperCase()
  if (!domain || failed) return <span className="corpus-logo-mark corpus-logo-monogram" aria-hidden="true">{monogram}</span>
  return <span className="corpus-logo-mark"><img src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`} alt="" loading="lazy" onError={() => setFailed(true)} /></span>
}

export function CorpusPage({ onNotify }: { settings: SettingsData | null; onNotify: (message: string, tone: 'success' | 'error') => void }) {
  const { locale, tr, schemaText } = useLocale()
  const [manifest, setManifest] = useState<CorpusManifest | null>(null)
  const [pendingDelete, setPendingDelete] = useState<CorpusDocument | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [reviewing, setReviewing] = useState<CorpusDocument | null>(null)
  const [verification, setVerification] = useState<CorpusVerification | null>(null)
  const [reviewRows, setReviewRows] = useState<CorpusVerificationRow[]>([])
  const [reviewPhase, setReviewPhase] = useState<'idle' | 'loading' | 'extracting'>('idle')
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [savingReview, setSavingReview] = useState(false)
  const [confirmApprove, setConfirmApprove] = useState(false)
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set())
  const [tableQuery, setTableQuery] = useState('')
  const [reviewPage, setReviewPage] = useState(1)
  const displayCurrency = currencyPreference()

  const refresh = () => api.corpus().then(setManifest).catch((error) => onNotify(error instanceof Error ? error.message : tr('Could not load the corpus.', 'コーパスを読み込めませんでした。'), 'error'))
  useEffect(() => {
    void refresh()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!pendingDelete) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !deleting) setPendingDelete(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [pendingDelete, deleting])

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      const result = await api.deleteCorpusDocument(pendingDelete.sha256)
      await refresh()
      setPendingDelete(null)
      onNotify(tr(`${result.deleted.filename || 'Annual report'} was removed from the downloaded corpus.`, `${result.deleted.filename || '年次報告書'}をダウンロード済みコーパスから削除しました。`), 'success')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('Could not delete the downloaded report.', 'ダウンロード済みレポートを削除できませんでした。'), 'error')
    } finally { setDeleting(false) }
  }

  const loadReview = async (document: CorpusDocument) => {
    setReviewPhase('loading')
    setReviewError(null)
    setVerification(null)
    setReviewRows([])
    try {
      let payload = await api.corpusVerification(document.sha256)
      if (payload.status !== 'assignment_supplied' && !payload.candidate_extracted) {
        setReviewPhase('extracting')
        payload = await api.extractCorpusVerification(document.sha256)
      }
      if (!payload.candidate_extracted) throw new Error(tr('The PDF extraction did not produce a review table. Retry extraction before reviewing.', 'PDF抽出で確認表を生成できませんでした。確認前に抽出を再試行してください。'))
      setVerification(payload)
      setReviewRows(payload.rows)
    } catch (error) {
      const message = error instanceof Error ? error.message : tr('Could not extract the verification sheet from the PDF.', 'PDFから検証シートを抽出できませんでした。')
      setReviewError(message)
      onNotify(message, 'error')
    } finally { setReviewPhase('idle') }
  }

  const openReview = (document: CorpusDocument) => {
    setReviewPage(document.balance_sheet_page || 1)
    setReviewing(document)
    void loadReview(document)
  }

  const updateReviewAnswer = (index: number, value: string) => {
    setReviewRows((current) => current.map((row, rowIndex) => rowIndex === index
      ? { ...row, answer_m_usd: restoreNativeCurrency(value.trim() === '' ? null : Number(value), verification?.currency || reviewing?.currency || 'USD', displayCurrency) }
      : row))
  }

  const approveReview = async () => {
    if (!reviewing || !verification?.candidate_extracted) return
    setSavingReview(true)
    try {
      const payload = await api.approveCorpusVerification(reviewing.sha256, reviewRows)
      setVerification(payload)
      setReviewRows(payload.rows)
      setConfirmApprove(false)
      await refresh()
      onNotify(tr('The 27-row answer table is now human verified for this exact PDF.', 'このPDFに対する27行の回答表を人による確認済みとして保存しました。'), 'success')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('Could not approve the verification sheet.', '検証シートを承認できませんでした。'), 'error')
    } finally { setSavingReview(false) }
  }

  const companyGroups = useMemo(() => {
    const needle = tableQuery.trim().toLocaleLowerCase()
    const groups: Record<string, { company: string; target?: CorpusTarget; documents: CorpusDocument[] }> = {}
    for (const target of manifest?.targets || []) {
      groups[target.company] = { company: target.company, target, documents: [] }
    }
    for (const document of manifest?.documents || []) {
      ;(groups[document.company] ||= { company: document.company, documents: [] }).documents.push(document)
    }
    return Object.values(groups)
      .map((group) => ({ ...group, documents: [...group.documents].sort((left, right) => right.fiscal_year - left.fiscal_year) }))
      // The library lists only companies whose reports are actually pinned;
      // research targets without a stored report are not corpus members.
      .filter((group) => group.documents.length > 0)
      .filter((group) => !needle || `${group.company} ${englishCompanyNames[group.company] || ''} ${group.target?.official_url || ''} ${group.documents.map((document) => `${document.filename} ${document.fiscal_year}`).join(' ')}`.toLocaleLowerCase().includes(needle))
      .sort((left, right) => {
        if (left.company.trim().toLocaleLowerCase() === '3m') return -1
        if (right.company.trim().toLocaleLowerCase() === '3m') return 1
        if (Boolean(left.documents.length) !== Boolean(right.documents.length)) return left.documents.length ? -1 : 1
        return left.company.localeCompare(right.company)
      })
  }, [manifest, tableQuery])
  const crawledCompanies = useMemo(() => {
    const targetByCompany = new Map((manifest?.targets || []).map((target) => [target.company, target]))
    const seen = new Map<string, { company: string; domain: string; years: number[] }>()
    for (const document of manifest?.documents || []) {
      const target = targetByCompany.get(document.company)
      const candidates = [officialHost(target?.official_url), document.official_source_verified ? officialHost(document.source_url) : '']
      const domain = candidates.find((host) => host && !MIRROR_HOSTS.test(host)) || ''
      const entry = seen.get(document.company) || { company: document.company, domain, years: [] }
      if (!entry.domain && domain) entry.domain = domain
      entry.years.push(document.fiscal_year)
      seen.set(document.company, entry)
    }
    return [...seen.values()]
      .map((entry) => ({ ...entry, years: [...entry.years].sort() }))
      .sort((left, right) => {
        if (left.company.trim().toLocaleLowerCase() === '3m') return -1
        if (right.company.trim().toLocaleLowerCase() === '3m') return 1
        if (Boolean(left.domain) !== Boolean(right.domain)) return left.domain ? -1 : 1
        if (left.years.length !== right.years.length) return right.years.length - left.years.length
        return left.company.localeCompare(right.company)
      })
  }, [manifest])
  // The showcase uses only curated brand domains with known-good icons; every
  // other company is represented by the "and N more" tile.
  const showcaseCompanies = crawledCompanies
    .filter((entry) => showcaseDomains[entry.company])
    .map((entry) => ({ ...entry, domain: showcaseDomains[entry.company] }))
    .slice(0, 10)
  const showcaseRemainder = Math.max(0, crawledCompanies.length - showcaseCompanies.length)
  const isVerified = (document: CorpusDocument) => ['assignment_supplied', 'human_verified', 'independently_verified'].includes(document.verification_status || '')
  const screeningState = (document: CorpusDocument) => document.screened === 'unreadable' ? 'unreadable' : isVerified(document) ? 'verified' : 'review'
  const toggleCompany = (company: string) => setExpandedCompanies((current) => {
    const next = new Set(current)
    if (next.has(company)) next.delete(company)
    else next.add(company)
    return next
  })
  const reviewAnswerUnit = `M ${displayCurrency.currency}`
  const reviewIsImmutable = Boolean(verification?.immutable) || verification?.status === 'assignment_supplied'
  const companyLabel = (company: string, officialUrl = '') => {
    if (locale === 'ja' || company.trim().toLocaleLowerCase() === '3m') return company
    return englishCompanyNames[company] || company
  }
  const localizedEvidence = (row: CorpusVerificationRow) => {
    const evidence = row.evidence || ''
    const hasJapanese = /[\u3040-\u30ff\u3400-\u9fff]/.test(evidence)
    if (evidence && (locale === 'en') !== hasJapanese) return evidence
    const page = row.source_page ? ` ${locale === 'ja' ? '' : 'page '}${row.source_page}` : ''
    const displayed = convertCurrency(row.answer_m_usd, verification?.currency || reviewing?.currency || 'USD', displayCurrency.currency, displayCurrency.jpyPerUsd)
    const value = displayed == null ? tr('an unscorable value', '評価対象外の値') : `${displayed.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${reviewAnswerUnit}`
    return locale === 'ja'
      ? `${schemaText(row.item)}は固定元PDF${page ? `の${page}ページ` : ''}で${value}として確認されています。原文は左側のPDFで確認できます。`
      : `${schemaText(row.item)} was verified${page ? ` on source ${page}` : ' against the pinned source PDF'} as ${value}. The original wording remains visible in the PDF.`
  }
  return (
    <div className="page corpus-page">
      <header className="page-header"><div><div className="page-kicker">{tr('Cloud benchmark data', 'クラウドベンチマークデータ')}</div><h1>{tr('Annual Report corpus', '年次報告書コーパス')}</h1><p>{tr('This golden dataset was crawled once with the Firecrawl API from official sources, screened locally, pinned by SHA-256, and verified. Crawling is now closed; the library below is the frozen benchmark corpus.', 'このゴールデンデータセットはFirecrawl APIで公式ソースから一度だけクロールし、ローカルで検査してSHA-256で固定・検証したものです。クロールは終了しており、以下のライブラリが凍結済みベンチマークコーパスです。')}</p></div></header>
      <div className="corpus-summary">
        <Card><span>{tr('Companies', '会社')}</span><strong>{manifest?.summary.companies_with_reports ?? manifest?.summary.companies ?? 0}</strong><small>{tr('with pinned reports in the corpus', 'コーパスに固定レポートあり')}</small></Card>
        <Card><span>{tr('Documents', '文書')}</span><strong>{manifest?.summary.documents ?? 0}</strong><small>FY2020–FY2025</small></Card>
        <Card><span>{tr('Benchmark verified', 'ベンチマーク検証済み')}</span><strong>{manifest?.summary.verified ?? 0}</strong><small>{tr('assignment gold or human approved', '課題正解または人による承認')}</small></Card>
        <Card><span>{tr('Ready for human review', '人による確認待ち')}</span><strong>{manifest?.summary.human_review_required ?? 0}</strong><small>{tr('PDF answers are extracted and prefilled', 'PDF回答を抽出して入力済み')}</small></Card>
      </div>

      <Card className="corpus-provenance">
        <SectionHeading eyebrow={tr('Golden dataset provenance', 'ゴールデンデータセットの出所')} title={tr('How I used Firecrawl to build this corpus', 'Firecrawlを使ったコーパス構築の方法')} description={tr('Every stored report below came from one bounded Firecrawl acquisition pass; no further crawling runs from this page.', '以下の全レポートは一度の限定的なFirecrawl取得パスで収集されたものです。このページから新たなクロールは実行されません。')} />
        <div className="firecrawl-explainer">
          <div className="firecrawl-step"><span>1</span><div><strong>{tr('Discover official sources', '公式ソースを探索')}</strong><p>{tr('Firecrawl map and search located each company’s official annual-report library, securities-report page, or public-gazette filing — never arbitrary search hits.', 'Firecrawlのmap/searchで各社の公式年次報告書ライブラリ、有価証券報告書ページ、官報公告を特定しました。任意の検索結果は採用していません。')}</p></div></div>
          <div className="firecrawl-step"><span>2</span><div><strong>{tr('Download & screen locally', 'ダウンロードとローカル検査')}</strong><p>{tr('Ledger downloaded each candidate PDF directly, then confirmed company identity, annual-document type, fiscal year, and a readable balance sheet from inside the file.', 'LedgerがPDFを直接ダウンロードし、ファイル内部から会社の同一性、年次文書種別、会計年度、貸借対照表の可読性を確認しました。')}</p></div></div>
          <div className="firecrawl-step"><span>3</span><div><strong>{tr('Pin & verify', '固定と検証')}</strong><p>{tr('Accepted files are pinned by SHA-256; answer tables are verified against that exact hash, and unscorable rows stay explicitly unscorable rather than fabricated.', '採用ファイルはSHA-256で固定し、回答表はそのハッシュに対して検証します。評価不能な行は捏造せず、明示的に評価対象外のまま保持します。')}</p></div></div>
        </div>
        <div className="corpus-logo-grid">{showcaseCompanies.map((entry) => <div className="corpus-logo-tile" key={entry.company} title={entry.company}><CompanyLogo domain={entry.domain} label={companyLabel(entry.company)} /><span><strong>{companyLabel(entry.company)}</strong><small>{entry.years.map((year) => `FY${year}`).join(' · ')}</small></span></div>)}{showcaseRemainder > 0 && <div className="corpus-logo-tile corpus-logo-more"><span className="corpus-logo-mark corpus-logo-monogram" aria-hidden="true">…</span><span><strong>{tr(`and ${showcaseRemainder} more client${showcaseRemainder === 1 ? '' : 's'}`, `ほか${showcaseRemainder}社`)}</strong><small>{tr('all pinned in the library below', '以下のライブラリに全社掲載')}</small></span></div>}</div>
        <p className="corpus-provenance-footnote"><Flame size={14} /> {tr('The crawl phase is complete and the remaining Firecrawl credits are reserved; this corpus is frozen for benchmarking.', 'クロール工程は完了し、残りのFirecrawlクレジットは温存しています。このコーパスはベンチマーク用に凍結済みです。')}</p>
      </Card>

      <Card className="corpus-table-card">
        <SectionHeading eyebrow={tr('Pinned manifest', '固定マニフェスト')} title={tr('Annual Report Library', '年次報告書ライブラリ')} description={tr('One row per company actually held in the corpus, each report pinned by SHA-256. Expand a company to inspect its fiscal years.', 'コーパスに実際に保存されている会社のみを1行ずつ表示し、各レポートはSHA-256で固定されています。会社を展開すると年度別に確認できます。')} action={<label className="search-field corpus-table-search"><Search size={15} /><input value={tableQuery} onChange={(event) => setTableQuery(event.target.value)} placeholder={tr('Search companies or years', '会社または年度を検索')} /></label>} />
        {!companyGroups.length ? <EmptyState icon={<Search size={21} />} title={tr('No matching companies', '一致する会社がありません')} description={tr('Try a different company name or fiscal year.', '別の会社名または年度をお試しください。')} /> : <div className="table-wrap corpus-company-table-wrap"><table className="corpus-table corpus-company-table"><thead><tr>
          <th>{tr('Company / PDF name', '会社／PDF名')}</th><th>{tr('Fiscal year', '会計年度')}</th><th>{tr('Screening', '検査')}</th><th>{tr('Answers', '回答')}</th><th>{tr('Source', 'ソース')}</th><th className="corpus-delete-column">{tr('Delete', '削除')}</th>
        </tr></thead><tbody>{companyGroups.flatMap(({ company, documents, target }) => {
          const expanded = expandedCompanies.has(company) || Boolean(tableQuery.trim())
          const verifiedCount = documents.filter(isVerified).length
          const unreadableCount = documents.filter((document) => document.screened === 'unreadable').length
          const groupState = !documents.length ? 'pending' : unreadableCount ? 'unreadable' : verifiedCount === documents.length ? 'verified' : 'review'
          const yearLabel = !documents.length
            ? tr('No report stored', 'レポート未保存')
            : documents.length === 1
            ? `FY${documents[0].fiscal_year}`
            : `FY${documents[documents.length - 1].fiscal_year}–FY${documents[0].fiscal_year}`
          const rows = [<tr className="corpus-company-row" key={`company-${company}`}>
            <td><button className="corpus-company-toggle" type="button" onClick={() => documents.length && toggleCompany(company)} aria-expanded={expanded} disabled={!documents.length}>{documents.length ? expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} /> : <span className="corpus-company-placeholder" />}<span><strong>{companyLabel(company, target?.official_url || documents[0]?.source_url)}</strong><small>{documents.length ? `${documents.length} ${tr(documents.length === 1 ? 'fiscal year' : 'fiscal years', '年度')}` : tr('research target', '調査対象')}</small></span></button></td>
            <td>{yearLabel}</td>
            <td><Badge tone={groupState === 'unreadable' ? 'red' : groupState === 'verified' ? 'green' : 'amber'}>{groupState === 'pending' ? tr('Awaiting report', 'レポート待ち') : groupState === 'unreadable' ? tr('Unreadable', '読取不可') : groupState === 'verified' ? tr('Verified', '確認済み') : tr('Review', '確認')}</Badge></td>
            <td><span className="company-answer-summary">{documents.length ? `${verifiedCount}/${documents.length} ${tr('verified', '確認済み')}` : '—'}</span></td>
            <td>{documents.length ? <span className="company-expand-hint">{tr('Expand to inspect annual reports', '展開して年次報告書を確認')}</span> : target?.official_url ? <a href={target.official_url} target="_blank" rel="noreferrer">{tr('Open official website', '公式サイトを開く')} <ExternalLink size={13} /></a> : '—'}</td>
            <td className="corpus-delete-column" />
          </tr>]
          if (!expanded) return rows
          return rows.concat(documents.map((document) => {
            const state = screeningState(document)
            return <tr className="corpus-year-row" key={document.sha256}>
              <td><span className="corpus-year-file"><FileDown size={14} /><span><strong>{document.filename}</strong><small>{document.official_source_verified ? <><ShieldCheck size={12} /> {tr('official domain', '公式ドメイン')}</> : tr('source review required', 'ソース確認が必要')}</small></span></span></td>
              <td>FY{document.fiscal_year}</td>
              <td><Badge tone={state === 'unreadable' ? 'red' : state === 'verified' ? 'green' : 'amber'}>{state === 'unreadable' ? tr('Unreadable', '読取不可') : state === 'verified' ? tr('Verified', '確認済み') : tr('Review', '確認')}</Badge></td>
              <td><button className="corpus-review-button" type="button" onClick={() => openReview(document)}><ClipboardCheck size={14} /> {isVerified(document) ? tr('View answers', '回答を表示') : tr('Review answers', '回答を確認')}</button></td>
              <td><a href={document.source_url} target="_blank" rel="noreferrer">{tr('Open source', 'ソースを開く')} <ExternalLink size={13} /></a></td>
              <td className="corpus-delete-column"><button className="corpus-delete-button" type="button" onClick={() => setPendingDelete(document)} aria-label={tr(`Delete ${document.filename}`, `${document.filename}を削除`)}><Trash2 size={15} /><span>{tr('Delete', '削除')}</span></button></td>
            </tr>
          }))
        })}</tbody></table></div>}
      </Card>
      {reviewing && <div className="review-sheet-backdrop" role="presentation">
        <section className="review-sheet" role="dialog" aria-modal="true" aria-labelledby="review-sheet-title">
          <header><div><div className="eyebrow">{tr('Answer review', '回答の確認')}</div><h2 id="review-sheet-title">{companyLabel(reviewing.company, reviewing.source_url)} · FY{reviewing.fiscal_year}</h2><p>{tr('Ledger extracts and pre-fills all 27 rows from the pinned PDF first. Compare the values with the PDF, correct any mistakes, then save and approve the reviewed table.', 'Ledgerが固定PDFから27項目を先に抽出して入力します。PDFと照合し、誤りを修正してから確認表を保存・承認してください。')}</p></div><button type="button" onClick={() => { setReviewing(null); setConfirmApprove(false); setReviewError(null) }} aria-label={tr('Close review', 'レビューを閉じる')}><X size={18} /></button></header>
          <div className="review-sheet-actions"><a className="button secondary" href={api.corpusPdfUrl(reviewing.sha256)} target="_blank" rel="noreferrer"><ExternalLink size={15} /> {tr('Open searchable PDF', '検索可能なPDFを開く')}</a>{reviewPhase === 'extracting' ? <Badge tone="blue">{tr('Extracting from PDF…', 'PDFから抽出中…')}</Badge> : verification && <Badge tone={verification.status === 'human_review_required' ? 'amber' : 'green'}>{verification.status === 'human_review_required' ? tr('Review', '確認') : tr('Verified', '確認済み')}</Badge>}{verification?.candidate_extracted && <span className="candidate-row-summary">{tr(`27 rows prefilled · ${reviewRows.filter((row) => row.answer_m_usd !== null).length} values found`, `27項目を入力済み・${reviewRows.filter((row) => row.answer_m_usd !== null).length}件の値を検出`)}</span>}{verification?.consensus_summary && <span className="candidate-consensus-summary">{tr(`${verification.consensus_summary.successful_passes} semantic-mapping pass · ${verification.consensus_summary.exact_agreement_rows + verification.consensus_summary.stable_rows}/27 stable rows`, `セマンティックマッピング ${verification.consensus_summary.successful_passes}回 · 安定行 ${verification.consensus_summary.exact_agreement_rows + verification.consensus_summary.stable_rows}/27`)}</span>}</div>
          <div className="review-workspace">
            <aside className="review-pdf-pane">
            <div className="review-pdf-head"><ScanText size={16} /><span className="review-pdf-title"><strong>{reviewing.filename}</strong><small>SHA-256 {reviewing.sha256.slice(0, 12)}… · {tr('pinned source PDF', '固定元PDF')}</small></span></div>
            <div className="review-page-nav">
              <button type="button" onClick={() => setReviewPage((current) => Math.max(1, current - 1))} disabled={reviewPage <= 1} aria-label={tr('Previous page', '前のページ')}><ChevronLeft size={15} /></button>
              <span className="review-page-indicator">{tr('Page', 'ページ')} <input type="number" min={1} max={reviewing.pages || 1} value={reviewPage} onChange={(event) => { const next = Number(event.target.value); if (Number.isFinite(next)) setReviewPage(Math.min(Math.max(1, Math.round(next)), reviewing.pages || 1)) }} aria-label={tr('Go to page', 'ページへ移動')} /> / {reviewing.pages || 1}</span>
              <button type="button" onClick={() => setReviewPage((current) => Math.min(reviewing.pages || 1, current + 1))} disabled={reviewPage >= (reviewing.pages || 1)} aria-label={tr('Next page', '次のページ')}><ChevronRight size={15} /></button>
              {reviewing.balance_sheet_page ? <button type="button" className={`review-balance-jump ${reviewPage === reviewing.balance_sheet_page ? 'is-active' : ''}`} onClick={() => setReviewPage(reviewing.balance_sheet_page || 1)}>{tr(`Balance sheet p.${reviewing.balance_sheet_page}`, `貸借対照表 p.${reviewing.balance_sheet_page}`)}</button> : null}
              <small>{tr('⌘F / Ctrl+F searches inside the PDF', '⌘F / Ctrl+FでPDF内を検索')}</small>
            </div>
            <div className="review-pdf-frame"><iframe src={`${api.corpusPdfUrl(reviewing.sha256)}#page=${reviewPage}&zoom=page-fit&toolbar=0&navpanes=0`} key={`pdf-${reviewPage}`} title={tr('Source annual report PDF', '元の年次報告書PDF')} tabIndex={0} /></div></aside>
            <div className="review-answer-pane">
              {reviewPhase !== 'idle' ? <div className="review-sheet-loading" role="status"><LoaderCircle className="spin" size={22} /><strong>{reviewPhase === 'extracting' ? tr('Preparing a PDF-derived review draft…', 'PDFから確認用の下書きを作成中…') : tr('Loading the stored answer sheet…', '保存済み回答表を読み込んでいます…')}</strong><span>{reviewPhase === 'extracting' ? tr('No verified answer sheet is stored for this exact PDF yet. Ledger is mapping the 27 rows now; you will only need to check and correct them.', 'このPDFに固定された検証済み回答表はまだありません。Ledgerが27項目をマッピング中です。確認と修正のみ行ってください。') : tr('Verified source-bound answers appear immediately when they exist for this PDF hash.', 'このPDFハッシュに固定された検証済み回答がある場合は、すぐに表示されます。')}</span></div> : reviewError ? <div className="review-extraction-error"><TriangleAlert size={24} /><strong>{tr('PDF extraction did not complete', 'PDF抽出が完了しませんでした')}</strong><p>{reviewError}</p><Button variant="secondary" onClick={() => void loadReview(reviewing)}><RefreshCw size={15} /> {tr('Retry PDF extraction', 'PDF抽出を再試行')}</Button></div> : <><div className="review-prefill-note"><ScanText size={17} /><div><strong>{reviewIsImmutable ? tr('Audited answers — read only', '監査済み回答 — 読み取り専用') : tr('Extracted prefill — verify, then correct', '抽出済み入力 — 照合して修正')}</strong><span>{reviewIsImmutable ? tr(`This source-bound table has already been independently verified against the exact PDF. Values are displayed in ${displayCurrency.currency}; scoring remains in ${verification?.currency || reviewing.currency}.`, `この表は対象PDFと照合して独立検証済みです。表示は${displayCurrency.currency}、評価は${verification?.currency || reviewing.currency}のままです。`) : tr(`These values came from the PDF. Values are displayed in ${displayCurrency.currency}; edit only mismatches, then approve.`, `これらの値はPDFから抽出されています。${displayCurrency.currency}表示で不一致のみ修正し、承認してください。`)}</span></div></div><div className="review-table-wrap"><table className="review-table"><thead><tr><th>#</th><th>{tr('Classification', '分類')}</th><th>{tr('Item', '項目')}</th><th>{tr('Extracted answer', '抽出回答')} ({reviewAnswerUnit})</th><th>{tr('Agreement', '一致度')}</th><th>{tr('Page', 'ページ')}</th><th>{tr('Extracted evidence', '抽出根拠')}</th></tr></thead><tbody>{reviewRows.map((row, index) => <tr key={row.item}><td>{String(index + 1).padStart(2, '0')}</td><td>{schemaText(row.classification)}<small>{schemaText(row.subclassification) || '—'}</small></td><td><strong>{schemaText(row.item)}</strong></td><td><input type="number" step="any" value={convertCurrency(row.answer_m_usd, verification?.currency || reviewing.currency, displayCurrency.currency, displayCurrency.jpyPerUsd) ?? ''} disabled={reviewIsImmutable} onChange={(event) => updateReviewAnswer(index, event.target.value)} aria-label={`${schemaText(row.item)} answer`} /></td><td>{row.agreement_count !== undefined ? <Badge tone={row.stability === 'disagreement' || row.stability === 'missing' ? 'amber' : 'green'}>{row.agreement_count}/{verification?.consensus_summary?.requested_passes ?? row.successful_passes ?? 1}</Badge> : '—'}</td><td>{row.source_page ?? '—'}</td><td><div className="review-evidence" title={row.evidence || undefined}>{localizedEvidence(row) || '—'}</div></td></tr>)}</tbody></table></div></>}
            </div>
          </div>
          <footer><span>{reviewIsImmutable ? tr('This verified table is bound to the exact PDF SHA-256 and cannot be edited.', 'この検証済み表はPDFの正確なSHA-256に固定されており、編集できません。') : tr('Extracted answers are provisional, never automatic gold. Approval confirms that you checked the complete table against this exact PDF.', '抽出回答は暫定値であり、自動的な正解データにはなりません。承認すると、このPDFと表全体を照合済みであることを確認します。')}</span>{!reviewIsImmutable && <Button onClick={() => setConfirmApprove(true)} disabled={reviewPhase !== 'idle' || Boolean(reviewError) || !verification?.candidate_extracted || savingReview}><Save size={15} /> {verification?.status === 'human_verified' ? tr('Save updated approval', '更新した承認を保存') : tr('Save & approve reviewed answers', '確認済み回答を保存・承認')}</Button>}</footer>
        </section>
      </div>}
      {confirmApprove && reviewing && <div className="confirm-dialog-backdrop review-confirm" role="presentation" onMouseDown={() => !savingReview && setConfirmApprove(false)}><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="approve-review-title" onMouseDown={(event) => event.stopPropagation()}><div className="confirm-dialog-icon approve"><ShieldCheck size={20} /></div><div className="eyebrow">{tr('Benchmark approval', 'ベンチマーク承認')}</div><h2 id="approve-review-title">{tr('Save and approve all 27 rows?', '27項目すべてを保存・承認しますか？')}</h2><p>{tr('You are confirming that you checked the prefilled answers against the source PDF and corrected any mistakes. The approved table will be bound to this PDF SHA-256.', '入力済み回答を元PDFと照合し、誤りを修正したことを確認します。承認済み表はこのPDFのSHA-256に紐づきます。')}</p><div className="confirm-dialog-actions"><Button variant="ghost" onClick={() => setConfirmApprove(false)} disabled={savingReview}>{tr('Keep reviewing', '確認を続ける')}</Button><Button onClick={approveReview} disabled={savingReview}><ShieldCheck size={15} /> {savingReview ? tr('Saving…', '保存中…') : tr('Save & confirm approval', '保存して承認を確定')}</Button></div></section></div>}
      {pendingDelete && <div className="confirm-dialog-backdrop" role="presentation" onMouseDown={() => !deleting && setPendingDelete(null)}>
        <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-report-title" onMouseDown={(event) => event.stopPropagation()}>
          <button className="confirm-dialog-close" type="button" onClick={() => setPendingDelete(null)} disabled={deleting} aria-label={tr('Close dialog', 'ダイアログを閉じる')}><X size={18} /></button>
          <div className="confirm-dialog-icon"><Trash2 size={20} /></div>
          <div className="eyebrow">{tr('Downloaded report', 'ダウンロード済みレポート')}</div>
          <h2 id="delete-report-title">{tr('Delete this annual report?', 'この年次報告書を削除しますか？')}</h2>
          <p>{tr(`${pendingDelete.filename} will be removed from persistent corpus storage and its pinned manifest entry. Existing extraction runs will remain available.`, `${pendingDelete.filename}を永続コーパスストレージと固定マニフェストから削除します。既存の抽出実行は保持されます。`)}</p>
          <div className="confirm-dialog-actions"><Button variant="ghost" onClick={() => setPendingDelete(null)} disabled={deleting} autoFocus>{tr('Cancel', 'キャンセル')}</Button><Button variant="danger" onClick={confirmDelete} disabled={deleting}><Trash2 size={15} /> {deleting ? tr('Deleting…', '削除中…') : tr('Delete report', 'レポートを削除')}</Button></div>
        </section>
      </div>}
    </div>
  )
}
