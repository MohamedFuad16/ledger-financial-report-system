# Architecture

The app turns Annual Report PDFs into a fixed 27-row asset-side balance sheet. A Flask API stages uploads and coordinates extraction strategies, provider calls, validation, reconciliation, scoring, and file-backed run persistence. The browser UI configures and observes those workflows.

## Major components

- **Web client** — `frontend/` is a typed React/Vite SPA; Vercel serves the public production bundle, while Flask can still serve `frontend/dist/` locally.
- **HTTP API** — `server.py` exposes settings, upload, extraction, streaming, run, schema, evaluation, and bounded visit-telemetry endpoints. A process-wide two-slot admission gate limits the local parser/render/OCR phase across every endpoint and anonymous workspace; additional requests wait without occupying another heavy pipeline slot.
- **Pipeline** — `pipeline.py` orchestrates the strategy-independent lifecycle.
- **Extraction strategies** — `extraction.py` wraps PyPDF, PyMuPDF4LLM, Docling, and pdf-inspector behind one result type.
- **Contract and repair** — `normalize.py`, `models.py`, and `schema.py` normalize representations and enforce the 27-row contract.
- **Quality** — `reconcile.py` checks arithmetic identities; `pipeline.compute_metrics` scores only the assignment-supplied 3M FY2022 key or a human-approved 27-row table bound to the exact corpus PDF SHA-256.
- **Provider boundary** — `api_client.py`, `providers.py`, and `ratelimit.py` handle compatible LLM APIs and adaptive concurrency.
- **Corpus boundary** — `corpus/` discovers official Annual Reports through Firecrawl, downloads directly, screens locally, and atomically updates a SHA-256 manifest. Runtime corpus data is selected by `LEDGER_CORPUS_ROOT`, lives on persistent cloud storage, and is never tracked in Git.
- **Persistence** — uploads and runs use company/year/timestamp namespaces and carry an anonymous browser-workspace owner; each corpus company/year has one canonical manifest-owned PDF that is atomically replaced after a successful recrawl. Browser uploads are PDF-magic checked, capped at 128 MB each and 512 MB/50 files per workspace, removed after two hours, and deleted immediately when staging fails. Extraction and corpus job snapshots live under `runs/_extraction_jobs` and `runs/_corpus_jobs`; both are rehydrated independently of browser route state.
- **Private traffic boundary** — `traffic.py` writes bounded per-session metadata and counters to Upstash and uses the EC2 role to send owner-only SES notifications. Connector values are loaded from SSM and never enter Vercel.
- **Production runtime** — Caddy terminates TLS on one SSM-managed Tokyo EC2 `t3.medium` instance and proxies to one 10-thread Gunicorn worker on loopback. The one-process runtime makes the two-slot parser/OCR gate host-wide. SSM Parameter Store holds private connector values; no secret is bundled into Vercel. The assignment API has no browser access token, while CORS remains limited to approved UI origins.

## Control flow

1. The React client stages one or more PDFs with the API and renders real SSE lifecycle events.
2. `server.run_pipeline_bounded` admits no more than two concurrent local pipelines. Each admitted `pipeline.run_pipeline` extracts text, builds the prompt, calls the selected provider, parses and normalizes JSON, validates the contract, and makes at most one context-preserving repair call when JSON/Pydantic validation fails. It then flags low-confidence rows for review, reconciles every returned value, scores raw exactness/coverage plus separate confidence diagnostics, and files the run. OpenRouter concurrency remains separately governed by the adaptive outbound limiter.
3. Streaming endpoints emit per-file phase events and persist job snapshots. The client rehydrates unfinished jobs only on the matching strategy route after navigation or refresh, then reduces events into one current-company surface with up to six fiscal-year chips and one active report card. Completed predictions are served to the UI and exports; strategy aggregates use only reports completed by every selected parser and weight each report once.

Corpus flow is deliberately separate: React or the CLI supplies companies and FY2020–FY2025, a cross-process request gate spaces Firecrawl calls and honors account-wide cooldowns, Firecrawl discovers candidate report URLs, and Ledger directly downloads and screens the selected PDF. Opening Review answers runs one configured-LLM semantic mapping over the pinned PDF and stores a non-authoritative 27-row candidate. The review workspace embeds a searchable PDF beside those prefilled rows; a reviewer corrects discrepancies and approves the table for that exact SHA-256. Extraction failure remains a retry state. An unapproved report can still be executed with a warning, but it is excluded from exact-accuracy metrics. The discovery worker is deterministic Python orchestration, not an autonomous LLM agent.

Strategy 1 and Strategy 2 each expose the same four selectable parsers. Strategy 1 disables OCR for all four. Strategy 2 forces OCR for PyPDF and Docling, uses PyMuPDF4LLM's integrated adaptive OCR, and uses pdf-inspector as a page classifier: native Rust extraction for text pages, exact 200-DPI rendering plus local RapidOCR PP-OCRv6 ONNX for OCR-needed pages, followed by page-ordered assembly. Strategy 3 is one finalized pdf-inspector path: classification and complete per-page Markdown, selective 200-DPI local RapidOCR replacement only for parser-routed pages, unified page assembly, deterministic three-to-five-page scoring in `intelligent_scan.py`, then semantic mapping and validation.

In production this file-backed state lives on the EC2 instance's encrypted EBS volume, not in browser storage. It survives page refreshes and service restarts, but the current single-instance root volume is not a multi-AZ object-store backup and is configured for deletion if the instance is terminated.

See `agent/graph/architecture.svg` and `agent/graph/graph.md`.
