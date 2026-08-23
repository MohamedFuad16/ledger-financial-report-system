import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronRight, ClipboardCheck, ExternalLink, FileDown, FileSearch, FolderSearch2, Image, LoaderCircle, Play, RefreshCw, Save, ScanText, Search, ShieldCheck, Sparkles, Trash2, TriangleAlert, X } from 'lucide-react'
import { api } from '../lib/api'
import type { CorpusDocument, CorpusJob, CorpusManifest, CorpusTarget, CorpusVerification, CorpusVerificationRow, SettingsData } from '../types'
import { Badge, Button, Card, EmptyState, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'
import { convertCurrency, currencyPreference, restoreNativeCurrency } from '../lib/currency'

const availableYears = [2020, 2021, 2022, 2023, 2024, 2025]

const englishCompanyNames: Record<string, string> = {
  'AppBank株式会社': 'AppBank Inc.', 'Byside株式会社': 'Byside Inc.', 'JR九州エンジニアリング株式会社': 'JR Kyushu Engineering Co., Ltd.',
  'JUKI産機テクノロジー株式会社': 'JUKI Industrial Equipment Technology Corp.', 'note株式会社': 'note inc.', 'キャディ株式会社': 'CADDi Inc.',
  'クラスター株式会社': 'Cluster, Inc.', 'ダイニチ工業株式会社': 'Dainichi Co., Ltd.', 'ハコベル株式会社': 'Hacobell Inc.',
  'ファインディ株式会社': 'Findy Inc.', 'メディフォン株式会社': 'MediPhone, Inc.', 'ラクスル株式会社': 'Raksul Inc.',
  'リソルホールディングス株式会社': 'RESOL Holdings Co., Ltd.', '吉田海運株式会社': 'Yoshida Kaiun Co., Ltd.', '坂善商事株式会社': 'Sakazen Shoji Co., Ltd.',
  '大西運輸株式会社': 'Onishi Transport Co., Ltd.', '日本テーマパーク開発株式会社': 'Japan Theme Park Development, Inc.', '株式会社FABRIC TOKYO': 'FABRIC TOKYO Inc.',
  '株式会社FLUX': 'FLUX Inc.', '株式会社iCARE': 'iCARE Co., Ltd.', '株式会社Morght': 'Morght Inc.', '株式会社mov': 'mov inc.',
  '株式会社PIGNUS（ピグナス）': 'PIGNUS Inc.', '株式会社SANU': 'SANU Inc.', '株式会社with': 'with Inc.',
  '株式会社アップガレージグループ': 'UP GARAGE GROUP Co., Ltd.', '株式会社キズキ': 'Kizuki Co., Ltd.', '株式会社キッズコーポレーション': 'Kids Corporation Inc.',
  '株式会社グッドパッチ': 'Goodpatch Inc.', '株式会社ストライダーズ': 'Striders Corporation', '株式会社トーエネック': 'TOENEC Corporation',
  '株式会社ナレッジワーク': 'Knowledge Work Inc.', '株式会社ハッピートラベル': 'Happy Travel Co., Ltd.', '株式会社プレイド': 'PLAID, Inc.',
  '株式会社ベルク': 'Belc CO., LTD.', '株式会社レスタス': 'Lestas Inc.', '株式会社伊豆シャボテン公園': 'Izu Shaboten Resort Co., Ltd.',
  '株式会社寿々': 'Juju Co., Ltd.', '株式会社帝国ホテル': 'Imperial Hotel, Ltd.', '西尾レントオール株式会社': 'Nishio Rent All Co., Ltd.',
}

function officialHost(url?: string) {
  try { return new URL(url || '').hostname.replace(/^www\./, '') } catch { return '' }
}

export function CorpusPage({ settings, onNotify }: { settings: SettingsData | null; onNotify: (message: string, tone: 'success' | 'error') => void }) {
  const { locale, tr, schemaText } = useLocale()
  const [manifest, setManifest] = useState<CorpusManifest | null>(null)
  const [companiesText, setCompaniesText] = useState('3M | https://investors.3m.com/financials/annual-reports-proxy-statements')
  const [years, setYears] = useState<number[]>(availableYears)
  const [job, setJob] = useState<CorpusJob | null>(null)
  const [starting, setStarting] = useState(false)
  const [loadingBakuraku, setLoadingBakuraku] = useState(false)
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
  const [showSearchablePdf, setShowSearchablePdf] = useState(false)
  const displayCurrency = currencyPreference()

  const refresh = () => api.corpus().then(setManifest).catch((error) => onNotify(error instanceof Error ? error.message : tr('Could not load the corpus.', 'コーパスを読み込めませんでした。'), 'error'))
  const restoreLatestJob = () => api.corpusJobs()
    .then(async ({ jobs }) => {
      const ordered = [...jobs].sort((left, right) => Date.parse(right.updated_at || right.created_at || '') - Date.parse(left.updated_at || left.created_at || ''))
      const latest = ordered.find((item) => ['queued', 'running'].includes(item.status)) || ordered[0]
      setJob(latest ? await api.corpusJob(latest.id) : null)
    })
    .catch((error) => onNotify(error instanceof Error ? error.message : tr('Could not restore corpus progress.', 'コーパス進捗を復元できませんでした。'), 'error'))
  const refreshAll = () => Promise.all([refresh(), restoreLatestJob()])
  useEffect(() => {
    void refreshAll()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.corpusJob(job.id)
        setJob(next)
        if (next.status === 'complete') { await refresh(); onNotify(tr('Corpus discovery completed.', 'コーパス探索が完了しました。'), 'success') }
        if (next.status === 'failed' || next.status === 'interrupted') onNotify(next.error || tr('Corpus discovery failed.', 'コーパス探索に失敗しました。'), 'error')
      } catch (error) { onNotify(error instanceof Error ? error.message : tr('Could not read corpus progress.', 'コーパス進捗を取得できませんでした。'), 'error') }
    }, 1500)
    return () => window.clearTimeout(timer)
  }, [job, onNotify]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!pendingDelete) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !deleting) setPendingDelete(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [pendingDelete, deleting])

  const companies = useMemo(() => companiesText.split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const [name, officialUrl = '', country = 'US'] = line.split('|').map((part) => part.trim())
    return { name, official_url: officialUrl, country: country || 'US' }
  }).filter((item) => item.name), [companiesText])

  const loadBakuraku = async () => {
    setLoadingBakuraku(true)
    try {
      const result = await api.bakurakuCustomers()
      const usable = result.customers.filter((item) => item.company_name)
      setCompaniesText(usable.map((item) => `${item.company_name} | ${item.official_website} | JP`).join('\n'))
      onNotify(tr(`Loaded all ${usable.length} verified Bakuraku customers.`, `確認済みバクラク顧客${usable.length}社を読み込みました。`), 'success')
    } catch (error) { onNotify(error instanceof Error ? error.message : tr('Could not load the Bakuraku customer research.', 'バクラク顧客調査を読み込めませんでした。'), 'error') }
    finally { setLoadingBakuraku(false) }
  }

  const start = async () => {
    if (!settings?.has_firecrawl_key) { onNotify(tr('Add your Firecrawl key in Settings first.', '先に設定でFirecrawlキーを追加してください。'), 'error'); return }
    if (!companies.length || !years.length) { onNotify(tr('Add a company and at least one year.', '会社と1つ以上の年度を追加してください。'), 'error'); return }
    setStarting(true)
    try {
      const response = await api.startCorpusJob({ companies, years, deep_search: true })
      setJob({ id: response.job_id, status: 'queued', events: [] })
      onNotify(tr('Corpus discovery is running in the background.', 'コーパス探索をバックグラウンドで実行しています。'), 'success')
    } catch (error) { onNotify(error instanceof Error ? error.message : tr('Could not start corpus discovery.', 'コーパス探索を開始できませんでした。'), 'error') }
    finally { setStarting(false) }
  }

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
    setShowSearchablePdf(false)
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

  const latestEvents = [...(job?.events || [])]
    .sort((left, right) => Date.parse(String(right.at || '')) - Date.parse(String(left.at || '')))
    .slice(0, 8)
    .map((event) => event.type === 'downloaded' && event.company && event.year && !manifest?.documents.some(
      (document) => document.company === event.company && Number(document.fiscal_year) === Number(event.year),
    ) ? { ...event, type: 'invalidated', message: tr('Not retained after source audit', 'ソース監査後に不採用') } : event)
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
      .filter((group) => !needle || `${group.company} ${group.target?.official_url || ''} ${group.documents.map((document) => `${document.filename} ${document.fiscal_year}`).join(' ')}`.toLocaleLowerCase().includes(needle))
      .sort((left, right) => {
        if (left.company.trim().toLocaleLowerCase() === '3m') return -1
        if (right.company.trim().toLocaleLowerCase() === '3m') return 1
        if (Boolean(left.documents.length) !== Boolean(right.documents.length)) return left.documents.length ? -1 : 1
        return left.company.localeCompare(right.company)
      })
  }, [manifest, tableQuery])
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
  const eventLabel = (type: unknown) => {
    const labels: Record<string, string> = {
      discovering: tr('Finding reports', 'レポートを探索'),
      discovered: tr('Reports found', 'レポートを発見'),
      downloaded: tr('Downloaded', 'ダウンロード済み'),
      invalidated: tr('Rejected after audit', '監査後に不採用'),
      failed: tr('Needs attention', '要確認'),
      retry: tr('Retrying', '再試行中'),
    }
    const key = String(type || 'update')
    return labels[key] || tr('Update', '更新')
  }
  const companyLabel = (company: string, officialUrl = '') => {
    if (locale === 'ja' || company.trim().toLocaleLowerCase() === '3m') return company
    return englishCompanyNames[company] || officialHost(officialUrl) || company
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
      <header className="page-header"><div><div className="page-kicker">{tr('Cloud benchmark data', 'クラウドベンチマークデータ')}</div><h1>{tr('Annual Report corpus', '年次報告書コーパス')}</h1><p>{tr('Discover official Annual Reports with Firecrawl, download the PDFs, verify their fiscal year from inside the document, and pin every file by SHA-256.', 'Firecrawlで公式年次報告書を探索し、PDFをダウンロードして文書内の会計年度を検証し、SHA-256で固定します。')}</p></div></header>
      <div className="corpus-summary">
        <Card><span>{tr('Companies', '会社')}</span><strong>{manifest?.summary.companies ?? 0}</strong><small>{tr(`${manifest?.summary.companies_with_reports ?? 0} with stored reports`, `保存済みレポートあり ${manifest?.summary.companies_with_reports ?? 0}社`)}</small></Card>
        <Card><span>{tr('Documents', '文書')}</span><strong>{manifest?.summary.documents ?? 0}</strong><small>FY2020–FY2025</small></Card>
        <Card><span>{tr('Benchmark verified', 'ベンチマーク検証済み')}</span><strong>{manifest?.summary.verified ?? 0}</strong><small>{tr('assignment gold or human approved', '課題正解または人による承認')}</small></Card>
        <Card><span>{tr('Ready for human review', '人による確認待ち')}</span><strong>{manifest?.summary.human_review_required ?? 0}</strong><small>{tr('PDF answers are extracted and prefilled', 'PDF回答を抽出して入力済み')}</small></Card>
      </div>

      <div className="corpus-layout">
        <Card className="corpus-builder">
          <SectionHeading eyebrow={tr('Discovery job', '探索ジョブ')} title={tr('Crawl official report libraries', '公式レポートライブラリをクロール')} description={tr('One company per line: name | official website | country.', '1行に1社：会社名｜公式サイト｜国。')} action={<Button variant="secondary" onClick={loadBakuraku} disabled={loadingBakuraku}><Sparkles size={15} /> {loadingBakuraku ? tr('Loading…', '読込中…') : tr('Load 112 Bakuraku customers', 'バクラク顧客112社を読込')}</Button>} />
          <label className="large-field"><span>{tr('Companies and official websites', '会社と公式サイト')}</span><textarea rows={7} value={companiesText} onChange={(event) => setCompaniesText(event.target.value)} placeholder="3M | https://investors.3m.com/financials/annual-reports-proxy-statements" /></label>
          <div className="year-picker"><span>{tr('Fiscal years', '会計年度')}</span><div>{availableYears.map((year) => <label key={year} className={years.includes(year) ? 'is-selected' : ''}><input type="checkbox" checked={years.includes(year)} onChange={() => setYears((current) => current.includes(year) ? current.filter((item) => item !== year) : [...current, year])} />FY{year}</label>)}</div></div>
          <div className="storage-pattern"><FolderSearch2 size={20} /><div><strong>{tr('Persistent AWS storage', 'AWS永続ストレージ')}</strong><code>corpus_dataset/company/year/company_annual_report_year.pdf</code></div></div>
          <Button className="corpus-start" onClick={start} disabled={starting || job?.status === 'queued' || job?.status === 'running'}>{job?.status === 'running' || job?.status === 'queued' ? <LoaderCircle className="spin" size={16} /> : <Play size={15} fill="currentColor" />} {job?.status === 'running' || job?.status === 'queued' ? tr('Discovery running in background', 'バックグラウンドで探索中') : tr('Discover and download reports', 'レポートを探索してダウンロード')}</Button>
        </Card>

        <Card className="corpus-progress">
          <SectionHeading eyebrow={tr('Background worker', 'バックグラウンドワーカー')} title={tr('Discovery activity', '探索アクティビティ')} description={tr('Firecrawl finds links; the AWS worker downloads and screens each PDF before replacing its canonical company/year file.', 'Firecrawlでリンクを発見し、AWSワーカーがPDFをダウンロード・検査して会社・年度ごとの標準ファイルを置き換えます。')} action={<Button variant="ghost" onClick={() => void refreshAll()}><RefreshCw size={15} /> {tr('Refresh', '更新')}</Button>} />
          {!job ? <EmptyState icon={<FolderSearch2 size={21} />} title={tr('No active discovery', '実行中の探索はありません')} description={tr('Start with one company, verify the result, then scale the company list.', 'まず1社で結果を確認してから会社リストを拡大してください。')} /> : <>
            <div className={`job-status status-${job.status}`}><span>{job.status === 'complete' ? <CheckCircle2 size={18} /> : job.status === 'failed' || job.status === 'interrupted' ? <TriangleAlert size={18} /> : <LoaderCircle className="spin" size={18} />}</span><div><strong>{job.status === 'complete' ? tr('Discovery complete', '探索完了') : job.status === 'failed' || job.status === 'interrupted' ? tr('Discovery stopped', '探索停止') : tr('Working through official sources', '公式ソースを処理中')}</strong><small>{tr('Job', 'ジョブ')} {job.id}{job.updated_at ? ` · ${tr('updated', '更新')} ${new Date(job.updated_at).toLocaleString()}` : ''}</small></div></div>
            <div className="job-events">{latestEvents.map((event, index) => <div key={`${String(event.at)}-${index}`}><span>{eventLabel(event.type)}</span><strong>{[event.company && companyLabel(String(event.company)), event.year && `FY${event.year}`, event.message || event.screened].filter(Boolean).join(' · ')}</strong></div>)}</div>
          </>}
        </Card>
      </div>

      <Card className="corpus-table-card">
        <SectionHeading eyebrow={tr('Pinned manifest', '固定マニフェスト')} title={tr('Annual Report Library', '年次報告書ライブラリ')} description={tr('One row per company across 100 evidence-backed research targets. Expand stored reports by fiscal year; pending targets remain clearly unverified.', '根拠のある調査対象100社を会社ごとに1行表示します。保存済みレポートは年度別に展開でき、未取得対象は未検証として明示されます。')} action={<label className="search-field corpus-table-search"><Search size={15} /><input value={tableQuery} onChange={(event) => setTableQuery(event.target.value)} placeholder={tr('Search companies or years', '会社または年度を検索')} /></label>} />
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
            <td><button className="corpus-company-toggle" type="button" onClick={() => documents.length && toggleCompany(company)} aria-expanded={expanded} disabled={!documents.length}>{documents.length ? expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} /> : <span className="corpus-company-placeholder" />}<span><strong>{companyLabel(company, target?.official_url || documents[0]?.source_url)}</strong>{locale === 'en' && companyLabel(company, target?.official_url || documents[0]?.source_url) !== company && <small>{company}</small>}<small>{documents.length ? `${documents.length} ${tr(documents.length === 1 ? 'fiscal year' : 'fiscal years', '年度')}` : tr('research target', '調査対象')}</small></span></button></td>
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
            <aside className="review-pdf-pane"><div><ScanText size={16} /><strong>{tr('Pinned source PDF', '固定元PDF')}</strong><span className="review-pdf-mode"><button className={!showSearchablePdf ? 'is-active' : ''} type="button" onClick={() => setShowSearchablePdf(false)}><Image size={13} />{tr('A4 page', 'A4ページ')}</button><button className={showSearchablePdf ? 'is-active' : ''} type="button" onClick={() => setShowSearchablePdf(true)}><FileSearch size={13} />{tr('Search PDF', 'PDF検索')}</button></span><small>SHA-256 {reviewing.sha256.slice(0, 12)}…</small></div><p className="pdf-search-hint">{showSearchablePdf ? tr('Searchable full report · click inside, then press ⌘F / Ctrl+F.', '検索可能な全レポート・内部をクリックして⌘F / Ctrl+F。') : tr(`Exact A4 page fit · detected balance sheet${reviewing.balance_sheet_page ? ` p.${reviewing.balance_sheet_page}` : ''}. Switch to Search PDF for full-document search.`, `A4単ページ表示・検出した貸借対照表${reviewing.balance_sheet_page ? ` p.${reviewing.balance_sheet_page}` : ''}。全文検索は「PDF検索」に切り替えてください。`)}</p><div className="review-pdf-frame">{showSearchablePdf ? <iframe src={`${api.corpusPdfUrl(reviewing.sha256)}#page=${reviewing.balance_sheet_page || 1}&zoom=page-width&view=FitH&toolbar=1&navpanes=0`} title={tr('Source annual report PDF', '元の年次報告書PDF')} tabIndex={0} onLoad={(event) => event.currentTarget.focus()} /> : <img src={api.corpusPageImageUrl(reviewing.sha256, reviewing.balance_sheet_page || 1)} alt={tr(`Balance sheet page ${reviewing.balance_sheet_page || 1}`, `貸借対照表ページ${reviewing.balance_sheet_page || 1}`)} />}</div></aside>
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
