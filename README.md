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
</p>

---

## Overview

Ledger is a bilingual Annual Report benchmark workspace. It converts a PDF into a fixed 27-row asset-side balance-sheet contract, calls an OpenAI-compatible model for semantic mapping, validates the result, applies a measured confidence gate and benchmarks it against maintained golden answers.

The current assignment uses 3M reports as the initial benchmark, while the corpus pipeline is company-independent and supports official FY2020–FY2025 reports.

## Features

- **Two controlled extraction strategies** — the same four selectable parsers without OCR (Strategy 1) and with OCR (Strategy 2).
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

The same report is independently represented by the selected parser passes. OCR is page-adaptive only when the parser exposes a reliable page-level decision boundary; otherwise OCR is compulsory:

| Parser | Strategy 2 OCR policy | Output sent to the shared prompt |
|---|---|---|
| PyPDF | Compulsory | OCR text assembled in page order |
| PyMuPDF4LLM | Adaptive | Layout-aware Markdown with integrated OCR fallback |
| pdf-inspector | Adaptive | Per-page classification; native Rust extraction for text pages; OCR-needed pages rendered at exactly 200 DPI, processed by neural layout detection and GLM-OCR/VLM, then assembled as page-ordered Markdown |
| Docling | Compulsory | OCR-backed ML document graph exported as Markdown |

Each pass gets its own provider response, validation result, timing and persisted run, making the comparison inspectable rather than inferred.

## Quality contract

```text
model JSON
  → normalize representation-only defects
  → validate the exact Pydantic contract
  → reject contract-invalid model output without changing the experiment request
  → mark confidence < 0.80 as unaccepted
  → check deterministic balance-sheet identities
  → score only when an authoritative or SHA-bound human-approved golden set exists
```

The answer key is never model input. A low-confidence value stays in the audit artifact but is displayed and scored as unanswered. The assignment-provided 3M FY2022 table is the only built-in authoritative golden set. Firecrawl-generated candidate answers for every other report remain unverified until a reviewer checks all 27 rows against the original PDF and approves them; the approval is bound to that exact PDF SHA-256. Human review never starts from a blank form: Ledger first extracts and prefills the complete schema, shows the pinned PDF beside the table, and lets the reviewer correct the provisional values before Save & Approve.

| Metric | Meaning |
|---|---|
| Exact accuracy | Share of golden rows that are both correct and accepted |
| Field coverage | Share of 27 rows returned with accepted confidence |
| Precision | Share of accepted, comparable rows that are correct |
| Consistency | Share of testable arithmetic identities that hold |

## Annual Report corpus

The corpus builder discovers reports only for FY2020–FY2025. Firecrawl finds candidate official URLs; Ledger downloads the PDF directly, verifies and screens it, then stores it as:

```text
corpus_dataset/
└── <company>/
    └── <year>/
        └── <company>_annual_report_<year>.pdf
```

`corpus_dataset/corpus_manifest.json` records provenance, review state and SHA-256 identities. A successful recrawl atomically replaces the canonical company/year PDF; a failed download or screening pass leaves the previous file intact. The worker persists the PDF first, then asks Firecrawl for three uncached structured extraction passes and stores their provisional consensus with explicit agreement metadata. If a legacy pinned PDF has no candidate artifact, opening **Review extracted answers** runs the same extraction before displaying editable fields; a failed extraction shows Retry rather than an empty manual-entry table. Candidate answers are never promoted to gold automatically. Unverified reports may still be used for extraction with a visible warning, but they do not receive an exact-accuracy score.

The standalone worker accepts a CSV or JSON company list:

```bash
.venv/bin/python corpus_worker.py research/bakuraku/customers.csv \
  --years 2020 2021 2022 2023 2024 2025
```

## Tech stack

| Layer | Technology |
|---|---|
| Web client | React 19, TypeScript, Vite, Framer Motion, Recharts |
| API | Flask, Gunicorn, Server-Sent Events |
| PDF parsing | PyPDF, PyMuPDF4LLM, pdf-inspector, Docling |
| Validation | Pydantic plus deterministic normalization/reconciliation |
| Model gateways | OpenRouter, Z.AI, OpenAI and custom OpenAI-compatible endpoints |
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
research/bakuraku/       evidence-backed corpus seed companies
extraction.py            parser implementations
prompts.py               shared prompt assembly
models.py                exact output contract
normalize.py             recorded representation repair
reconcile.py             deterministic accounting checks
pipeline.py              end-to-end extraction and persistence
api_client.py            provider calls, retry and cache accounting
server.py                Flask API and SSE routes
traffic.py               private visit log and HTML email notification
```

## Getting started

Requires Python 3.11+ and Node.js 20+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

npm --prefix frontend install
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
.venv/bin/python test_contract.py
.venv/bin/python -m unittest test_traffic.py test_corpus_manifest.py
npm --prefix frontend test
npm --prefix frontend run build
```

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
- [Evaluation dataset notes](test_dataset/README.md)
- [Agent-maintained architecture index](agent/agent.md)

## Security

Do not commit `.env`, downloaded reports or run artifacts. Provider, Firecrawl, Upstash and email credentials are backend-only. Visit notifications use a fixed verified recipient; browser input cannot choose a destination or retrieve connector settings.

## License

Built as a technical assignment and benchmark prototype. Add an explicit license before third-party reuse.

---

<p align="center">
  Built by <a href="https://www.mohamedfuad.com/">Mohamed Fuad</a>
</p>
