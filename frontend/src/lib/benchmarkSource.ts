import type { RunSummary } from '../types'

// Which model's runs the public dashboard aggregates. Selected in Settings,
// persisted per browser; Gemini 3.7 Flash (the medium-effort benchmark) is
// the default view.
export type BenchmarkSource = 'gemini' | 'glm-thinking' | 'glm-non-thinking'

const STORAGE_KEY = 'ledger-benchmark-source'

export const benchmarkSourceMeta: Record<BenchmarkSource, { label: string; labelJa: string }> = {
  gemini: { label: 'Gemini 3.7 Flash', labelJa: 'Gemini 3.7 Flash' },
  'glm-thinking': { label: 'GLM-5.3 (thinking)', labelJa: 'GLM-5.3（思考モード）' },
  'glm-non-thinking': { label: 'GLM-5.3 (no thinking)', labelJa: 'GLM-5.3（思考なし）' },
}

export function benchmarkSource(): BenchmarkSource {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'gemini' || stored === 'glm-thinking' || stored === 'glm-non-thinking') return stored
  } catch {
    /* storage unavailable: fall through to the default */
  }
  return 'gemini'
}

export function saveBenchmarkSource(source: BenchmarkSource) {
  try {
    localStorage.setItem(STORAGE_KEY, source)
  } catch {
    /* storage unavailable: selection lives only for this page view */
  }
}

export function runMatchesSource(run: RunSummary, source: BenchmarkSource): boolean {
  const model = String(run.model || '').toLowerCase()
  if (source === 'gemini') {
    if (!model.includes('gemini')) return false
    // The published Gemini benchmark: medium-effort Strategy 2/3 plus the
    // low-effort Strategy 1 control (the control is reasoning-insensitive and
    // the low run covers it), never both efforts of one arm at once.
    const effort = String(run.reasoning_effort || '')
    return run.experiment === 'no_ocr' ? effort === 'low' : effort === 'medium'
  }
  if (!model.includes('glm')) return false
  const thinking = run.enable_reasoning !== false
  return source === 'glm-thinking' ? thinking : !thinking
}
