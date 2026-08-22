export type PanelKey =
  | 'dashboard'
  | 'strategy1'
  | 'strategy2'
  | 'strategy3'
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
  gold_company?: string | null
  gold_status?: 'assignment_supplied' | 'human_verified' | 'human_review_required' | 'unavailable' | string
}

export interface RunSummary extends RunMetrics {
  run_id: string
  timestamp?: string
  strategy: string
  strategy_label?: string
  parser?: string
  experiment?: 'no_ocr' | 'ocr' | 'intelligent_scan' | 'legacy_no_ocr'
  ocr_enabled?: boolean
  ocr_policy?: 'off' | 'adaptive' | 'force'
  company?: string
  currency?: string
  value_scale?: 'millions' | string
  answer_unit?: string
  source_pdf_sha256?: string
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
  firecrawl_pdf_mode: 'fast' | 'auto' | 'ocr'
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
  verification_status?: 'assignment_supplied' | 'human_verified' | 'independently_verified' | 'human_review_required'
  candidate_extracted?: boolean
  candidate_count?: number
  candidate_method?: string | null
  consensus_summary?: CorpusConsensusSummary | null
  approved_at?: string | null
}

export interface CorpusConsensusSummary {
  requested_passes: number
  successful_passes: number
  exact_agreement_rows: number
  stable_rows: number
  disagreement_rows: number
  missing_rows: number
}

export interface CorpusTarget {
  company: string
  official_url: string
  country: string
  evidence_url: string
  status: 'report_stored' | 'research_seed'
}

export interface CorpusManifest {
  version: number
  updated_at: string | null
  documents: CorpusDocument[]
  targets?: CorpusTarget[]
  summary: { documents: number; companies: number; companies_with_reports?: number; ok: number; review: number; unreadable: number; verified?: number; human_review_required?: number }
}

export interface CorpusVerificationRow {
  classification: string
  subclassification: string
  item: string
  answer_m_usd: number | null
  source_page?: number | null
  evidence?: string | null
  pass_values?: Array<number | null>
  agreement_count?: number
  successful_passes?: number
  agreement_ratio?: number
  stability?: 'exact' | 'stable' | 'disagreement' | 'missing'
}

export interface CorpusVerification {
  document_id: string
  company: string
  fiscal_year: number
  filename: string
  currency: string
  value_scale?: string
  answer_unit?: string
  sha256: string
  status: 'assignment_supplied' | 'human_verified' | 'independently_verified' | 'human_review_required'
  immutable?: boolean
  candidate_extracted?: boolean
  extracted_row_count?: number
  approved_at?: string | null
  candidate_method?: string | null
  consensus_summary?: CorpusConsensusSummary | null
  rows: CorpusVerificationRow[]
}

export interface CorpusJob {
  id: string
  status: 'queued' | 'running' | 'complete' | 'failed' | 'interrupted'
  events: Array<Record<string, unknown>>
  created_at?: string
  updated_at?: string
  finished_at?: string
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
  verification_status?: 'assignment_supplied' | 'human_verified' | 'independently_verified' | 'human_review_required'
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
  totalSeconds?: number | null
  extractSeconds?: number | null
  fiscalYear?: string
  error?: string
  steps?: Record<string, {
    state: 'queued' | 'running' | 'complete' | 'failed'
    message?: string
    durationSeconds?: number
  }>
}

export interface ExtractionJobEvent {
  event: string
  data: Record<string, unknown>
  at: string
}

export interface ExtractionJob {
  id: string
  status: 'queued' | 'running' | 'complete' | 'failed' | 'interrupted'
  scope: 's1' | 's2' | 's3'
  strategies: string[]
  files_total: number
  passes_total: number
  succeeded: number
  failed: number
  error?: string | null
  created_at: string
  updated_at: string
  events: ExtractionJobEvent[]
  next_offset: number
}

export interface ExecutionFile {
  name: string
  pages?: number
  approxTokens?: number
  state: 'queued' | 'running' | 'complete' | 'failed'
  passes: ExecutionPass[]
}
