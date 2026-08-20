export type PanelKey =
  | 'dashboard'
  | 'strategy1'
  | 'strategy2'
  | 'strategy3'
  | 'strategy4'
  | 'history'
  | 'corpus'
  | 'schema'
  | 'settings'

export type MetricValue = number | null | undefined

export interface RunMetrics {
  accuracy?: MetricValue
  coverage?: MetricValue
  precision?: MetricValue
  consistency?: MetricValue
  exact_matches?: number
  total_compared?: number
  filled_fields?: number
  committed_and_compared?: number
  has_golden?: boolean
}

export interface RunSummary extends RunMetrics {
  run_id: string
  timestamp?: string
  strategy: string
  strategy_label?: string
  model?: string
  fiscal_year?: string
  detected_fiscal_year?: string
  pdf_file?: string
  page_count?: number
  approx_input_tokens?: number
  extract_seconds?: MetricValue
  total_seconds?: MetricValue
  api_elapsed?: MetricValue
  row_count?: number
  warnings?: string[]
  contract_repairs?: string[]
  failed_identities?: string[]
}

export interface AssetRow {
  classification: string
  subclassification: string
  item: string
  description: string
  answer_m_usd: number | null
  confidence: number
  accepted?: boolean
  source_page: number | null
  source_label: string | null
  evidence: string | null
}

export interface ReconciliationCheck {
  identity: string
  total_item: string
  status: 'ok' | 'failed' | 'skipped'
  reason?: string | null
  stated?: number | null
  computed?: number | null
  delta?: number | null
}

export interface RunDetail extends RunSummary {
  ok: boolean
  rows: AssetRow[]
  metrics: RunMetrics
  reconciliation?: {
    checks: ReconciliationCheck[]
    total_identities: number
    evaluated: number
    passed: number
    failed: number
    skipped: number
    consistency: MetricValue
    failed_identities: string[]
  }
  usage?: Record<string, number>
  parser_diagnostics?: Record<string, unknown>
  garbled_pages?: number[]
  readable_pages?: number
}

export interface SchemaRow {
  classification: string
  subclassification: string
  item: string
  description: string
  golden_answers: Record<string, number | null>
}

export interface ProviderInfo {
  key: string
  label: string
  base_url: string
  default_model: string
  suggested_models: string[]
  reasoning_style: string
  automatic_prompt_caching: boolean
  docs: string
}

export interface SettingsData {
  provider: string
  provider_label: string
  model: string
  base_url: string
  api_key_masked: string
  has_key: boolean
  reasoning_effort: string
  reasoning_style: string
  prompt_caching: boolean
  enable_reasoning: boolean
  temperature: number
  max_concurrency: number
  auto_concurrency: boolean
  firecrawl_key_masked: string
  has_firecrawl_key: boolean
  rate_limit: {
    max_concurrency?: number
    permitted_concurrency?: number
    in_flight?: number
    throttle_events?: number
    paused_for_seconds?: number
    observed_headers?: Record<string, unknown>
  }
  firecrawl_credits?: {
    remainingCredits?: number
    planCredits?: number
  }
}

export interface CorpusDocument {
  company: string
  company_slug: string
  fiscal_year: number
  source_url: string
  local_path: string
  filename: string
  downloaded_at: string
  sha256: string
  pages: number
  readable_pages: number
  balance_sheet_page: number | null
  currency: string
  screened: 'ok' | 'review' | 'unreadable'
  fiscal_year_confirmed: boolean
  official_source_verified?: boolean
  screen_reasons?: string[]
  output_directory?: string
  output_count?: number
}

export interface CorpusManifest {
  version: number
  updated_at: string | null
  documents: CorpusDocument[]
  summary: { documents: number; companies: number; ok: number; review: number; unreadable: number }
}

export interface CorpusJob {
  id: string
  status: 'queued' | 'running' | 'complete' | 'failed'
  events: Array<Record<string, unknown>>
  result?: { downloaded: CorpusDocument[]; failed: Array<Record<string, unknown>> } | null
  error?: string | null
}

export interface StagedFile {
  id?: string
  name: string
  path?: string
  size_bytes?: number
  pages?: number
  approx_tokens?: number
  error?: string
}

export interface ExecutionPass {
  strategy: string
  strategyLabel: string
  state: 'queued' | 'running' | 'complete' | 'failed'
  step?: string
  message?: string
  runId?: string
  metrics?: RunMetrics
  error?: string
  steps?: Record<string, {
    state: 'queued' | 'running' | 'complete' | 'failed'
    message?: string
    durationSeconds?: number
  }>
}

export interface ExecutionFile {
  name: string
  pages?: number
  approxTokens?: number
  state: 'queued' | 'running' | 'complete' | 'failed'
  passes: ExecutionPass[]
}
