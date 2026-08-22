# Ledger: current system status

Last verified: 22 August 2026

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
2. **Extract locally.** The chosen parser converts readable pages and the backend inserts `--- PAGE n ---` markers. Strategy 3 additionally replaces only pdf-inspector-routed OCR pages and selects three to five complete pages. No semantic-mapping LLM call has happened yet.
3. **Build one prompt.** `prompts.build_user_prompt` combines the extraction note, parser diagnostics, the fixed 27-row schema, any detected fiscal context and that strategy's complete page-marked representation. The configured system prompt is sent separately as the first message.
4. **Call the model once.** `api_client.run_extraction` sends an OpenAI-compatible `chat/completions` request with JSON-object output requested. Provider-specific reasoning controls are mapped in `providers.py`; temperature defaults to `0.0` for reproducible extraction.
5. **Retry transport failures safely.** HTTP 429 responses reduce the shared concurrency gate and honor `Retry-After`; retryable 5xx responses use bounded backoff. Quota exhaustion fails immediately. These retries repeat the same request and are not semantic repairs.
6. **Normalize and validate.** `normalize.py` repairs representation-only issues such as currency strings, percentages, aliases and row order, recording each repair. `models.py` then requires the exact 27-row contract. If JSON or Pydantic contract validation still fails, one bounded semantic repair request includes the original context, invalid answer and exact validation error.
7. **Flag review priority.** A row is confidence-accepted when it has a value and confidence is at least `0.80`, but lower-confidence values remain visible and usable. Confidence never determines correctness.
8. **Verify and score.** `reconcile.py` checks every returned value against deterministic balance-sheet identities without changing it. `compute_metrics` measures raw field coverage, exact accuracy and precision; confidence-accepted coverage and precision remain separate diagnostics.
9. **Persist the run and job.** Request, raw response, optional repair artifacts and `prediction.json` are filed under `runs/<strategy>/FY<year>/<run_id>/`. The extraction job itself is also written under `runs/_extraction_jobs/`, so it continues on the backend and can be rehydrated after navigation or refresh. Real progress events update one animated live card per report; the card advances through the active parser and stage while a compact rail preserves overall comparison progress.

The repair boundary is intentionally narrow: confidence below `0.80` never triggers a model retry, and a failed arithmetic identity never triggers a model retry. Both are downstream measurements of a contract-valid answer.

## Strategy 1: four-parser no-OCR control

Strategy 1 exposes the same four parsers with OCR disabled.

| Parser | Strategy 1 representation | OCR policy |
|---|---|---|
| PyPDF | Raw page text assembled in memory with page markers | Off |
| PyMuPDF4LLM | Layout-aware Markdown with complete page boundaries | Off |
| pdf-inspector | Position-aware native Rust Markdown | Off |
| Docling | ML document graph converted to Markdown | Off |

## Strategy 2: four-parser OCR-enabled arm

Strategy 2 exposes the four selectable parsers with OCR enabled. “Adaptive” applies only to a parser that has a real page-level decision mechanism; it does not mean that OCR is optional for the whole strategy.

| Parser | Strategy 2 OCR behavior | Policy |
|---|---|---|
| PyPDF | Renders and OCRs every page because PyPDF has no trusted OCR-needed classifier | Compulsory |
| PyMuPDF4LLM | Uses its integrated page-aware OCR recovery | Adaptive |
| pdf-inspector | Classifies every page; retains native Rust text for text pages and processes only OCR-needed pages through local 200-DPI RapidOCR PP-OCRv6 ONNX | Adaptive |
| Docling | Runs document conversion with OCR forced for every page | Compulsory |

The user may select one parser or any subset; every pass produces its own model request and stored prediction against the same PDF, model, prompt, schema, and evaluation code.

The exact pdf-inspector path is:

```text
PDF
  → pdf-inspector per-page classification
      ├─ text page → native Rust extraction
      └─ OCR-needed page
           → render at exactly 200 DPI
           → local RapidOCR PP-OCRv6 ONNX recognition
           → Markdown for that page
  → page-ordered Markdown assembly
  → shared prompt/model/contract/evaluation pipeline
```

Per-page provenance records the decision, reason, engine, page number and render DPI. Each selected pass still produces an independent model request and run artifact.

## Strategy 3: pdf-inspector intelligent scanning gate (active)

Strategy 3 uses pdf-inspector 1.15+ as the finalized parser. The verified Python API supplies document classification, confidence, encoding health, complete per-page Markdown, OCR-needed pages/reasons, table pages, column pages and complexity metadata. Ledger OCRs only parser-routed pages at 200 DPI, replaces their page bodies in the unified Markdown, scores every complete page with schema/accounting BM25-style terms plus heading/table/layout/numeric signals, and sends the top three to five pages to the configured LLM. The existing semantic JSON mapping, deterministic validation, confidence gating, reconciliation and human approval remain unchanged. Run diagnostics preserve the classification, page provenance, every selected score component and input reduction. No vector store, embeddings, token chunks, recursive retrieval or agentic loop are present.

The live and historical comparison now uses a matched report cohort: a report contributes to parser averages only when every selected parser completed that report. Repeated observations are averaged within each report before reports are averaged, preventing a parser rerun or a failed pass from silently changing the comparison population. Scheduled, successful and failed pass counts remain visible, and each PDF's individual values remain in its run history.

## Model response and output contract

The model must return one JSON object containing a detected fiscal year and exactly 27 rows. Each row carries the canonical classification, subclassification, item, description, value in millions of USD, confidence and evidence metadata. The main assignment result sheet intentionally displays only:

1. Classification
2. Subclassification
3. Item
4. Answer (M USD)

Evidence, source labels, confidence, warnings and arithmetic diagnostics stay in the stored run for audit and are not required in the compact result sheet.

The answer key is never sent to the model. It is read only after a prediction has passed contract validation; confidence is not used to reveal, hide or select gold values.

### Benchmark-key assurance

There are three different checks, and they must not be conflated:

1. **Corpus screening** proves that the downloaded bytes are a PDF from the expected official domain, records a SHA-256 identity, checks the expected fiscal year inside the file, counts readable/garbled pages, and looks for a balance-sheet page and currency. This is document identity and health evidence, not an answer-key audit.
2. **Arithmetic reconciliation** proves that a set of 27 values obeys the schema's subtotal identities. It catches inconsistent totals, but an internally consistent set can still be copied from the wrong column or year.
3. **Golden-set verification** requires source-level provenance for every value. Only the 3M FY2022 27-row answer key supplied by the assignment is authoritative by default. Every other company/year begins with configured-LLM semantic mapping and has no exact-accuracy score until a person reviews all 27 rows against the source PDF and saves approval. The review workspace is extracted-first: it embeds the searchable pinned PDF beside 27 prefilled rows, permits corrections, and exposes Save & Approve only after a candidate artifact exists. Approval is bound to the exact PDF SHA-256, so replacing the PDF invalidates that approval.

For a defensible manual audit, one reviewer should transcribe each leaf value from the rendered official PDF and record the printed page/table/column/unit; a second reviewer should independently re-enter it; computed subtotals should be regenerated from the leaves; disagreements should be resolved against the rendered page; and the final key should be pinned to the same PDF SHA-256 used by the run. Exact accuracy should not be reported as authoritative for a provisional key without that qualifier.

### FY2021 incident audit

The historical 3M FY2021 `3.7%` value was `1 / 27`, but it was calculated against a project-derived reference that is no longer an authoritative runtime gold set. The document also has a broken font-to-Unicode mapping: its balance sheet renders visibly while ordinary text extraction returns glyph-code noise. It is therefore useful evidence for comparing Strategy 1 with the new OCR-enabled Strategy 2, but Ledger now reports speed and coverage—not exact accuracy—until a reviewer approves a SHA-bound FY2021 table.

## Corpus acquisition and reuse

The Report corpus workflow is independent from extraction:

```text
Company + official site + FY2020–FY2025
  → Firecrawl call 1: map/search for candidate official-report URLs
  → direct PDF download to the canonical company/year path
  → MIME/signature, year, balance-sheet and text-health screening
  → user opens Review answers
  → one configured-LLM semantic-mapping pass over the pinned PDF
  → provisional 27-row candidate table
  → SHA-256-bound manifest + candidate review artifact
  → human review in the Corpus UI (optional before execution, required for accuracy)
```

Crawling never starts a Strategy 1/2 model extraction. A screened recrawl atomically replaces the canonical company/year file, while a failed replacement leaves the prior PDF intact. Strategy 1 and Strategy 2 expose an Upload/Corpus switch; a corpus search can stage one document or a batch through the same extraction API without duplicating the PDF. Unverified documents are usable, but the picker warns that their candidate answers are not gold and their runs will not contribute to exact-accuracy leadership.

The corpus worker is deterministic Python orchestration running in the EC2 Gunicorn service. Firecrawl supplies link discovery only. Ledger spaces all credit-consuming Firecrawl calls through one cross-process gate (12.5 seconds by default), honors account-wide `Retry-After`, and adds bounded jittered retry backoff. For documents without a candidate artifact, the Review action runs the configured LLM semantic mapping before rendering editable inputs; failures stay in a retry state instead of falling back to manual transcription. The worker itself uses ordinary HTTPS download, PyPDF screening, hashing and atomic filesystem writes; it is not an autonomous LLM agent.

Corpus job state is atomically snapshotted under `runs/_corpus_jobs/<job-id>/state.json`. The Report corpus page lists and rehydrates the newest active or recent job, so route changes and browser reloads no longer own or erase progress. The thread continues independently on the backend. A service restart cannot resume an in-flight Python thread, but the preserved state is marked `interrupted` instead of disappearing, and a new job can be started. Canonical PDFs and the manifest live separately on EBS and remain available.

### Verified corpus smoke tests

On 21 August 2026, the Firecrawl workflow discovered the official 3M FY2022 SEC filing on `investors.3m.com`. Ledger downloaded and normalized it to `3M_annual_report_2022.pdf`, matched SHA-256 `d5cf549543a24b04228fd2af979ff2ca94cf64fb008a789340cb9117fbcfde5d`, confirmed FY2022 and the balance sheet on page 38, and screened all 252 pages as readable. The same manifest identity was then selected through the production `/api/corpus/stage` contract: it returned HTTP 200 as a `source: corpus` staged file with 252 pages, no browser access token, and no copied PDF.

Firecrawl credential persistence was also verified against production using an empty replacement field: the backend reused the masked saved credential, completed the read-only credit probe, returned HTTP 200, and kept the key server-side.

The same workflow was then tested against AppBank's official Japanese IR library. Firecrawl followed the official securities-report page to the FY2024 filing, downloaded `AppBank_annual_report_2024.pdf`, verified the official source, screened all 105 pages as readable, detected FY2024 and found the balance sheet on page 68. The file is visible as `Ready` in both strategy corpus selectors and reuses the canonical company/year path rather than creating duplicates.

This successful Japanese crawl also exposes an important experiment boundary: the AppBank filing is denominated in JPY, while the assignment's fixed output contract requires M USD and forbids external facts. It is therefore valid corpus data but not yet a valid M-USD benchmark input. Ledger should introduce an explicit currency-aware contract and a documented conversion source before running this or other Japanese filings through the accuracy comparison.

## Frontend responsibilities

- English/Japanese locale state and localized display labels
- responsive desktop rail and mobile drawer
- side-by-side pinned-PDF and extracted-answer human review with correction and SHA-bound approval
- report upload or corpus selection
- provider/runtime settings forms without exposing saved secret values
- real-time SSE reduction into one animated report card with current parser, stage, message, elapsed time and compact pass progress
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

- Strategy 1, Strategy 2 and Strategy 3 are active; Strategy 3 is one finalized pdf-inspector pass rather than a parser bake-off.
- Strategy 1 is intentionally no-OCR; Strategy 2 provides compulsory or page-adaptive OCR.
- File-backed state is tied to one EC2 instance and is not horizontally shared.
- The public assignment API has no end-user authentication. CORS is a browser boundary, not authentication.
- Golden-answer accuracy is available only for fiscal years with a maintained key; reconciliation remains available for every company.
- Only 3M FY2022 has an assignment-supplied complete answer key. Every other report remains unscored until its 27-row candidate sheet is manually approved for the exact PDF SHA-256.
- Strategy 2 is an end-to-end OCR-parser capability bake-off, not a pure OCR-only causal ablation, because different parsers use different OCR engines and routing behavior. A future shared OCR-normalized control would isolate the OCR-engine effect.
- Final accuracy can include deterministic normalization and one contract-repair call. Benchmark reporting should therefore add first-pass validity, repair rate, raw accuracy, confidence calibration, extra model calls, latency and cost.
- Bulk crawling 112 customers does not imply 112 usable annual-report issuers. Many Bakuraku customers are private, and Japanese filings need a currency-aware benchmark contract before model extraction.
