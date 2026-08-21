import { AnimatePresence, motion } from 'framer-motion'
import { Check, FileText, LoaderCircle, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ExecutionFile, ExecutionPass } from '../types'
import { formatDuration, formatNumber, parserFor } from '../lib/format'
import { useLocale } from '../lib/i18n'

/* One compact card follows each report through every parser and stage.
   The underlying passes remain independent; only their live presentation is folded. */

const stepOrder = ['upload', 'extract', 'prompt', 'api', 'validate', 'output'] as const
type Step = typeof stepOrder[number]
type StepState = 'queued' | 'running' | 'complete' | 'failed'

function activePassFor(file: ExecutionFile) {
  const running = file.passes.find((pass) => pass.state === 'running')
  if (running) return running
  if (file.state === 'failed') return file.passes.find((pass) => pass.state === 'failed') || file.passes.at(-1)
  if (file.state === 'complete') return file.passes.at(-1)
  return file.passes.find((pass) => pass.state === 'queued') || file.passes.at(-1)
}

function stateForStep(pass: ExecutionPass, step: Step): StepState {
  if (pass.steps?.[step]) return pass.steps[step].state
  const stepIndex = stepOrder.indexOf(step)
  const activeIndex = stepOrder.indexOf((pass.step || '') as Step)
  if (pass.state === 'complete') return 'complete'
  if (pass.state === 'failed' && stepIndex === activeIndex) return 'failed'
  if (activeIndex >= 0 && stepIndex < activeIndex) return 'complete'
  if (pass.state === 'running' && (stepIndex === activeIndex || activeIndex < 0 && step === 'upload')) return 'running'
  return 'queued'
}

export function ExecutionPipeline({ files, running }: { files: ExecutionFile[]; running: boolean }) {
  const { tr } = useLocale()
  const [now, setNow] = useState(Date.now())
  const startedAt = useRef<Record<string, number>>({})
  const labels: Record<Step, string> = {
    upload: tr('Save report', 'レポートを保存'),
    extract: tr('Parse document', '文書を解析'),
    prompt: tr('Build prompt', 'プロンプトを作成'),
    api: tr('Run model', 'モデルを実行'),
    validate: tr('Validate output', '出力を検証'),
    output: tr('Save result', '結果を保存'),
  }

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(timer)
  }, [running])

  if (!files.length) {
    return (
      <div className="pipeline-empty">
        <span className="pipeline-empty-icon"><FileText size={22} /></span>
        <strong>{tr('No execution in progress', '実行中の処理はありません')}</strong>
        <p>{tr('Stage an Annual Report to watch its parser and extraction stage update live.', '年次報告書を追加すると、パーサーと抽出ステージの進行をリアルタイムで確認できます。')}</p>
      </div>
    )
  }

  const timeLabel = (key: string, pass: ExecutionPass, step: Step, state: StepState) => {
    const stored = pass.steps?.[step]?.durationSeconds
    if (stored != null) return formatDuration(stored)
    if (state !== 'running') return state === 'complete' ? tr('Done', '完了') : state === 'failed' ? tr('Stopped', '停止') : tr('Waiting', '待機')
    if (!startedAt.current[key]) startedAt.current[key] = Date.now()
    return formatDuration((now - startedAt.current[key]) / 1000)
  }

  return (
    <div className="execution-file-list">
      <AnimatePresence initial={false}>
        {files.map((file) => {
          const activePass = activePassFor(file)
          if (!activePass) return null
          const passIndex = Math.max(0, file.passes.indexOf(activePass))
          const parser = parserFor(activePass.strategy)
          const step = (activePass.step && stepOrder.includes(activePass.step as Step)
            ? activePass.step
            : activePass.state === 'complete' ? 'output' : 'upload') as Step
          const stepState = stateForStep(activePass, step)
          const statusLabel = file.state === 'complete'
            ? tr('Completed', '完了')
            : file.state === 'failed'
              ? tr('Failed', '失敗')
              : activePass.state === 'queued'
                ? tr('Queued', '待機中')
                : tr('Running', '実行中')
          const message = activePass.steps?.[step]?.message
            || activePass.message
            || (stepState === 'running'
              ? tr('Working…', '処理中…')
              : stepState === 'failed'
                ? tr('This parser pass needs attention', 'このパーサー処理を確認してください')
                : stepState === 'complete'
                  ? tr('Parser comparison complete', 'パーサー比較が完了しました')
                  : passIndex > 0
                    ? tr('Waiting for the previous parser', '前のパーサーを待機中')
                    : tr('Ready to start', '開始待ち'))
          const completedPasses = file.passes.filter((pass) => pass.state === 'complete').length
          const timerKey = `${file.name}-${activePass.strategy}-${step}`

          return (
            <motion.section
              className={`execution-file-card execution-file-card-${file.state}`}
              data-testid="execution-file-card"
              key={file.name}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <div className="execution-primary-row">
                <span className="file-avatar"><FileText size={15} /></span>
                <div className="execution-file-copy">
                  <strong>{file.name}</strong>
                  <span>{formatNumber(file.pages)} {tr('pages', 'ページ')} · {formatNumber(file.approxTokens)} {tr('estimated tokens', '推定トークン')}</span>
                </div>
                <AnimatePresence mode="wait" initial={false}>
                  <motion.div
                    className="execution-live-inline"
                    key={`${activePass.strategy}-${step}-${stepState}`}
                    initial={{ opacity: 0, y: 7 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -7 }}
                    transition={{ duration: .22 }}
                  >
                    <span className={`execution-state-icon execution-state-${stepState}`}>
                      {stepState === 'complete' ? <Check size={16} strokeWidth={2.6} /> : stepState === 'failed' ? <X size={16} strokeWidth={2.6} /> : stepState === 'running' ? <LoaderCircle className="spin" size={18} strokeWidth={2.2} /> : <b>{String(passIndex + 1).padStart(2, '0')}</b>}
                    </span>
                    <div className="execution-live-copy">
                      <div className="execution-parser-line"><i style={{ background: parser.color }} /><strong>{parser.short}</strong><span>{labels[step]}</span></div>
                      <p className={stepState === 'running' ? 'execution-shimmer-text' : ''}>{message}</p>
                    </div>
                    <time>{timeLabel(timerKey, activePass, step, stepState)}</time>
                  </motion.div>
                </AnimatePresence>
                <span className={`execution-status execution-status-${file.state}`}>{statusLabel}</span>
              </div>

              {file.passes.length > 1 && <div className="execution-pass-rail" aria-label={tr('Parser comparison progress', 'パーサー比較の進捗')}>
                {file.passes.map((pass, index) => {
                  const meta = parserFor(pass.strategy)
                  const isActive = pass === activePass
                  return (
                    <span className={`execution-pass-chip is-${pass.state}${isActive ? ' is-active' : ''}`} key={`${file.name}-${pass.strategy}`}>
                      <i style={{ background: meta.color }} />
                      <span>{meta.short}</span>
                      {pass.state === 'complete' ? <Check size={12} strokeWidth={2.8} /> : pass.state === 'failed' ? <X size={12} strokeWidth={2.8} /> : pass.state === 'running' ? <LoaderCircle className="spin" size={12} /> : <b>{index + 1}</b>}
                    </span>
                  )
                })}
                <small>{tr(`${completedPasses} of ${file.passes.length} parsers complete`, `${file.passes.length}件中${completedPasses}件のパーサーが完了`)}</small>
              </div>}
            </motion.section>
          )
        })}
      </AnimatePresence>
      <span className="sr-only" aria-live="polite">{running ? tr('Live execution events are streaming', '実行イベントをリアルタイムで受信中') : ''}</span>
    </div>
  )
}
