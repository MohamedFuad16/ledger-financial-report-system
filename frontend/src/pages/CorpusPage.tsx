import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ExternalLink, FileDown, FolderSearch2, LoaderCircle, Play, RefreshCw, ShieldCheck, Sparkles, Trash2, TriangleAlert, X } from 'lucide-react'
import { api } from '../lib/api'
import type { CorpusDocument, CorpusJob, CorpusManifest, SettingsData } from '../types'
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

  const refresh = () => api.corpus().then(setManifest).catch((error) => onNotify(error instanceof Error ? error.message : tr('Could not load the corpus.', 'コーパスを読み込めませんでした。'), 'error'))
  useEffect(() => { refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.corpusJob(job.id)
        setJob(next)
        if (next.status === 'complete') { await refresh(); onNotify(tr('Corpus discovery completed.', 'コーパス探索が完了しました。'), 'success') }
        if (next.status === 'failed') onNotify(next.error || tr('Corpus discovery failed.', 'コーパス探索に失敗しました。'), 'error')
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

  const latestEvents = (job?.events || []).slice(-8).reverse()
  return (
    <div className="page corpus-page">
      <header className="page-header"><div><div className="page-kicker">{tr('Cloud benchmark data', 'クラウドベンチマークデータ')}</div><h1>{tr('Annual Report corpus', '年次報告書コーパス')}</h1><p>{tr('Discover official Annual Reports with Firecrawl, download the PDFs, verify their fiscal year from inside the document, and pin every file by SHA-256.', 'Firecrawlで公式年次報告書を探索し、PDFをダウンロードして文書内の会計年度を検証し、SHA-256で固定します。')}</p></div></header>
      <div className="corpus-summary">
        <Card><span>{tr('Companies', '会社')}</span><strong>{manifest?.summary.companies ?? 0}</strong><small>{tr('official-source targets', '公式ソース対象')}</small></Card>
        <Card><span>{tr('Documents', '文書')}</span><strong>{manifest?.summary.documents ?? 0}</strong><small>FY2020–FY2025</small></Card>
        <Card><span>{tr('Screened OK', '検査済み')}</span><strong>{manifest?.summary.ok ?? 0}</strong><small>{tr('ready for a benchmark', 'ベンチマーク準備完了')}</small></Card>
        <Card><span>{tr('Needs review', '要確認')}</span><strong>{(manifest?.summary.review ?? 0) + (manifest?.summary.unreadable ?? 0)}</strong><small>{tr('kept, never silently dropped', '削除せず保持')}</small></Card>
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
          <SectionHeading eyebrow={tr('Background worker', 'バックグラウンドワーカー')} title={tr('Discovery activity', '探索アクティビティ')} description={tr('Firecrawl finds links; the AWS worker downloads and screens each PDF before replacing its canonical company/year file.', 'Firecrawlでリンクを発見し、AWSワーカーがPDFをダウンロード・検査して会社・年度ごとの標準ファイルを置き換えます。')} action={<Button variant="ghost" onClick={refresh}><RefreshCw size={15} /> {tr('Refresh', '更新')}</Button>} />
          {!job ? <EmptyState icon={<FolderSearch2 size={21} />} title={tr('No active discovery', '実行中の探索はありません')} description={tr('Start with one company, verify the result, then scale the company list.', 'まず1社で結果を確認してから会社リストを拡大してください。')} /> : <>
            <div className={`job-status status-${job.status}`}><span>{job.status === 'complete' ? <CheckCircle2 size={18} /> : job.status === 'failed' ? <TriangleAlert size={18} /> : <LoaderCircle className="spin" size={18} />}</span><div><strong>{job.status === 'complete' ? tr('Discovery complete', '探索完了') : job.status === 'failed' ? tr('Discovery stopped', '探索停止') : tr('Working through official sources', '公式ソースを処理中')}</strong><small>{tr('Job', 'ジョブ')} {job.id}</small></div></div>
            <div className="job-events">{latestEvents.map((event, index) => <div key={`${String(event.at)}-${index}`}><span>{String(event.type || 'update')}</span><strong>{[event.company, event.year && `FY${event.year}`, event.message || event.screened].filter(Boolean).join(' · ')}</strong></div>)}</div>
          </>}
        </Card>
      </div>

      <Card className="corpus-table-card">
        <SectionHeading eyebrow={tr('Pinned manifest', '固定マニフェスト')} title={tr('Downloaded Annual Reports', 'ダウンロード済み年次報告書')} description={tr('Crawled files do not enter extraction automatically; review the screening verdict first.', 'クロール済みファイルは自動抽出されません。先に検査結果を確認してください。')} />
        {!manifest?.documents.length ? <EmptyState icon={<FileDown size={21} />} title={tr('No corpus documents yet', 'コーパス文書はまだありません')} description={tr('The first verified download will appear here.', '最初の確認済みダウンロードがここに表示されます。')} /> : <div className="table-wrap"><table className="corpus-table"><thead><tr><th>{tr('Company', '会社')}</th><th>{tr('Year', '年度')}</th><th>{tr('Screening', '検査')}</th><th>{tr('PDF health', 'PDF状態')}</th><th>{tr('Source', 'ソース')}</th><th>{tr('Stored PDF', '保存PDF')}</th><th>{tr('Extraction outputs', '抽出出力')}</th><th className="corpus-delete-column">{tr('Delete', '削除')}</th></tr></thead><tbody>{manifest.documents.map((document) => <tr key={document.sha256}><td><strong>{document.company}</strong><small>{document.official_source_verified ? <><ShieldCheck size={12} /> {tr('official domain', '公式ドメイン')}</> : tr('source review required', 'ソース確認が必要')}</small></td><td>FY{document.fiscal_year}</td><td><Badge tone={document.screened === 'ok' ? 'green' : document.screened === 'unreadable' ? 'red' : 'amber'}>{document.screened}</Badge></td><td>{document.readable_pages}/{document.pages} {tr('readable', '読取可')}<small>{document.balance_sheet_page ? `${tr('Balance sheet', '貸借対照表')} p.${document.balance_sheet_page}` : document.screen_reasons?.[0] || tr('No balance-sheet page found', '貸借対照表ページが見つかりません')}</small></td><td><a href={document.source_url} target="_blank" rel="noreferrer">{tr('Open source', 'ソースを開く')} <ExternalLink size={13} /></a></td><td><code>{document.local_path}</code></td><td><code>{document.output_directory}</code><small>{document.output_count || 0} {tr('stored runs', '件の保存済み実行')}</small></td><td className="corpus-delete-column"><button className="corpus-delete-button" type="button" onClick={() => setPendingDelete(document)} aria-label={tr(`Delete ${document.filename}`, `${document.filename}を削除`)}><Trash2 size={15} /><span>{tr('Delete', '削除')}</span></button></td></tr>)}</tbody></table></div>}
      </Card>
      {pendingDelete && <div className="confirm-dialog-backdrop" role="presentation" onMouseDown={() => !deleting && setPendingDelete(null)}>
        <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-report-title" onMouseDown={(event) => event.stopPropagation()}>
          <button className="confirm-dialog-close" type="button" onClick={() => setPendingDelete(null)} disabled={deleting} aria-label={tr('Close dialog', 'ダイアログを閉じる')}><X size={18} /></button>
          <div className="confirm-dialog-icon"><Trash2 size={20} /></div>
          <div className="eyebrow">{tr('Downloaded report', 'ダウンロード済みレポート')}</div>
          <h2 id="delete-report-title">{tr('Delete this annual report?', 'この年次報告書を削除しますか？')}</h2>
          <p>{tr(`${pendingDelete.filename} will be removed from the local corpus and its pinned manifest entry. Existing extraction runs will remain available.`, `${pendingDelete.filename}をローカルコーパスと固定マニフェストから削除します。既存の抽出実行は保持されます。`)}</p>
          <div className="confirm-dialog-actions"><Button variant="ghost" onClick={() => setPendingDelete(null)} disabled={deleting} autoFocus>{tr('Cancel', 'キャンセル')}</Button><Button variant="danger" onClick={confirmDelete} disabled={deleting}><Trash2 size={15} /> {deleting ? tr('Deleting…', '削除中…') : tr('Delete report', 'レポートを削除')}</Button></div>
        </section>
      </div>}
    </div>
  )
}
