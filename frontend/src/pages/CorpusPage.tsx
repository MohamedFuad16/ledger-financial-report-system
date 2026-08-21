import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ClipboardCheck, ExternalLink, FileDown, FolderSearch2, LoaderCircle, Play, RefreshCw, Save, ScanText, ShieldCheck, Sparkles, Trash2, TriangleAlert, X } from 'lucide-react'
import { api } from '../lib/api'
import type { CorpusDocument, CorpusJob, CorpusManifest, CorpusVerification, CorpusVerificationRow, SettingsData } from '../types'
import { Badge, Button, Card, EmptyState, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

const availableYears = [2020, 2021, 2022, 2023, 2024, 2025]

export function CorpusPage({ settings, onNotify }: { settings: SettingsData | null; onNotify: (message: string, tone: 'success' | 'error') => void }) {
  const { tr } = useLocale()
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

  const refresh = () => api.corpus().then(setManifest).catch((error) => onNotify(error instanceof Error ? error.message : tr('Could not load the corpus.', 'コーパスを読み込めませんでした。'), 'error'))
  const restoreLatestJob = () => api.corpusJobs()
    .then(async ({ jobs }) => {
      const latest = jobs.find((item) => ['queued', 'running'].includes(item.status)) || jobs[0]
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
      const response = await api.startCorpusJob({ companies, years })
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
    setReviewing(document)
    void loadReview(document)
  }

  const updateReviewAnswer = (index: number, value: string) => {
    setReviewRows((current) => current.map((row, rowIndex) => rowIndex === index
      ? { ...row, answer_m_usd: value.trim() === '' ? null : Number(value) }
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

  const latestEvents = (job?.events || []).slice(-8).reverse()
  return (
    <div className="page corpus-page">
      <header className="page-header"><div><div className="page-kicker">{tr('Cloud benchmark data', 'クラウドベンチマークデータ')}</div><h1>{tr('Annual Report corpus', '年次報告書コーパス')}</h1><p>{tr('Discover official Annual Reports with Firecrawl, download the PDFs, verify their fiscal year from inside the document, and pin every file by SHA-256.', 'Firecrawlで公式年次報告書を探索し、PDFをダウンロードして文書内の会計年度を検証し、SHA-256で固定します。')}</p></div></header>
      <div className="corpus-summary">
        <Card><span>{tr('Companies', '会社')}</span><strong>{manifest?.summary.companies ?? 0}</strong><small>{tr('official-source targets', '公式ソース対象')}</small></Card>
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
            <div className={`job-status status-${job.status}`}><span>{job.status === 'complete' ? <CheckCircle2 size={18} /> : job.status === 'failed' || job.status === 'interrupted' ? <TriangleAlert size={18} /> : <LoaderCircle className="spin" size={18} />}</span><div><strong>{job.status === 'complete' ? tr('Discovery complete', '探索完了') : job.status === 'failed' || job.status === 'interrupted' ? tr('Discovery stopped', '探索停止') : tr('Working through official sources', '公式ソースを処理中')}</strong><small>{tr('Job', 'ジョブ')} {job.id}</small></div></div>
            <div className="job-events">{latestEvents.map((event, index) => <div key={`${String(event.at)}-${index}`}><span>{String(event.type || 'update')}</span><strong>{[event.company, event.year && `FY${event.year}`, event.message || event.screened].filter(Boolean).join(' · ')}</strong></div>)}</div>
          </>}
        </Card>
      </div>

      <Card className="corpus-table-card">
        <SectionHeading eyebrow={tr('Pinned manifest', '固定マニフェスト')} title={tr('Downloaded Annual Reports', 'ダウンロード済み年次報告書')} description={tr('Crawled files do not enter extraction automatically; review the screening verdict first.', 'クロール済みファイルは自動抽出されません。先に検査結果を確認してください。')} />
        {!manifest?.documents.length ? <EmptyState icon={<FileDown size={21} />} title={tr('No corpus documents yet', 'コーパス文書はまだありません')} description={tr('The first verified download will appear here.', '最初の確認済みダウンロードがここに表示されます。')} /> : <div className="table-wrap"><table className="corpus-table"><thead><tr>
          <th>{tr('Company', '会社')}</th><th>{tr('Year', '年度')}</th><th>{tr('Screening', '検査')}</th><th>{tr('Answer verification', '回答検証')}</th><th>{tr('PDF health', 'PDF状態')}</th><th>{tr('Source', 'ソース')}</th><th>{tr('Stored PDF', '保存PDF')}</th><th>{tr('Extraction outputs', '抽出出力')}</th><th className="corpus-delete-column">{tr('Delete', '削除')}</th>
        </tr></thead><tbody>{manifest.documents.map((document) => <tr key={document.sha256}>
          <td><strong>{document.company}</strong><small>{document.official_source_verified ? <><ShieldCheck size={12} /> {tr('official domain', '公式ドメイン')}</> : tr('source review required', 'ソース確認が必要')}</small></td>
          <td>FY{document.fiscal_year}</td>
          <td><Badge tone={document.screened === 'ok' ? 'green' : document.screened === 'unreadable' ? 'red' : 'amber'}>{document.screened}</Badge></td>
          <td><div className="corpus-verification-cell"><Badge tone={document.verification_status === 'human_review_required' ? 'amber' : 'green'}>{document.verification_status === 'assignment_supplied' ? tr('Assignment gold', '課題正解') : document.verification_status === 'human_verified' ? tr('Human verified', '人による確認済み') : document.candidate_extracted ? tr('Extracted · review required', '抽出済み・確認待ち') : tr('Extraction required', '抽出が必要')}</Badge><button className="corpus-review-button" type="button" onClick={() => openReview(document)}><ClipboardCheck size={14} /> {document.verification_status === 'human_verified' || document.verification_status === 'assignment_supplied' ? tr('View reviewed answers', '確認済み回答を表示') : tr('Review extracted answers', '抽出済み回答を確認')}</button></div></td>
          <td>{document.readable_pages}/{document.pages} {tr('readable', '読取可')}<small>{document.balance_sheet_page ? `${tr('Balance sheet', '貸借対照表')} p.${document.balance_sheet_page}` : document.screen_reasons?.[0] || tr('No balance-sheet page found', '貸借対照表ページが見つかりません')}</small></td>
          <td><a href={document.source_url} target="_blank" rel="noreferrer">{tr('Open source', 'ソースを開く')} <ExternalLink size={13} /></a></td>
          <td><code>{document.local_path}</code></td>
          <td><code>{document.output_directory}</code><small>{document.output_count || 0} {tr('stored runs', '件の保存済み実行')}</small></td>
          <td className="corpus-delete-column"><button className="corpus-delete-button" type="button" onClick={() => setPendingDelete(document)} aria-label={tr(`Delete ${document.filename}`, `${document.filename}を削除`)}><Trash2 size={15} /><span>{tr('Delete', '削除')}</span></button></td>
        </tr>)}</tbody></table></div>}
      </Card>
      {reviewing && <div className="review-sheet-backdrop" role="presentation">
        <section className="review-sheet" role="dialog" aria-modal="true" aria-labelledby="review-sheet-title">
          <header><div><div className="eyebrow">{tr('Extracted-answer review', '抽出済み回答の確認')}</div><h2 id="review-sheet-title">{reviewing.company} · FY{reviewing.fiscal_year}</h2><p>{tr('Ledger extracts and pre-fills all 27 rows from the pinned PDF first. Compare the values with the PDF, correct any mistakes, then save and approve the reviewed table.', 'Ledgerが固定PDFから27項目を先に抽出して入力します。PDFと照合し、誤りを修正してから確認表を保存・承認してください。')}</p></div><button type="button" onClick={() => { setReviewing(null); setConfirmApprove(false); setReviewError(null) }} aria-label={tr('Close review', 'レビューを閉じる')}><X size={18} /></button></header>
          <div className="review-sheet-actions"><a className="button secondary" href={api.corpusPdfUrl(reviewing.sha256)} target="_blank" rel="noreferrer"><ExternalLink size={15} /> {tr('Open PDF in new tab', 'PDFを新しいタブで開く')}</a>{reviewPhase === 'extracting' ? <Badge tone="blue">{tr('Extracting from PDF…', 'PDFから抽出中…')}</Badge> : verification && <Badge tone={verification.status === 'human_review_required' ? 'amber' : 'green'}>{verification.status === 'assignment_supplied' ? tr('Assignment supplied', '課題提供') : verification.status === 'human_verified' ? tr('Human verified', '人による確認済み') : tr('Extracted · approval required', '抽出済み・承認待ち')}</Badge>}{verification?.candidate_extracted && <span className="candidate-row-summary">{tr(`27 rows extracted · ${reviewRows.filter((row) => row.answer_m_usd !== null).length} values found`, `27項目を抽出・${reviewRows.filter((row) => row.answer_m_usd !== null).length}件の値を検出`)}</span>}{verification?.consensus_summary && <span className="candidate-consensus-summary">{tr(`${verification.consensus_summary.successful_passes}/${verification.consensus_summary.requested_passes} extraction passes · ${verification.consensus_summary.exact_agreement_rows + verification.consensus_summary.stable_rows}/27 stable rows`, `抽出 ${verification.consensus_summary.successful_passes}/${verification.consensus_summary.requested_passes}回 · 安定行 ${verification.consensus_summary.exact_agreement_rows + verification.consensus_summary.stable_rows}/27`)}</span>}</div>
          <div className="review-workspace">
            <aside className="review-pdf-pane"><div><ScanText size={16} /><strong>{tr('Pinned source PDF', '固定元PDF')}</strong><small>SHA-256 {reviewing.sha256.slice(0, 12)}…</small></div><object data={api.corpusPdfUrl(reviewing.sha256)} type="application/pdf" aria-label={tr('Source annual report PDF', '元の年次報告書PDF')}><a href={api.corpusPdfUrl(reviewing.sha256)} target="_blank" rel="noreferrer">{tr('Open the source PDF', '元PDFを開く')}</a></object></aside>
            <div className="review-answer-pane">
              {reviewPhase !== 'idle' ? <div className="review-sheet-loading" role="status"><LoaderCircle className="spin" size={22} /><strong>{reviewPhase === 'extracting' ? tr('Extracting and prefilling 27 answers from the PDF…', 'PDFから27項目を抽出して入力しています…') : tr('Loading the extracted answer sheet…', '抽出済み回答表を読み込んでいます…')}</strong><span>{reviewPhase === 'extracting' && tr('This may take a minute. No manual entry is required.', '1分ほどかかる場合があります。手入力は不要です。')}</span></div> : reviewError ? <div className="review-extraction-error"><TriangleAlert size={24} /><strong>{tr('PDF extraction did not complete', 'PDF抽出が完了しませんでした')}</strong><p>{reviewError}</p><Button variant="secondary" onClick={() => void loadReview(reviewing)}><RefreshCw size={15} /> {tr('Retry PDF extraction', 'PDF抽出を再試行')}</Button></div> : <><div className="review-prefill-note"><ScanText size={17} /><div><strong>{tr('Extracted prefill — verify, then correct', '抽出済み入力 — 照合して修正')}</strong><span>{tr('These values came from the PDF. Edit only the rows that do not match the source, then approve the full table.', 'これらの値はPDFから抽出されています。元資料と一致しない行のみ修正し、表全体を承認してください。')}</span></div></div><div className="review-table-wrap"><table className="review-table"><thead><tr><th>#</th><th>{tr('Classification', '分類')}</th><th>{tr('Item', '項目')}</th><th>{tr('Extracted answer (M USD)', '抽出回答（百万USD）')}</th><th>{tr('Agreement', '一致度')}</th><th>{tr('Page', 'ページ')}</th><th>{tr('Extracted evidence', '抽出根拠')}</th></tr></thead><tbody>{reviewRows.map((row, index) => <tr key={row.item}><td>{String(index + 1).padStart(2, '0')}</td><td>{row.classification}<small>{row.subclassification || '—'}</small></td><td><strong>{row.item}</strong></td><td><input type="number" step="any" value={row.answer_m_usd ?? ''} disabled={verification?.status === 'assignment_supplied'} onChange={(event) => updateReviewAnswer(index, event.target.value)} aria-label={`${row.item} answer`} /></td><td>{row.agreement_count !== undefined ? <Badge tone={row.stability === 'disagreement' || row.stability === 'missing' ? 'amber' : 'green'}>{row.agreement_count}/{verification?.consensus_summary?.requested_passes ?? row.successful_passes ?? 1}</Badge> : '—'}</td><td>{row.source_page ?? '—'}</td><td>{row.evidence || '—'}</td></tr>)}</tbody></table></div></>}
            </div>
          </div>
          <footer><span>{tr('Extracted answers are provisional, never automatic gold. Approval confirms that you checked the complete table against this exact PDF.', '抽出回答は暫定値であり、自動的な正解データにはなりません。承認すると、このPDFと表全体を照合済みであることを確認します。')}</span>{verification?.status !== 'assignment_supplied' && <Button onClick={() => setConfirmApprove(true)} disabled={reviewPhase !== 'idle' || Boolean(reviewError) || !verification?.candidate_extracted || savingReview}><Save size={15} /> {verification?.status === 'human_verified' ? tr('Save updated approval', '更新した承認を保存') : tr('Save & approve reviewed answers', '確認済み回答を保存・承認')}</Button>}</footer>
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
