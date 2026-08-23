import type {
  ProviderInfo,
  CorpusJob,
  CorpusManifest,
  CorpusVerification,
  ExtractionJob,
  RunDetail,
  RunSummary,
  SchemaRow,
  SettingsData,
  StagedFile,
} from '../types'

const API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')
const apiUrl = (path: string) => `${API_BASE_URL}${path}`
const WORKSPACE_KEY = 'ledger_anonymous_workspace_v1'

export function workspaceId(): string {
  if (typeof window === 'undefined') return 'legacy-public'
  const existing = window.localStorage.getItem(WORKSPACE_KEY)
  if (existing && /^[A-Za-z0-9_-]{8,64}$/.test(existing)) return existing
  const random = typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID().replace(/-/g, '')
    : `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`
  const created = `ws_${random}`.slice(0, 64)
  window.localStorage.setItem(WORKSPACE_KEY, created)
  return created
}

function withWorkspace(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers)
  headers.set('X-Ledger-Workspace', workspaceId())
  return { ...init, headers }
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(url), withWorkspace(init))
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with HTTP ${response.status}`)
  }
  return payload as T
}

export const api = {
  trackVisit: (body: Record<string, unknown>) =>
    jsonRequest<{ ok: boolean; recorded: boolean; duplicate?: boolean }>('/api/traffic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  providers: () =>
    jsonRequest<{ providers: ProviderInfo[]; reasoning_efforts: string[] }>('/api/providers'),
  settings: () => jsonRequest<SettingsData>('/api/settings'),
  saveSettings: (body: Record<string, unknown>) =>
    jsonRequest<{ ok: boolean; message: string; elapsed: number }>('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  saveRuntimeSettings: (body: Record<string, unknown>) =>
    jsonRequest<{ ok: boolean; max_concurrency: number; auto_concurrency: boolean; has_firecrawl_key: boolean; firecrawl_key_masked: string; firecrawl_pdf_mode: 'fast' | 'auto' | 'ocr'; firecrawl_credits?: { remainingCredits?: number; planCredits?: number } }>('/api/runtime-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  prompt: () => jsonRequest<{ system_prompt: string; default_prompt: string }>('/api/prompt'),
  savePrompt: (systemPrompt: string) =>
    jsonRequest<{ ok: boolean }>('/api/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ system_prompt: systemPrompt }),
    }),
  resetPrompt: () =>
    jsonRequest<{ ok: boolean; system_prompt: string }>('/api/prompt', { method: 'DELETE' }),
  runs: async () => (await jsonRequest<{ runs: RunSummary[] }>('/api/runs')).runs,
  benchmarkRuns: async () => (await jsonRequest<{ runs: RunSummary[] }>('/api/benchmark-runs')).runs,
  run: (id: string) => jsonRequest<RunDetail>(`/api/runs/${encodeURIComponent(id)}`),
  deleteRun: (id: string) =>
    jsonRequest<{ ok: boolean }>(`/api/runs/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  deleteAllRuns: () => jsonRequest<{ ok: boolean; deleted: number }>('/api/runs/all', { method: 'DELETE' }),
  schema: () => jsonRequest<SchemaRow[]>('/api/schema'),
  goldenAnswers: () => jsonRequest<Record<string, Record<string, number>>>('/api/golden_answers'),
  stageUploads: async (files: File[]) => {
    const body = new FormData()
    files.forEach((file) => body.append('pdfs', file))
    return jsonRequest<{
      ok: boolean
      files: StagedFile[]
      advisories?: string[]
      plan: {
        total_pages: number
        total_approx_tokens: number
        recommended_concurrency: number
        advisories: string[]
      }
    }>('/api/uploads', { method: 'POST', body })
  },
  corpus: () => jsonRequest<CorpusManifest>('/api/corpus'),
  corpusPdfUrl: (documentId: string) => apiUrl(`/api/corpus/${encodeURIComponent(documentId)}/pdf`),
  corpusPageImageUrl: (documentId: string, pageNumber: number) =>
    apiUrl(`/api/corpus/${encodeURIComponent(documentId)}/pages/${Math.max(1, Math.trunc(pageNumber))}.png`),
  corpusVerification: (documentId: string) =>
    jsonRequest<CorpusVerification>(`/api/corpus/${encodeURIComponent(documentId)}/verification`),
  extractCorpusVerification: (documentId: string) =>
    jsonRequest<CorpusVerification>(`/api/corpus/${encodeURIComponent(documentId)}/verification/extract`, {
      method: 'POST',
    }),
  approveCorpusVerification: (documentId: string, rows: CorpusVerification['rows']) =>
    jsonRequest<CorpusVerification>(`/api/corpus/${encodeURIComponent(documentId)}/verification`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows }),
    }),
  deleteCorpusDocument: (documentId: string) =>
    jsonRequest<{ ok: boolean; deleted: { filename: string; file_removed: boolean } }>(`/api/corpus/${encodeURIComponent(documentId)}`, { method: 'DELETE' }),
  stageCorpusDocuments: (documentIds: string[]) =>
    jsonRequest<{
      ok: boolean
      files: StagedFile[]
      advisories?: string[]
      plan: { total_pages: number; total_approx_tokens: number; recommended_concurrency: number; advisories: string[] }
    }>('/api/corpus/stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: documentIds }),
    }),
  startCorpusJob: (body: Record<string, unknown>) =>
    jsonRequest<{ ok: boolean; job_id: string; status: string }>('/api/corpus/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  corpusJobs: () => jsonRequest<{ jobs: CorpusJob[] }>('/api/corpus/jobs'),
  corpusJob: (id: string) => jsonRequest<CorpusJob>(`/api/corpus/jobs/${encodeURIComponent(id)}`),
  bakurakuCustomers: () => jsonRequest<{ count: number; customers: Array<Record<string, string>> }>('/api/bakuraku/customers'),
  extractionJobs: () => jsonRequest<{ jobs: Array<Omit<ExtractionJob, 'events' | 'next_offset'>> }>('/api/extraction/jobs'),
  extractionJob: (id: string, after = 0) => jsonRequest<ExtractionJob>(`/api/extraction/jobs/${encodeURIComponent(id)}?after=${Math.max(0, after)}`),
  startExtractionJob: (body: Record<string, unknown>) =>
    jsonRequest<{ ok: boolean; job_id: string; status: string }>('/api/extraction/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
}

export interface SseEvent<T = Record<string, unknown>> {
  event: string
  data: T
  at?: string
}

export async function consumeEventStream(
  response: Response,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.error || `Execution failed with HTTP ${response.status}`)
  }
  if (!response.body) throw new Error('The server returned no event stream.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const flush = (block: string) => {
    let event = 'message'
    const data: string[] = []
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      if (line.startsWith('data:')) data.push(line.slice(5).trim())
    }
    if (!data.length) return
    onEvent({ event, data: JSON.parse(data.join('\n')) })
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    blocks.forEach(flush)
    if (done) break
  }
  if (buffer.trim()) flush(buffer)
}

export async function runStagedExtraction(
  body: Record<string, unknown>,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const response = await fetch(apiUrl('/api/extract/stream'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Ledger-Workspace': workspaceId() },
    body: JSON.stringify(body),
  })
  return consumeEventStream(response, onEvent)
}
