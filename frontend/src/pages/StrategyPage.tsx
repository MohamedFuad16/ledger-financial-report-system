import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import {
  Check,
  FileText,
  Info,
  Play,
  RotateCcw,
  Save,
} from 'lucide-react'
import { api, type SseEvent } from '../lib/api'
import type { CorpusDocument, ExecutionFile, RunSummary } from '../types'
import { experimentForStrategyPage, experimentStrategies, extractionJobBelongsToStrategyPage, formatDuration, formatMetric, formatNumber, parserFor, runBelongsToStrategyPage, type StrategyPageKind } from '../lib/format'
import { ExecutionPipeline } from '../components/ExecutionPipeline'
import { FolderUpload } from '../components/FolderUpload'
import { CorpusPicker, type CorpusSelectionMode } from '../components/CorpusPicker'
import { RunTable } from '../components/RunTable'
import { Badge, Button, Card, Disclosure, InlineStatus, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

const parserDescriptions: Record<string, [string, string]> = {
  s1: ['Raw text · OCR off', '生テキスト・OCRオフ'],
  's1-pymupdf': ['Layout Markdown · OCR off', 'レイアウトMarkdown・OCRオフ'],
  's1-inspector': ['Position-aware Rust · OCR off', '位置認識Rust・OCRオフ'],
  's1-docling': ['ML document graph · OCR off', 'ML文書グラフ・OCRオフ'],
  's2-pypdf': ['Raw text + OCR', '生テキスト＋OCR'],
  s2: ['Layout Markdown + OCR', 'レイアウトMarkdown＋OCR'],
  's2-inspector': ['Position-aware Rust + OCR', '位置認識Rust＋OCR'],
  's2-docling': ['ML document graph + OCR', 'ML文書グラフ＋OCR'],
  s3: ['Selective OCR + intelligent page gate', '選択OCR＋インテリジェントページゲート'],
}

export function StrategyPage({
  kind,
  runs,
  onRefreshRuns,
  onNotify,
}: {
  kind: StrategyPageKind
  runs: RunSummary[]
  onRefreshRuns: () => Promise<void>
  onNotify: (message: string, tone: 'success' | 'error') => void
}) {
  const { locale, tr } = useLocale()
  const isStrategy1 = kind === 's1'
  const isStrategy3 = kind === 's3'
  const [files, setFiles] = useState<File[]>([])
  const [inputSource, setInputSource] = useState<'upload' | 'corpus'>('upload')
  const [corpusDocuments, setCorpusDocuments] = useState<CorpusDocument[]>([])
  const [corpusLoading, setCorpusLoading] = useState(false)
  const [corpusLoaded, setCorpusLoaded] = useState(false)
  const [corpusSelectionMode, setCorpusSelectionMode] = useState<CorpusSelectionMode>('single')
  const [selectedCorpusIds, setSelectedCorpusIds] = useState<string[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploadHovering, setUploadHovering] = useState(false)
  // Public strategy numbering matches the stable backend parser keys and job scopes.
  // Strategy 1 is the no-OCR control; Strategy 2 is the OCR-enabled arm.
  const experiment = experimentForStrategyPage(kind)
  const parserChoices = experimentStrategies[experiment]
  const strategyNumber = isStrategy3 ? '03' : isStrategy1 ? '01' : '02'
  const [selectedParsers, setSelectedParsers] = useState<string[]>(parserChoices)
  const [reasoningEnabled, setReasoningEnabled] = useState(true)
  const [prompt, setPrompt] = useState('')
  const [defaultPrompt, setDefaultPrompt] = useState('')
  const [promptSaving, setPromptSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [executions, setExecutions] = useState<ExecutionFile[]>([])
  const storageKey = `ledger-active-extraction-${kind}`
  const [activeJobId, setActiveJobId] = useState<string | null>(() => window.localStorage.getItem(storageKey))
  const eventOffset = useRef(0)

  useEffect(() => {
    setSelectedParsers(parserChoices)
  }, [kind]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    api.prompt().then((data) => { setPrompt(data.system_prompt); setDefaultPrompt(data.default_prompt) }).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (inputSource !== 'corpus' || corpusLoaded || corpusLoading) return
    setCorpusLoading(true)
    api.corpus()
      .then((manifest) => setCorpusDocuments(manifest.documents))
      .catch((error) => onNotify(error instanceof Error ? error.message : tr('Could not load stored reports.', '保存済みレポートを読み込めませんでした。'), 'error'))
      .finally(() => { setCorpusLoading(false); setCorpusLoaded(true) })
  }, [inputSource, corpusLoaded, corpusLoading, onNotify, tr])

  const strategyRuns = useMemo(() => runs.filter((run) => runBelongsToStrategyPage(run, kind)), [runs, kind])
  const acceptFiles = (incoming: File[]) => {
    const pdfs = incoming.filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length !== incoming.length) onNotify(tr('Only PDF files can be staged.', '追加できるのはPDFファイルのみです。'), 'error')
    setFiles(pdfs)
    setExecutions([])
  }

  const savePrompt = async () => {
    setPromptSaving(true)
    try {
      await api.savePrompt(prompt)
      onNotify(tr('System prompt saved.', 'システムプロンプトを保存しました。'), 'success')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('Could not save the prompt.', 'プロンプトを保存できませんでした。'), 'error')
    } finally {
      setPromptSaving(false)
    }
  }

  const resetPrompt = async () => {
    try {
      const data = await api.resetPrompt()
      setPrompt(data.system_prompt || defaultPrompt)
      onNotify(tr('Default prompt restored.', '既定のプロンプトに戻しました。'), 'success')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('Could not reset the prompt.', 'プロンプトをリセットできませんでした。'), 'error')
    }
  }

  const updatePass = (index: number, strategy: string, update: Partial<ExecutionFile['passes'][number]>) => {
    setExecutions((current) => current.map((file, fileIndex) => fileIndex !== index ? file : {
      ...file,
      state: update.state === 'failed' ? 'failed' : update.state === 'running' ? 'running' : file.state,
      passes: file.passes.map((pass) => pass.strategy === strategy ? { ...pass, ...update } : pass),
    }))
  }

  const updateStep = (
    index: number,
    strategy: string,
    step: string,
    state: 'queued' | 'running' | 'complete' | 'failed',
    message?: string,
    durationSeconds?: number,
    startedAt?: string,
  ) => {
    setExecutions((current) => current.map((file, fileIndex) => fileIndex !== index ? file : {
      ...file,
      state: state === 'failed' ? 'failed' : state === 'running' ? 'running' : file.state,
      passes: file.passes.map((pass) => pass.strategy !== strategy ? pass : {
        ...pass,
        state: state === 'failed' ? 'failed' : state === 'running' ? 'running' : pass.state,
        step,
        message,
        steps: {
          ...pass.steps,
          [step]: { state, message, durationSeconds, startedAt: pass.steps?.[step]?.startedAt || startedAt },
        },
      }),
    }))
  }

  const progressMessage = (data: Record<string, any>) => {
    if (locale === 'en') return data.message
    const parser = parserFor(data.strategy).short
    if (data.step === 'upload') return 'レポートを保存しました'
    if (data.step === 'extract') return data.done
      ? data.selected_page_count
        ? `${formatNumber(data.page_count)}ページを検査・${formatNumber(data.selected_page_count)}ページを選択`
        : `${formatNumber(data.page_count)}ページを解析完了`
      : `${parser}で文書を解析中`
    if (data.step === 'prompt') return data.done
      ? '入力プロンプトを作成しました'
      : '27行のスキーマプロンプトを作成中'
    if (data.step === 'api') return data.throttled
      ? 'レート制限のため待機後に再試行します'
      : data.done ? 'モデルの応答を受信しました' : 'モデルの応答を待っています'
    if (data.step === 'validate') return data.done ? '出力契約の検証完了' : '出力契約を検証中'
    if (data.step === 'output') return '実行結果を保存しました'
    return data.message
  }

  const handleEvent = (message: SseEvent) => {
    const data = message.data as Record<string, any>
    if (message.event === 'batch_start') {
      setExecutions((data.files || []).map((file: any) => ({
        name: file.name,
        pages: file.pages,
        approxTokens: file.approx_tokens,
        state: 'queued',
        passes: (data.strategies || []).map((strategy: any) => ({ strategy: strategy.key, strategyLabel: strategy.label, state: 'queued' })),
      })))
    }
    if (message.event === 'pass_start') {
      updatePass(data.index, data.strategy, { state: 'running', startedAt: message.at, message: tr(`Preparing ${parserFor(data.strategy).short}`, `${parserFor(data.strategy).short}を準備中`) })
    }
    if (message.event === 'progress') {
      updateStep(
        data.index,
        data.strategy,
        data.step,
        data.done ? 'complete' : 'running',
        progressMessage(data),
        data.duration_seconds,
        message.at,
      )
    }
    if (message.event === 'file_done') {
      setExecutions((current) => current.map((file, fileIndex) => fileIndex !== data.index ? file : {
        ...file,
        state: data.ok ? file.state : 'failed',
        passes: file.passes.map((pass) => {
          if (pass.strategy !== data.strategy) return pass
          const failedStep = data.step || pass.step || 'api'
          return {
            ...pass,
            state: data.ok ? 'complete' : 'failed',
            step: data.ok ? 'output' : failedStep,
            message: data.ok ? `${formatMetric(data.metrics?.accuracy)} ${tr('accuracy', '正確率')} · ${formatDuration(data.total_seconds)}` : data.error,
            runId: data.run_id,
            metrics: data.metrics,
            totalSeconds: data.total_seconds,
            extractSeconds: data.extract_seconds,
            apiSeconds: data.api_elapsed_seconds,
            fiscalYear: data.fiscal_year,
            error: data.error,
            steps: data.ok ? pass.steps : {
              ...pass.steps,
              [failedStep]: { state: 'failed' as const, message: data.error },
            },
          }
        }),
      }))
    }
    if (message.event === 'file_complete') {
      setExecutions((current) => current.map((file, index) => index !== data.index ? file : {
        ...file,
        state: file.passes.some((pass) => pass.state === 'failed') ? 'failed' : 'complete',
      }))
    }
  }

  useEffect(() => {
    if (activeJobId) return
    api.extractionJobs().then(({ jobs }) => {
      const resumable = jobs.find((job) => job.scope === kind && (job.status === 'queued' || job.status === 'running'))
      if (resumable) {
        window.localStorage.setItem(storageKey, resumable.id)
        setActiveJobId(resumable.id)
      }
    }).catch(() => undefined)
  }, [activeJobId, kind, storageKey])

  useEffect(() => {
    if (!activeJobId) return
    let cancelled = false
    let timer = 0
    let finished = false
    eventOffset.current = 0
    setExecutions([])
    setRunning(true)

    const poll = async () => {
      try {
        const job = await api.extractionJob(activeJobId, eventOffset.current)
        if (cancelled) return
        if (!extractionJobBelongsToStrategyPage(job.scope, kind)) {
          window.localStorage.removeItem(storageKey)
          setActiveJobId(null)
          setRunning(false)
          return
        }
        job.events.forEach((record) => handleEvent({ event: record.event, data: record.data, at: record.at }))
        eventOffset.current = job.next_offset
        if ((job.status === 'complete' || job.status === 'failed' || job.status === 'interrupted') && !finished) {
          finished = true
          setRunning(false)
          await onRefreshRuns()
          window.localStorage.removeItem(storageKey)
          setActiveJobId(null)
          if (job.status === 'failed' || job.status === 'interrupted') {
            onNotify(job.error || tr('The extraction could not be completed.', '抽出を完了できませんでした。'), 'error')
          } else {
            onNotify(tr(`${job.succeeded} extraction pass${job.succeeded === 1 ? '' : 'es'} completed.`, `${job.succeeded}件の抽出処理が完了しました。`), 'success')
          }
          return
        }
        timer = window.setTimeout(poll, 800)
      } catch (error) {
        if (cancelled) return
        setRunning(false)
        window.localStorage.removeItem(storageKey)
        setActiveJobId(null)
        onNotify(error instanceof Error ? error.message : tr('Could not resume the extraction job.', '抽出ジョブを再開できませんでした。'), 'error')
      }
    }
    void poll()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  // Replaying the persisted event log intentionally rebuilds page-local presentation state.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeJobId, storageKey])

  const startRun = async () => {
    const readyCount = inputSource === 'upload' ? files.length : selectedCorpusIds.length
    if (!readyCount || running) return
    if (!selectedParsers.length) {
      onNotify(tr('Select at least one parser for the bake-off.', '比較するパーサーを1つ以上選択してください。'), 'error')
      return
    }
    setRunning(true)
    // Show the pipeline instantly: seed one queued card per selected report so
    // the click lands in Live execution with no dead gap while staging runs.
    const optimisticNames = inputSource === 'upload'
      ? files.map((file) => file.name)
      : selectedCorpusIds.map((id) => corpusDocuments.find((document) => document.sha256 === id)?.filename || id)
    setExecutions(optimisticNames.map((name) => ({
      name,
      state: 'queued' as const,
      passes: selectedParsers.map((key) => ({ strategy: key, strategyLabel: parserFor(key).label, state: 'queued' as const })),
    })))
    try {
      const staged = inputSource === 'upload'
        ? await api.stageUploads(files)
        : await api.stageCorpusDocuments(selectedCorpusIds)
      const usable = staged.files.filter((file) => file.id && !file.error)
      if (!usable.length) throw new Error(staged.files[0]?.error || tr('No readable PDF could be staged.', '読み取り可能なPDFを追加できませんでした。'))
      const advisories = [...(staged.advisories || []), ...(staged.plan.advisories || [])]
      if (advisories.length) onNotify(advisories.join(' '), 'error')
      const job = await api.startExtractionJob({
        upload_ids: usable.map((file) => file.id),
        strategies: selectedParsers,
        system_prompt: prompt,
        reasoning_effort: reasoningEnabled ? 'high' : 'none',
        enable_reasoning: reasoningEnabled,
      })
      window.localStorage.setItem(storageKey, job.job_id)
      setActiveJobId(job.job_id)
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('The extraction could not be completed.', '抽出を完了できませんでした。'), 'error')
      setExecutions([])
      setRunning(false)
    }
  }

  const completedComparison = executions
    .flatMap((file) => file.passes.map((pass) => ({ file: file.name, pages: file.pages, approxTokens: file.approxTokens, ...pass })))
    .filter((pass) => pass.state === 'complete')
  const expectedStrategies = executions[0]?.passes.map((pass) => pass.strategy) || []
  const matchedExecutions = executions.filter((file) => expectedStrategies.length > 0 && expectedStrategies.every((strategy) =>
    file.passes.some((pass) => pass.strategy === strategy && pass.state === 'complete'),
  ))
  const matchedComparison = matchedExecutions.flatMap((file) => file.passes.map((pass) => ({ file: file.name, pages: file.pages, approxTokens: file.approxTokens, ...pass })))
  const comparisonSummary = Object.values(matchedComparison.reduce<Record<string, {
    strategy: string
    passes: typeof matchedComparison
  }>>((groups, pass) => {
    const group = groups[pass.strategy] || { strategy: pass.strategy, passes: [] }
    group.passes.push(pass)
    groups[pass.strategy] = group
    return groups
  }, {})).map((group) => {
    const average = (values: Array<number | null | undefined>) => {
      const numeric = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
      return numeric.length ? numeric.reduce((total, value) => total + value, 0) / numeric.length : null
    }
    return {
      strategy: group.strategy,
      count: group.passes.length,
      scheduled: executions.length,
      successful: executions.filter((file) => file.passes.some((pass) => pass.strategy === group.strategy && pass.state === 'complete')).length,
      failed: executions.filter((file) => file.passes.some((pass) => pass.strategy === group.strategy && pass.state === 'failed')).length,
      accuracy: average(group.passes.map((pass) => pass.metrics?.accuracy)),
      coverage: average(group.passes.map((pass) => pass.metrics?.coverage)),
      totalSeconds: average(group.passes.map((pass) => pass.totalSeconds)),
    }
  })
  const selectedInputCount = inputSource === 'upload' ? files.length : selectedCorpusIds.length

  return (
    <div className="page strategy-page">
      <header className="page-header">
        <div>
          <Badge tone={isStrategy3 ? 'amber' : isStrategy1 ? 'blue' : 'green'}>{tr('Strategy', '戦略')} {strategyNumber} · {tr('Active', '有効')}</Badge>
          <h1>{isStrategy3 ? tr('Intelligent scanning gate', 'インテリジェントスキャニングゲート') : isStrategy1 ? tr('No-OCR parser control', 'OCRなしパーサー対照実験') : tr('OCR-enabled parser bake-off', 'OCR有効パーサーベイクオフ')}</h1>
          <p>{isStrategy3 ? tr('Use pdf-inspector as the finalized parser, replace only OCR-routed pages, then rank complete unified-Markdown pages and send the top three to five to the model.', 'pdf-inspectorを最終パーサーとして使用し、OCR対象ページだけを置換した後、統合Markdownの完全なページを順位付けし、上位3〜5ページだけをモデルに送ります。') : isStrategy1 ? tr('Compare the same four parsers with OCR disabled while holding the PDF, model, prompt, and output contract constant.', 'PDF・モデル・プロンプト・出力契約を固定し、同じ4つのパーサーをOCRなしで比較します。') : tr('Compare the same four parsers with OCR enabled: adaptive where page detection exists, otherwise compulsory.', '同じ4つのパーサーをOCR有効で比較します。ページ判定がある場合は適応型、ない場合はOCRを必須化します。')}</p>
        </div>
      </header>

      <div className="hypothesis-banner">
        <div className="hypothesis-number">H{isStrategy3 ? '3' : isStrategy1 ? '1' : '2'}</div>
        <div><span>{tr('Experiment hypothesis', '実験仮説')}</span><strong>{isStrategy3 ? tr('Parser-guided OCR plus deterministic page scoring should preserve the evidence required by the 27-row schema while sharply reducing LLM input.', 'パーサー誘導OCRと決定論的ページスコアリングにより、27行スキーマに必要な根拠を維持しながらLLM入力を大幅に削減できるはずです。') : isStrategy1 ? tr('With OCR disabled, parser representation alone explains differences in extraction accuracy and speed.', 'OCRを無効にすると、パーサー表現そのものが抽出精度と速度の差を説明できるはずです。') : tr('OCR-enabled passes should recover damaged or image-only pages; adaptive parsers OCR only classified pages, while the remaining parsers use compulsory OCR.', 'OCR有効パスは破損したテキスト層や画像ページを復元します。適応型パーサーは判定されたページだけをOCRし、その他はOCRを必須化します。')}</strong></div>
      </div>

      <div className="strategy-prompt-row">
        <Disclosure title={tr('System prompt', 'システムプロンプト')} subtitle={tr('Shared across all active strategies', 'すべての有効な戦略で共有')}>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={12} />
          <div className="prompt-actions"><Button variant="ghost" onClick={resetPrompt}><RotateCcw size={14} /> {tr('Reset', 'リセット')}</Button><Button variant="secondary" onClick={savePrompt} disabled={promptSaving}><Save size={14} /> {promptSaving ? tr('Saving', '保存中') : tr('Save prompt', 'プロンプトを保存')}</Button></div>
        </Disclosure>
      </div>

      <div className="strategy-workspace">
        <div className="strategy-controls">
          <Card>
            <SectionHeading eyebrow={tr('Input', '入力')} title={tr('Annual Report PDF', '年次報告書PDF')} description={isStrategy3 ? tr('Run the finalized pdf-inspector and intelligent-gate pipeline on one report or a batch.', '最終版pdf-inspector＋インテリジェントゲートを1件または一括レポートで実行します。') : isStrategy1 ? tr('Use one report for a clean parser comparison, or stage a batch.', '1つのレポートでパーサーを比較するか、複数ファイルを一括追加します。') : tr('Stage one report or a multi-year batch.', '1つのレポートまたは複数年度をまとめて追加します。')} action={<div className="segmented-control input-source-toggle"><button className={inputSource === 'upload' ? 'is-active' : ''} onClick={() => setInputSource('upload')}>{tr('Upload', 'アップロード')}</button><button className={inputSource === 'corpus' ? 'is-active' : ''} onClick={() => setInputSource('corpus')}>{tr('Corpus', 'コーパス')}</button></div>} />
            {inputSource === 'upload' ? <><div
              className={`upload-zone ${dragging ? 'is-dragging' : ''}`}
              onMouseEnter={() => setUploadHovering(true)}
              onMouseLeave={() => setUploadHovering(false)}
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFiles(Array.from(event.dataTransfer.files)) }}
            >
              <input type="file" accept="application/pdf,.pdf" multiple onChange={(event) => acceptFiles(Array.from(event.target.files || []))} aria-label={tr('Choose Annual Report PDFs', '年次報告書PDFを選択')} />
              <FolderUpload active={uploadHovering || dragging} open={dragging} tone={kind === 's1' ? 'blue' : kind === 's2' ? 'red' : 'violet'} />
              <strong>{files.length ? tr(`${files.length} PDF${files.length === 1 ? '' : 's'} ready`, `${files.length}件のPDFを準備済み`) : tr('Drop Annual Reports here', '年次報告書をここにドロップ')}</strong>
              <p>{files.length ? files.map((file) => file.name).join(' · ') : tr('or click to browse from this computer', 'またはクリックして端末から選択')}</p>
            </div>
            {!!files.length && <div className="selected-files">{files.map((file) => <div key={`${file.name}-${file.size}`}><FileText size={15} /><span><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(1)} MB</small></span><Check size={15} strokeWidth={3} /></div>)}</div>}</> : corpusLoading ? <div className="corpus-picker-loading"><span className="button-spinner" /> {tr('Loading stored reports…', '保存済みレポートを読み込み中…')}</div> : <CorpusPicker documents={corpusDocuments} selected={selectedCorpusIds} mode={corpusSelectionMode} onModeChange={setCorpusSelectionMode} onSelectionChange={setSelectedCorpusIds} />}

            <div className="parser-picker">
                <div className="field-label"><span>{tr('Parser passes', 'パーサー処理')}</span><small>{tr(`${selectedParsers.length} model call${selectedParsers.length === 1 ? '' : 's'} per PDF`, `PDFごとに${selectedParsers.length}回のモデル呼び出し`)}</small></div>
                {parserChoices.map((key) => {
                  const meta = parserFor(key)
                  const selected = selectedParsers.includes(key)
                  const description = parserDescriptions[key] || [meta.label, meta.label]
                  return <label className={`parser-option ${selected ? 'is-selected' : ''}`} style={{ '--parser-color': meta.color } as CSSProperties} key={key}><input type="checkbox" checked={selected} onChange={() => setSelectedParsers((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key])} /><i /><span><strong>{meta.short}</strong><small>{tr(description[0], description[1])}</small></span><span className="check-box"><Check size={12} strokeWidth={3} /></span></label>
                })}
              </div>

            <div className="control-grid strategy-run-options">
              <div className="reasoning-toggle"><span><strong>{tr('Model reasoning', 'モデル推論')}</strong><small>{tr('Mapped to the model’s native thinking on/off control.', 'モデル固有の思考オン／オフに対応します。')}</small></span><div><button className={!reasoningEnabled ? 'is-active' : ''} onClick={() => setReasoningEnabled(false)}>{tr('Off', 'オフ')}</button><button className={reasoningEnabled ? 'is-active' : ''} onClick={() => setReasoningEnabled(true)}>{tr('On', 'オン')}</button></div></div>
            </div>

            <Button className="run-button" onClick={startRun} disabled={!selectedInputCount || running}>
              {running ? <><span className="button-spinner" /> {tr('Running extraction', '抽出を実行中')}</> : <><Play size={15} fill="currentColor" /> {tr(`Run ${selectedParsers.length || ''} parser pass${selectedParsers.length === 1 ? '' : 'es'}`, `${selectedParsers.length || ''}件のパーサー処理を実行`)}</>}
            </Button>
            <div className="run-footnote"><Info size={13} /> {inputSource === 'corpus' ? tr('Stored corpus PDFs stay in their company/year folders. Extraction starts only after this button is pressed.', '保存済みPDFは会社・年度別フォルダーに保持され、このボタンを押した後にのみ抽出を開始します。') : tr('PDFs are staged locally. A model call starts only after this button is pressed.', 'PDFはローカルに準備され、このボタンを押した後にのみモデルを呼び出します。')}</div>
          </Card>

        </div>

        <Card className="pipeline-card">
          <SectionHeading eyebrow={tr('Live execution', 'ライブ実行')} title={tr('Execution pipeline', '実行パイプライン')} description={tr('One live card per report follows the active parser and extraction stage.', 'レポートごとのライブカードで、実行中のパーサーと抽出ステージを追跡します。')} action={<InlineStatus status={running ? 'loading' : executions.length ? 'success' : 'neutral'}>{running ? tr('Running', '実行中') : executions.length ? tr('Complete', '完了') : tr('Idle', '待機')}</InlineStatus>} />
          <ExecutionPipeline files={executions} running={running} />
        </Card>
      </div>

      {completedComparison.length > 0 && !isStrategy3 && (
        <Card className="comparison-card">
          <SectionHeading eyebrow={isStrategy3 ? tr('Selected-page results', '選択ページ結果') : tr('Controlled comparison', '統制比較')} title={isStrategy3 ? tr('Intelligent gate extraction results', 'インテリジェントゲート抽出結果') : tr('Extraction technology bake-off', '抽出技術ベイクオフ')} description={isStrategy3 ? tr('Each result records OCR routing, selected pages, score components, input reduction, model output and deterministic validation.', '各結果にOCRルーティング、選択ページ、スコア内訳、入力削減、モデル出力、決定論的検証を記録します。') : tr('Batch averages compare each parser across the same reports. Per-report results remain available below.', '同じレポート群に対するパーサーごとの平均を比較し、各レポートの結果も下に保持します。')} />
          <div className="comparison-cohort-note">
            <strong>{tr(`${matchedExecutions.length} of ${executions.length} reports in the matched cohort`, `${executions.length}件中${matchedExecutions.length}件が比較対象`)}</strong>
            <span>{isStrategy3 ? tr('Every completed report used the same locked pdf-inspector → selective OCR → intelligent gate → semantic mapping contract.', '完了したすべてのレポートは、固定されたpdf-inspector→選択OCR→インテリジェントゲート→セマンティックマッピング契約を使用します。') : tr('A report enters the cumulative average only after every selected parser completes it, preventing partial-success bias.', '選択したすべてのパーサーが完了したレポートだけを累積平均に含め、部分成功による偏りを防ぎます。')}</span>
          </div>
          {comparisonSummary.length > 0 && <div className="comparison-grid">{comparisonSummary.map((summary) => { const meta = parserFor(summary.strategy); return <article key={summary.strategy}><i style={{ background: meta.color }} /><span>{meta.short}<small>{tr(`Matched average of ${summary.count} report${summary.count === 1 ? '' : 's'}`, `${summary.count}件の対応平均`)}</small></span><strong>{formatMetric(summary.accuracy)}</strong><small>{formatMetric(summary.coverage)} {tr('coverage', 'カバレッジ')} · {formatDuration(summary.totalSeconds)} {tr('average', '平均')}</small><small>{tr(`${summary.successful}/${summary.scheduled} successful · ${summary.failed} failed`, `成功 ${summary.successful}/${summary.scheduled} · 失敗 ${summary.failed}`)}</small></article> })}</div>}
          <div className="comparison-detail-wrap">
            <table className="comparison-detail-table">
              <thead><tr><th>{tr('Report', 'レポート')}</th><th>{tr('Parser / mode', 'パーサー／モード')}</th><th>{tr('Exact accuracy', '完全一致率')}</th><th>{tr('Field coverage', 'フィールドカバレッジ')}</th><th>{tr('Pages', 'ページ')}</th><th>{tr('Estimated tokens', '推定トークン')}</th><th>{tr('Parse time', '解析時間')}</th><th>{tr('Model time', 'モデル時間')}</th><th>{tr('Total time', '合計時間')}</th></tr></thead>
              <tbody>{completedComparison.map((pass) => <tr key={`${pass.file}-${pass.strategy}`}><td><strong>{pass.file}</strong></td><td>{parserFor(pass.strategy).label}</td><td>{formatMetric(pass.metrics?.accuracy)}</td><td>{formatMetric(pass.metrics?.coverage)}</td><td>{formatNumber(pass.pages)}</td><td>{formatNumber(pass.approxTokens)}</td><td>{formatDuration(pass.extractSeconds)}</td><td>{formatDuration(pass.apiSeconds)}</td><td><strong>{formatDuration(pass.totalSeconds)}</strong></td></tr>)}</tbody>
            </table>
          </div>
        </Card>
      )}

      <Card className="previous-runs-card">
        <SectionHeading eyebrow={tr('History', '履歴')} title={tr(`Previous Strategy ${isStrategy3 ? '3' : isStrategy1 ? '1' : '2'} runs`, `戦略${isStrategy3 ? '3' : isStrategy1 ? '1' : '2'}の過去実行`)} description={tr(`${strategyRuns.length} stored experiment records.`, `${strategyRuns.length}件の実験記録を保存。`)} />
        <RunTable runs={strategyRuns.slice(0, 8)} />
      </Card>
    </div>
  )
}
