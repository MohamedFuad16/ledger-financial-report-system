<p align="center">
  <img src="frontend/public/ledger-icon.png" width="96" alt="Ledger logo" />
</p>

<h1 align="center">Ledger</h1>

<p align="center">
  Extract, verify and benchmark the asset side of Annual Report balance sheets.
</p>

<p align="center">
  <img alt="React" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111827" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" />
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Python-000000?logo=flask&logoColor=white" />
  <img alt="AWS" src="https://img.shields.io/badge/Backend-AWS_EC2-FF9900?logo=amazonwebservices&logoColor=white" />
  <img alt="Vercel" src="https://img.shields.io/badge/Frontend-Vercel-000000?logo=vercel&logoColor=white" />
</p>

<p align="center">
  <a href="https://assignment.mohamedfuad.com">Open Ledger</a>
  ·
  <a href="docs/CURRENT_STATUS.md">Architecture report</a>
  ·
  <a href="ROADMAP.md">Strategy roadmap</a>
</p>

---

## Overview

Ledger is a bilingual Annual Report benchmark workspace. It converts a PDF into a fixed 27-row asset-side balance-sheet contract, calls an OpenAI-compatible model for semantic mapping, validates the result, flags low-confidence rows for review and benchmarks the extracted values against maintained golden answers.

The current assignment uses 3M reports as the initial benchmark, while the corpus pipeline is company-independent and supports official FY2020–FY2025 reports.

## Features

- **Two active extraction strategies** — the same four selectable parsers without OCR (Strategy 1) and with OCR (Strategy 2).
- **Strategy 3 intelligent scanning gate** — pdf-inspector performs native page extraction and OCR routing, Ledger replaces only routed pages with OCR Markdown, then a deterministic gate sends the top three to five complete pages to the same 27-row semantic mapper.
- **Four parser passes** — PyPDF, PyMuPDF4LLM, pdf-inspector and Docling can be selected individually or together.
- **Fixed output contract** — exactly 27 canonical rows, normalized and validated before use.
- **Truthful evaluation** — exact accuracy, field coverage and precision are separate metrics.
- **Live execution** — real Server-Sent Events drive each timed task capsule.
- **Official-report corpus** — Firecrawl discovery, direct PDF download, health screening and SHA-256 manifesting.
- **Upload or corpus input** — stage one report or a searchable company/year batch.
- **Adaptive concurrency** — shared rate-limit feedback, `Retry-After` handling and gradual recovery.
- **English and Japanese** — locale-aware navigation, result tables and exports.
- **Private visit reporting** — bounded Upstash events and a structured owner-only SES email.
- **Responsive interface** — desktop collapsible rail and mobile navigation drawer.

## How it works

```text
Annual Report PDF
        │
        ▼
Selected local parser
        │  page-marked report representation
        ▼
System prompt + fixed 27-row contract
        │
        ▼
Configured model gateway
        │  JSON response
        ▼
Normalize → Validate → Confidence gate → Reconcile → Score
        │
        ▼
Company / fiscal year / run artifacts
```

The selected parser and OCR policy change between strategies. The report, prompt, model settings, output contract, confidence rule and scoring path remain shared.

### Strategy 1 · no-OCR parser comparison

All four parsers run with OCR disabled. PyPDF calls `page.extract_text()` for every page, normalizes the text, inserts page markers and builds an in-memory prompt. PyMuPDF4LLM, pdf-inspector and Docling use their native non-OCR representations. No pass consults the answer key.

### Strategy 2 · OCR-enabled parser comparison

The report is independently represented by the selected parser passes. OCR is page-adaptive only when the parser exposes a reliable page-level decision boundary; otherwise OCR is compulsory:

| Parser | Strategy 2 OCR policy | Output sent to the shared prompt |
|---|---|---|
| PyPDF | Compulsory | OCR text assembled in page order |
| PyMuPDF4LLM | Adaptive | Layout-aware Markdown with integrated OCR fallback |
| pdf-inspector | Adaptive | Per-page classification; native Rust extraction for text pages; OCR-needed pages rendered at exactly 200 DPI, processed locally by RapidOCR PP-OCRv6 ONNX, then assembled as page-ordered text |
| Docling | Compulsory | OCR-backed ML document graph exported as Markdown |

Each pass gets its own provider response, validation result, timing and persisted run, making the comparison inspectable rather than inferred.

### Strategy 3 · pdf-inspector intelligent scanning gate

Strategy 3 is active and uses pdf-inspector as the finalized parser. `detect_pdf` records document type, confidence, encoding health and OCR routing; `extract_pages_markdown` supplies complete page Markdown plus table, column, complexity and per-page OCR metadata. Pages marked for OCR are rendered at 200 DPI and replaced in place with text produced locally by RapidOCR PP-OCRv6 ONNX. The resulting unified page sequence is scored deterministically using BM25-style schema vocabulary, financial headings, table presence, column/layout signals, numeric density and bounded boilerplate penalties. Only the top three to five complete pages—preserving their original PDF page numbers and order—enter the existing semantic-mapping call.

PDF-Inspector decides native text versus OCR; Ledger's deterministic gate scores complete pages for schema relevance; the configured LLM maps the selected evidence packet to JSON; Pydantic validation and arithmetic reconciliation then verify the response. Diagnostics store every selected page, score component, OCR provenance and Markdown-character reduction. See [ROADMAP.md](ROADMAP.md).

## Quality contract

```text
model JSON
  → normalize representation-only defects
  → validate the exact Pydantic contract
  → reject contract-invalid model output without changing the experiment request
  → flag confidence < 0.80 for review without suppressing its value
  → check deterministic balance-sheet identities
  → score only when an authoritative or SHA-bound human-approved golden set exists
```

The answer key is never model input. A low-confidence value remains visible, is checked arithmetically, and is prioritized for review; confidence does not decide correctness. The assignment-provided 3M FY2022 table is the only built-in assignment key. Separately maintained review fixtures bind gold to the exact PDF SHA-256, legal entity, fiscal year and currency. Condensed statutory disclosures score only directly supported rows and explicitly mark every unavailable schema row unscorable. Ordinary model-mapped candidates remain unverified until a reviewer checks them against the pinned source and approves them. Human review never starts from a blank form: Ledger first runs the configured LLM semantic mapping and prefills the complete schema, shows the searchable pinned PDF beside the table, and lets the reviewer correct the provisional values before Save & Approve.

| Metric | Meaning |
|---|---|
| Exact accuracy | Share of golden rows whose returned values are correct |
| Field coverage | Share of 27 rows for which the model returned a value |
| Precision | Share of returned, comparable values that are correct |
| Consistency | Share of testable arithmetic identities that hold |

## Annual Report corpus

The cloud corpus is frozen for benchmarking: 75 SHA-pinned reports across 34 companies (FY2020–FY2025), every one gold-backed by either the assignment key, a human audit, or a dual-pass derived answer sheet. After removing one complete six-document company cohort, the fresh Gemini 3.7 Flash Strategy 3 predictions recalculate to 100% document-macro and 100% row-micro exact accuracy (1,099/1,099 scored rows), with all 75 retained documents exact. The public UI shows the library and lets users select stored reports for extraction. Dataset PDFs and the manifest live only on persistent cloud storage; they are ignored by Git and are not bundled with the repository.

```text
corpus_dataset/
└── <company>/
    └── <year>/
        └── <company>_annual_report_<year>.pdf
```

The cloud manifest records provenance, review state and SHA-256 identities. Set `LEDGER_CORPUS_ROOT` to that persistent directory in the backend environment. Opening **Review answers** runs one configured-LLM semantic-mapping pass over the pinned PDF and displays its 27 provisional rows beside the searchable source. A failed mapping shows Retry rather than an empty manual-entry table. Candidate answers are never promoted to gold automatically.

## Tech stack

| Layer | Technology |
|---|---|
| Web client | React 19, TypeScript, Vite, Framer Motion, Recharts |
| API | Flask, Gunicorn, Server-Sent Events |
| PDF parsing | PyPDF, PyMuPDF4LLM, pdf-inspector, Docling |
| Validation | Pydantic plus deterministic normalization/reconciliation |
| Model gateways | OpenRouter, OpenAI and custom OpenAI-compatible endpoints |
| Corpus discovery | Firecrawl v2 |
| Frontend hosting | Vercel |
| Backend hosting | AWS EC2, Caddy, Systems Manager |
| Private telemetry | Upstash Redis REST, AWS SES |

## Project structure

```text
frontend/                React application and public brand assets
corpus/                  discovery, download, screening and manifest services
deploy/aws/              EC2 bootstrap and HTTPS configuration
docs/CURRENT_STATUS.md   code-backed architecture and extraction report
ROADMAP.md               Strategy 3 design and acceptance contract
intelligent_scan.py      deterministic complete-page scoring and selection
extraction.py            parser implementations
prompts.py               shared prompt assembly
models.py                exact output contract
normalize.py             recorded representation repair
reconcile.py             deterministic accounting checks
pipeline.py              end-to-end extraction and persistence
api_client.py            provider calls, retry and cache accounting
server.py                Flask API and SSE routes
traffic.py               private visit log and HTML email notification
pyproject.toml            Ruff, mypy, pytest and coverage policy
scripts/verify_project.sh one-command local quality gate
```

## Getting started

Requires Python 3.11+ and Node.js 20+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

npm --prefix frontend ci
npm --prefix frontend run build
python server.py
```

Open `http://localhost:5000`.

For React development with Flask running separately:

```bash
npm --prefix frontend run dev
```

Copy `.env.example` to `.env`, then use **Settings** to test and save the provider and Firecrawl credentials. Saved keys remain server-side and are never returned to the browser or written into run artifacts.

## Verification

```bash
scripts/verify_project.sh
```

The gate runs Ruff lint/format, mypy, 118 backend unit tests, the standalone
contract checks, pip-audit, Bandit (medium/high), 31 Vitest checks, TypeScript,
npm audit, and a production Vite build.

## Deployment

The Vite frontend is deployed on Vercel. Native parsers, long SSE requests and persistent artifacts run on a Tokyo EC2 instance behind Caddy HTTPS.

Set the API origin before the production frontend build:

```bash
vercel env add VITE_API_BASE_URL production
vercel --prod
```

The assignment API has no browser access token. CORS limits approved browser origins, but it is not user authentication. Model and Firecrawl credentials remain only in the backend environment.

## Documentation

- [Current architecture and detailed extraction status](docs/CURRENT_STATUS.md)
- [Agent-maintained architecture index](agent/agent.md)

## Security

Do not commit `.env`, downloaded reports or run artifacts. Provider, Firecrawl, Upstash and email credentials are backend-only. Credential status never reveals key fragments. Uploads must be real PDFs, are bounded per workspace, and expire after two hours; failed staging is removed immediately. Responses set CSP, frame-denial, MIME-sniffing and referrer protections. Visit notifications use a fixed verified recipient; browser input cannot choose a destination or read connector settings.

## License

Built as a technical assignment and benchmark prototype. Add an explicit license before third-party reuse.

---

<p align="center">
  Built by <a href="https://www.mohamedfuad.com/">Mohamed Fuad</a>
</p>
