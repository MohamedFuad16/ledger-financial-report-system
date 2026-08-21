# Ledger: current system status

Last verified: 21 August 2026

## What is running

Ledger is a split React/Flask application:

```text
Browser
  └─ React 19 + TypeScript + Vite (Vercel)
       ├─ dashboard, charts, tables and bilingual UI
       ├─ upload/corpus selection
       └─ live Server-Sent Event rendering
            │ HTTPS JSON / SSE
            ▼
Flask + Gunicorn (Tokyo EC2)
  ├─ PDF staging and corpus management
  ├─ PyPDF / PyMuPDF4LLM / pdf-inspector / Docling
  ├─ prompt construction and provider calls
  ├─ contract normalization, validation and scoring
  ├─ disk-backed PDFs, manifests and run artifacts
  └─ private visit telemetry through Upstash + AWS SES
```

The frontend never receives the model key, Firecrawl key, Upstash token or email configuration. It sends user actions to the Flask API and displays the returned data. The backend owns all native PDF work, provider calls, filesystem persistence and secret-bearing integrations.

The API does not use a browser/deployment access token. CORS limits which browser origins may call it, and the adaptive request limiter controls provider concurrency. The service is suitable for this public assignment, but it is not an authenticated multi-tenant product: anyone who can call its public API origin can request work that uses configured provider quota.

## Shared extraction lifecycle

Every active parser follows the same pipeline. Only the document representation changes.

1. **Stage the PDF.** A browser upload is saved under `uploads/<company>/<year>/<timestamp>/`, or a selected corpus document is referenced in place after its manifest SHA-256 and path are validated.
2. **Extract locally.** The chosen parser converts every readable page and the backend inserts `--- PAGE n ---` markers. No LLM call has happened yet.
3. **Build one prompt.** `prompts.build_user_prompt` combines the extraction note, parser diagnostics, the fixed 27-row schema, any detected fiscal context and the complete extracted report. The configured system prompt is sent separately as the first message.
4. **Call the model once.** `api_client.run_extraction` sends an OpenAI-compatible `chat/completions` request with JSON-object output requested. Provider-specific reasoning controls are mapped in `providers.py`; temperature defaults to `0.1`.
5. **Retry transport failures safely.** HTTP 429 responses reduce the shared concurrency gate and honor `Retry-After`; retryable 5xx responses use bounded backoff. Quota exhaustion fails immediately.
6. **Normalize and validate.** `normalize.py` repairs representation-only issues such as currency strings, percentages, aliases and row order, recording each repair. `models.py` then requires the exact 27-row contract. If JSON or contract validation still fails, one bounded semantic repair request includes the original context, invalid answer and exact validation error.
7. **Apply the confidence gate.** A row is accepted only when it has a value and confidence is at least `0.80`. The raw value remains stored for audit.
8. **Verify and score.** `reconcile.py` checks deterministic balance-sheet identities without changing values. `compute_metrics` separately measures coverage, exact accuracy and precision against a golden set when one exists.
9. **Persist the run.** Request, raw response, optional repair artifacts and `prediction.json` are filed under `runs/<company>/FY<year>/<run_id>/`. Real progress events are streamed to the execution capsules throughout the run.

## Strategy 1: direct LLM baseline

Strategy 1 deliberately measures the simplest text representation.

```text
Annual Report PDF
  → PyPDF page.extract_text()
  → normalized raw page text in memory
  → page-number markers
  → fixed system prompt + 27-row user contract + full report text
  → configured model
  → normalized and validated 27-row JSON
  → confidence gate, reconciliation, golden-set metrics
  → stored prediction
```

Important details:

- PyPDF does not create an intermediate Markdown file. It produces one in-memory string from page-by-page `extract_text()` output.
- It performs no OCR, table reconstruction, chunking, retrieval or reranking.
- Flattened columns can interleave, which is the intended control condition.
- Basic metadata and relevant outline entries are included only as diagnostics when available.

## Strategy 2: representation bake-off

Strategy 2 keeps the prompt, model, schema, validation and scoring constant while changing the parser. One selected PDF runs through the selected parser passes sequentially; separate PDFs may run concurrently.

| Parser | Representation | Role |
|---|---|---|
| PyPDF | Raw page text | Baseline included for comparison |
| PyMuPDF4LLM | Layout-aware Markdown, page chunks, OCR disabled | Preserves headings and table structure |
| pdf-inspector | Position-aware Markdown from a Rust parser | Preserves reading order and reports document/table diagnostics |
| Docling | ML document model and Markdown graph | Optional, slowest and most resource-intensive pass |

Each pass produces an independent model request and run artifact. This makes parser timing, token load, coverage and accuracy directly comparable on the same PDF. Docling is optional because its model load is CPU/memory heavy; its conversions are serialized.

## Model response and output contract

The model must return one JSON object containing a detected fiscal year and exactly 27 rows. Each row carries the canonical classification, subclassification, item, description, value in millions of USD, confidence and evidence metadata. The main assignment result sheet intentionally displays only:

1. Classification
2. Subclassification
3. Item
4. Answer (M USD)

Evidence, source labels, confidence, warnings and arithmetic diagnostics stay in the stored run for audit and are not required in the compact result sheet.

The answer key is never sent to the model. It is read only after a prediction has passed validation and the confidence gate.

## Corpus acquisition and reuse

The Report corpus workflow is independent from extraction:

```text
Company + official site + FY2020–FY2025
  → Firecrawl map/search for candidate official-report URLs
  → direct PDF download
  → MIME/signature, year, balance-sheet and text-health screening
  → SHA-256 manifest entry
  → corpus_dataset/<company>/<year>/<downloaded_at>/<company>_annual_report_<year>.pdf
```

Crawling never starts a model extraction. Strategy 1 and Strategy 2 expose an Upload/Corpus switch; a corpus search can stage one document or a batch through the same extraction API without duplicating the PDF.

### Verified corpus smoke test

On 21 August 2026, the Firecrawl workflow discovered the official 3M FY2022 SEC filing on `investors.3m.com`. Ledger downloaded and normalized it to `3M_annual_report_2022.pdf`, matched SHA-256 `d5cf549543a24b04228fd2af979ff2ca94cf64fb008a789340cb9117fbcfde5d`, confirmed FY2022 and the balance sheet on page 38, and screened all 252 pages as readable. The same manifest identity was then selected through the production `/api/corpus/stage` contract: it returned HTTP 200 as a `source: corpus` staged file with 252 pages, no browser access token, and no copied PDF.

Firecrawl credential persistence was also verified against production using an empty replacement field: the backend reused the masked saved credential, completed the read-only credit probe, returned HTTP 200, and kept the key server-side.

## Frontend responsibilities

- English/Japanese locale state and localized display labels
- responsive desktop rail and mobile drawer
- report upload or corpus selection
- provider/runtime settings forms without exposing saved secret values
- real-time SSE task capsules and elapsed-time display
- dashboard charts, run history, compact result tables and CSV export

## Backend responsibilities

- persistent PDF, corpus manifest and run storage
- PDF parsing and parser diagnostics
- prompt construction and provider-specific reasoning payloads
- adaptive concurrency, rate-limit backoff and quota handling
- deterministic normalization, Pydantic validation, one bounded repair, confidence gating and scoring
- Firecrawl discovery/download jobs
- private traffic event persistence and owner-only HTML email notification

## Current deployment

| Surface | Runtime |
|---|---|
| Web application | Vercel static deployment |
| API and extraction workers | Gunicorn on one `t3.medium` EC2 instance in `ap-northeast-1` |
| TLS/reverse proxy | Caddy |
| Durable application data | EC2 filesystem |
| Visit counters/event log | Upstash Redis REST |
| Visit notification | AWS SES from the EC2 role |

## Current limitations

- Strategies 3 and 4 remain planned.
- Text-only parsers cannot recover scanned pages or PDFs with broken font mappings; those require OCR or a vision strategy.
- File-backed state is tied to one EC2 instance and is not horizontally shared.
- The public assignment API has no end-user authentication. CORS is a browser boundary, not authentication.
- Golden-answer accuracy is available only for fiscal years with a maintained key; reconciliation remains available for every company.
