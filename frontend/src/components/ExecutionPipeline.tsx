import { AnimatePresence, motion } from 'framer-motion'
import { Check, FileText, LoaderCircle, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ExecutionFile, ExecutionPass } from '../types'
import { formatDuration, formatNumber, parserFor } from '../lib/format'
import { useLocale } from '../lib/i18n'

/* Visual behavior adapted from Beautiful UI's Task Rows primitive (MIT).
   Status and timing come from Ledger's real extraction SSE stream. */

const stepOrder = ['upload', 'extract', 'prompt', 'api', 'validate', 'output'] as const
type StepState = 'queued' | 'running' | 'complete' | 'failed'

export function ExecutionPipeline({ files, running }: { files: ExecutionFile[]; running: boolean }) {
  const { tr } = useLocale()
  const [now, setNow] = useState(Date.now())
  const startedAt = useRef<Record<string, number>>({})
  const labels: Record<string, string> = {
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
        <p>{tr('Stage an Annual Report to watch each parser task move from document text to verified output.', '年次報告書を追加すると、文書解析から検証済み出力までの各タスクを確認できます。')}</p>
      </div>
    )
  }

  const derivedState = (pass: ExecutionPass, step: string): StepState => {
    if (pass.steps?.[step]) return pass.steps[step].state
    const stepIndex = stepOrder.indexOf(step as typeof stepOrder[number])
    const activeIndex = stepOrder.indexOf((pass.step || '') as typeof stepOrder[number])
    if (pass.state === 'complete') return 'complete'
    if (pass.state === 'failed' && stepIndex === activeIndex) return 'failed'
    if (activeIndex >= 0 && stepIndex < activeIndex) return 'complete'
    if (pass.state === 'running' && stepIndex === activeIndex) return 'running'
    return 'queued'
  }

  const timeLabel = (key: string, pass: ExecutionPass, step: string, state: StepState) => {
    const stored = pass.steps?.[step]?.durationSeconds
    if (stored != null) return formatDuration(stored)
    if (state !== 'running') return state === 'complete' ? tr('Done', '完了') : tr('Waiting', '待機')
    if (!startedAt.current[key]) startedAt.current[key] = Date.now()
    return formatDuration((now - startedAt.current[key]) / 1000)
  }

  return (
    <div className="task-pipeline-list">
      <AnimatePresence initial={false}>
        {files.map((file) => (
          <motion.section className="task-file-group" key={file.name} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <header className="task-file-head">
              <span className="file-avatar"><FileText size={15} /></span>
              <div><strong>{file.name}</strong><span>{formatNumber(file.pages)} {tr('pages', 'ページ')} · {formatNumber(file.approxTokens)} {tr('estimated tokens', '推定トークン')}</span></div>
            </header>
            <div className="task-rows">
              {file.passes.map((pass, passIndex) => {
                const parser = parserFor(pass.strategy)
                const statusLabel = pass.state === 'complete' ? tr('Completed', '完了') : pass.state === 'failed' ? tr('Failed', '失敗') : pass.state === 'running' ? tr('Running', '実行中') : tr('Queued', '待機中')
                return (
                  <motion.section className={`task-pass task-pass-${pass.state}`} key={`${file.name}-${pass.strategy}`} layout>
                    <header className="task-pass-head">
                      <span className="task-pass-index">{String(passIndex + 1).padStart(2, '0')}</span>
                      <i style={{ background: parser.color }} />
                      <div><strong>{parser.short}</strong><span>{pass.message || statusLabel}</span></div>
                      <span className={`task-status-pill task-status-${pass.state}`}>{statusLabel}</span>
                    </header>
                    <motion.div className="task-capsule-list" initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: .045 } } }}>
                      {stepOrder.map((step) => {
                        const state = derivedState(pass, step)
                        const key = `${file.name}-${pass.strategy}-${step}`
                        const message = pass.steps?.[step]?.message
                        return (
                          <motion.article className={`task-capsule task-capsule-${state}`} key={step} variants={{ hidden: { opacity: 0, y: 5 }, visible: { opacity: 1, y: 0 } }} layout>
                            <span className="task-capsule-icon">{state === 'complete' ? <Check size={14} strokeWidth={3} /> : state === 'failed' ? <X size={14} strokeWidth={2.7} /> : state === 'running' ? <LoaderCircle className="spin" size={16} strokeWidth={2.4} /> : null}</span>
                            <div>
                              <strong>{labels[step]}</strong>
                              <AnimatePresence mode="wait" initial={false}>
                                <motion.small key={message || state} initial={{ opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -3 }}>
                                  {message || (state === 'running' ? tr('Working…', '処理中…') : state === 'failed' ? tr('Needs attention', '要確認') : state === 'complete' ? tr('Complete', '完了') : tr('Waiting for previous task', '前のタスクを待機中'))}
                                </motion.small>
                              </AnimatePresence>
                            </div>
                            <time>{timeLabel(key, pass, step, state)}</time>
                          </motion.article>
                        )
                      })}
                    </motion.div>
                  </motion.section>
                )
              })}
            </div>
          </motion.section>
        ))}
      </AnimatePresence>
      {running && <div className="pipeline-live-caption"><LoaderCircle className="spin" size={14} /> {tr('Live execution events are streaming', '実行イベントをリアルタイムで受信中')}</div>}
    </div>
  )
}
