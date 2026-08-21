import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import {
  Check,
  FileText,
  Info,
  Play,
  RotateCcw,
  Save,
} from 'lucide-react'
import { api, runStagedExtraction, type SseEvent } from '../lib/api'
import type { CorpusDocument, ExecutionFile, RunDetail, RunSummary } from '../types'
import { formatDuration, formatMetric, formatMoney, formatNumber, parserFor, parserMeta } from '../lib/format'
import { ExecutionPipeline } from '../components/ExecutionPipeline'
import { FolderUpload } from '../components/FolderUpload'
import { CorpusPicker, type CorpusSelectionMode } from '../components/CorpusPicker'
import { RunTable } from '../components/RunTable'
import { Badge, Button, Card, Disclosure, InlineStatus, SectionHeading } from '../components/ui'
import { useLocale } from '../lib/i18n'

const allS2Parsers = ['s1', 's2', 's2-inspector', 's2-docling']

export function StrategyPage({
  kind,
  runs,
  onRefreshRuns,
  onNotify,
}: {
  kind: 's1' | 's2'
  runs: RunSummary[]
  onRefreshRuns: () => Promise<void>
  onNotify: (message: string, tone: 'success' | 'error') => void
}) {
  const { locale, tr, schemaText } = useLocale()
  const isS2 = kind === 's2'
  const [files, setFiles] = useState<File[]>([])
  const [inputSource, setInputSource] = useState<'upload' | 'corpus'>('upload')
  const [corpusDocuments, setCorpusDocuments] = useState<CorpusDocument[]>([])
  const [corpusLoading, setCorpusLoading] = useState(false)
  const [corpusLoaded, setCorpusLoaded] = useState(false)
  const [corpusSelectionMode, setCorpusSelectionMode] = useState<CorpusSelectionMode>('single')
  const [selectedCorpusIds, setSelectedCorpusIds] = useState<string[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploadHovering, setUploadHovering] = useState(false)
  const [selectedParsers, setSelectedParsers] = useState<string[]>(isS2 ? ['s1', 's2', 's2-inspector'] : ['s1'])
  const [reasoningEnabled, setReasoningEnabled] = useState(true)
  const [prompt, setPrompt] = useState('')
  const [defaultPrompt, setDefaultPrompt] = useState('')
  const [promptSaving, setPromptSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [executions, setExecutions] = useState<ExecutionFile[]>([])
  const [latestDetail, setLatestDetail] = useState<RunDetail | null>(null)
  const successfulRunIds = useRef<string[]>([])

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

  const strategyRuns = useMemo(() => runs.filter((run) => isS2 ? run.strategy.startsWith('s2') : run.strategy === 's1'), [runs, isS2])
  const acceptFiles = (incoming: File[]) => {
    const pdfs = incoming.filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length !== incoming.length) onNotify(tr('Only PDF files can be staged.', '追加できるのはPDFファイルのみです。'), 'error')
    setFiles(pdfs)
    setExecutions([])
    setLatestDetail(null)
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
          [step]: { state, message, durationSeconds },
        },
      }),
    }))
  }

  const progressMessage = (data: Record<string, any>) => {
    if (locale === 'en') return data.message
    const parser = parserFor(data.strategy).short
    if (data.step === 'upload') return 'レポートを保存しました'
    if (data.step === 'extract') return data.done
      ? `${formatNumber(data.page_count)}ページを解析完了`
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
      updatePass(data.index, data.strategy, { state: 'running', message: tr(`Preparing ${parserFor(data.strategy).short}`, `${parserFor(data.strategy).short}を準備中`) })
    }
    if (message.event === 'progress') {
      updateStep(
        data.index,
        data.strategy,
        data.step,
        data.done ? 'complete' : 'running',
        progressMessage(data),
        data.duration_seconds,
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
            error: data.error,
            steps: data.ok ? pass.steps : {
              ...pass.steps,
              [failedStep]: { state: 'failed' as const, message: data.error },
            },
          }
        }),
      }))
      if (data.ok && data.run_id) successfulRunIds.current.push(data.run_id)
    }
    if (message.event === 'file_complete') {
      setExecutions((current) => current.map((file, index) => index !== data.index ? file : {
        ...file,
        state: file.passes.some((pass) => pass.state === 'failed') ? 'failed' : 'complete',
      }))
    }
  }

  const startRun = async () => {
    const readyCount = inputSource === 'upload' ? files.length : selectedCorpusIds.length
    if (!readyCount || running) return
    if (isS2 && !selectedParsers.length) {
      onNotify(tr('Select at least one parser for the bake-off.', '比較するパーサーを1つ以上選択してください。'), 'error')
      return
    }
    setRunning(true)
    setLatestDetail(null)
    successfulRunIds.current = []
    try {
      const staged = inputSource === 'upload'
        ? await api.stageUploads(files)
        : await api.stageCorpusDocuments(selectedCorpusIds)
      const usable = staged.files.filter((file) => file.id && !file.error)
      if (!usable.length) throw new Error(staged.files[0]?.error || tr('No readable PDF could be staged.', '読み取り可能なPDFを追加できませんでした。'))
      await runStagedExtraction({
        upload_ids: usable.map((file) => file.id),
        strategies: isS2 ? selectedParsers : ['s1'],
        system_prompt: prompt,
        reasoning_effort: reasoningEnabled ? 'high' : 'none',
        enable_reasoning: reasoningEnabled,
      }, handleEvent)
      await onRefreshRuns()
      const latestId = successfulRunIds.current.at(-1)
      if (latestId) setLatestDetail(await api.run(latestId))
      onNotify(tr(`${successfulRunIds.current.length} extraction pass${successfulRunIds.current.length === 1 ? '' : 'es'} completed.`, `${successfulRunIds.current.length}件の抽出処理が完了しました。`), 'success')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : tr('The extraction could not be completed.', '抽出を完了できませんでした。'), 'error')
    } finally {
      setRunning(false)
    }
  }

  const comparison = executions.flatMap((file) => file.passes.map((pass) => ({ file: file.name, ...pass }))).filter((pass) => pass.state === 'complete')
  const selectedInputCount = inputSource === 'upload' ? files.length : selectedCorpusIds.length

  return (
    <div className="page strategy-page">
      <header className="page-header">
        <div>
          <Badge tone={isS2 ? 'blue' : 'green'}>{tr('Strategy', '戦略')} {isS2 ? '02' : '01'} · {tr('Active', '有効')}</Badge>
          <h1>{isS2 ? tr('Document representation bake-off', '文書表現ベイクオフ') : tr('Direct LLM baseline', 'LLM直接抽出ベースライン')}</h1>
          <p>{isS2 ? tr('Hold the prompt and model constant while comparing how each parser represents the same Annual Report.', '同じ年次報告書に対してプロンプトとモデルを固定し、パーサーごとの文書表現を比較します。') : tr('The control condition: basic page-by-page text, one model call, and the shared 27-row contract.', 'ページ単位の基本テキスト、1回のモデル呼び出し、共通の27行契約を使う対照条件です。')}</p>
        </div>
      </header>

      <div className="hypothesis-banner">
        <div className="hypothesis-number">H{isS2 ? '2' : '1'}</div>
        <div><span>{tr('Experiment hypothesis', '実験仮説')}</span><strong>{isS2 ? tr('Layout-aware structure should preserve tables and provenance without distorting the accounting taxonomy.', 'レイアウトを考慮した構造は、会計分類を歪めずに表と出典を保持できるはずです。') : tr('A long-context model can recover the full asset taxonomy directly from ordinary extracted text.', '長文脈モデルは通常の抽出テキストから資産分類全体を直接復元できるはずです。')}</strong></div>
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
            <SectionHeading eyebrow={tr('Input', '入力')} title={tr('Annual Report PDF', '年次報告書PDF')} description={isS2 ? tr('Use one report for a clean parser comparison, or stage a batch.', '1つのレポートでパーサーを比較するか、複数ファイルを一括追加します。') : tr('Stage one report or a multi-year batch.', '1つのレポートまたは複数年度をまとめて追加します。')} action={<div className="segmented-control input-source-toggle"><button className={inputSource === 'upload' ? 'is-active' : ''} onClick={() => setInputSource('upload')}>{tr('Upload', 'アップロード')}</button><button className={inputSource === 'corpus' ? 'is-active' : ''} onClick={() => setInputSource('corpus')}>{tr('Corpus', 'コーパス')}</button></div>} />
            {inputSource === 'upload' ? <><div
              className={`upload-zone ${dragging ? 'is-dragging' : ''}`}
              onMouseEnter={() => setUploadHovering(true)}
              onMouseLeave={() => setUploadHovering(false)}
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFiles(Array.from(event.dataTransfer.files)) }}
            >
              <input type="file" accept="application/pdf,.pdf" multiple onChange={(event) => acceptFiles(Array.from(event.target.files || []))} aria-label={tr('Choose Annual Report PDFs', '年次報告書PDFを選択')} />
              <FolderUpload active={uploadHovering || dragging} open={dragging} />
              <strong>{files.length ? tr(`${files.length} PDF${files.length === 1 ? '' : 's'} ready`, `${files.length}件のPDFを準備済み`) : tr('Drop Annual Reports here', '年次報告書をここにドロップ')}</strong>
              <p>{files.length ? files.map((file) => file.name).join(' · ') : tr('or click to browse from this computer', 'またはクリックして端末から選択')}</p>
            </div>
            {!!files.length && <div className="selected-files">{files.map((file) => <div key={`${file.name}-${file.size}`}><FileText size={15} /><span><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(1)} MB</small></span><Check size={15} strokeWidth={3} /></div>)}</div>}</> : corpusLoading ? <div className="corpus-picker-loading"><span className="button-spinner" /> {tr('Loading stored reports…', '保存済みレポートを読み込み中…')}</div> : <CorpusPicker documents={corpusDocuments} selected={selectedCorpusIds} mode={corpusSelectionMode} onModeChange={setCorpusSelectionMode} onSelectionChange={setSelectedCorpusIds} />}

            {isS2 && (
              <div className="parser-picker">
                <div className="field-label"><span>{tr('Parser passes', 'パーサー処理')}</span><small>{tr(`${selectedParsers.length} model call${selectedParsers.length === 1 ? '' : 's'} per PDF`, `PDFごとに${selectedParsers.length}回のモデル呼び出し`)}</small></div>
                {allS2Parsers.map((key) => {
                  const meta = parserFor(key)
                  const selected = selectedParsers.includes(key)
                  return <label className={`parser-option ${selected ? 'is-selected' : ''}`} style={{ '--parser-color': meta.color } as CSSProperties} key={key}><input type="checkbox" checked={selected} onChange={() => setSelectedParsers((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key])} /><i /><span><strong>{meta.short}</strong><small>{key === 's1' ? tr('Raw baseline', '生テキスト基準') : key === 's2' ? tr('Layout Markdown', 'レイアウトMarkdown') : key === 's2-inspector' ? tr('Position-aware Rust', '位置認識Rust') : tr('ML document graph', 'ML文書グラフ')}</small></span><span className="check-box"><Check size={12} strokeWidth={3} /></span></label>
                })}
              </div>
            )}

            <div className="control-grid strategy-run-options">
              <div className="reasoning-toggle"><span><strong>{tr('Model reasoning', 'モデル推論')}</strong><small>{tr('Mapped to the model’s native thinking on/off control.', 'モデル固有の思考オン／オフに対応します。')}</small></span><div><button className={!reasoningEnabled ? 'is-active' : ''} onClick={() => setReasoningEnabled(false)}>{tr('Off', 'オフ')}</button><button className={reasoningEnabled ? 'is-active' : ''} onClick={() => setReasoningEnabled(true)}>{tr('On', 'オン')}</button></div></div>
            </div>

            <Button className="run-button" onClick={startRun} disabled={!selectedInputCount || running}>
              {running ? <><span className="button-spinner" /> {tr('Running extraction', '抽出を実行中')}</> : <><Play size={15} fill="currentColor" /> {isS2 ? tr(`Run ${selectedParsers.length || ''} parser pass${selectedParsers.length === 1 ? '' : 'es'}`, `${selectedParsers.length || ''}件のパーサー処理を実行`) : selectedInputCount > 1 ? tr(`Run ${selectedInputCount}-report batch`, `${selectedInputCount}件のレポートを一括実行`) : tr('Run baseline extraction', 'ベースライン抽出を実行')}</>}
            </Button>
            <div className="run-footnote"><Info size={13} /> {inputSource === 'corpus' ? tr('Stored corpus PDFs stay in their company/year folders. Extraction starts only after this button is pressed.', '保存済みPDFは会社・年度別フォルダーに保持され、このボタンを押した後にのみ抽出を開始します。') : tr('PDFs are staged locally. A model call starts only after this button is pressed.', 'PDFはローカルに準備され、このボタンを押した後にのみモデルを呼び出します。')}</div>
          </Card>

        </div>

        <Card className="pipeline-card">
          <SectionHeading eyebrow={tr('Live execution', 'ライブ実行')} title={tr('Execution pipeline', '実行パイプライン')} description={tr('One live card per report follows the active parser and extraction stage.', 'レポートごとのライブカードで、実行中のパーサーと抽出ステージを追跡します。')} action={<InlineStatus status={running ? 'loading' : executions.length ? 'success' : 'neutral'}>{running ? tr('Running', '実行中') : executions.length ? tr('Complete', '完了') : tr('Idle', '待機')}</InlineStatus>} />
          <ExecutionPipeline files={executions} running={running} />
        </Card>
      </div>

      {isS2 && comparison.length > 0 && (
        <Card className="comparison-card">
          <SectionHeading eyebrow={tr('Controlled comparison', '統制比較')} title={tr('Extraction technology bake-off', '抽出技術ベイクオフ')} description={tr('Same PDF, schema, model, and prompt; only the parser differs.', 'PDF、スキーマ、モデル、プロンプトを固定し、パーサーだけを変えます。')} />
          <div className="comparison-grid">{comparison.map((pass) => { const meta = parserFor(pass.strategy); return <article key={`${pass.file}-${pass.strategy}`}><i style={{ background: meta.color }} /><span>{meta.short}</span><strong>{formatMetric(pass.metrics?.accuracy)}</strong><small>{formatMetric(pass.metrics?.coverage)} {tr('coverage', 'カバレッジ')}</small></article> })}</div>
        </Card>
      )}

      {latestDetail && (
        <Card className="inline-results">
          <SectionHeading eyebrow={tr('Latest completed output', '最新の完了出力')} title={tr(`FY${latestDetail.fiscal_year} extracted asset-side balance sheet`, `FY${latestDetail.fiscal_year} 抽出済み資産側貸借対照表`)} description={`${parserFor(latestDetail.strategy).label} · ${latestDetail.run_id}`} action={<div className="result-badges"><Badge tone="green">{formatMetric(latestDetail.metrics.accuracy)} {tr('accuracy', '正確度')}</Badge><Badge>{formatMetric(latestDetail.metrics.coverage)} {tr('coverage', 'カバレッジ')}</Badge></div>} />
          <div className="result-table-wrap"><table className="result-table result-schema-table"><thead><tr><th>{tr('Classification', '分類')}</th><th>{tr('Subclassification', '小分類')}</th><th>{tr('Item', '項目')}</th><th>{tr('Answer (M USD)', '回答（百万USD）')}</th></tr></thead><tbody>{latestDetail.rows.map((row) => <tr className={!row.accepted ? 'is-rejected' : ''} key={row.item}><td>{schemaText(row.classification) || '—'}</td><td>{schemaText(row.subclassification) || '—'}</td><td><strong>{schemaText(row.item)}</strong></td><td className="numeric"><strong>{row.accepted ? formatMoney(row.answer_m_usd) : '—'}</strong></td></tr>)}</tbody></table></div>
        </Card>
      )}

      <Card className="previous-runs-card">
        <SectionHeading eyebrow={tr('History', '履歴')} title={tr(`Previous Strategy ${isS2 ? '2' : '1'} runs`, `戦略${isS2 ? '2' : '1'}の過去実行`)} description={tr(`${strategyRuns.length} stored experiment records.`, `${strategyRuns.length}件の実験記録を保存。`)} />
        <RunTable runs={strategyRuns.slice(0, 8)} compact />
      </Card>
    </div>
  )
}
