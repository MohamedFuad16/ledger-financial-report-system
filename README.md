<div align="center">

<img src="frontend/public/ledger-icon.png" width="96" alt="Ledger logo" />

# Ledger

**Reads a 100-page annual report, finds the few pages that matter, and returns a checked balance sheet.**

[![Live App](https://img.shields.io/badge/Live-assignment.mohamedfuad.com-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://assignment.mohamedfuad.com)
[![Python](https://img.shields.io/badge/Python_3.11-Flask-3776AB?style=for-the-badge&logo=python&logoColor=white)](#tech-stack)
[![React](https://img.shields.io/badge/React_19-TypeScript-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](#tech-stack)
[![AWS](https://img.shields.io/badge/Backend-AWS_EC2-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white)](#deployment)

<img src="https://raw.githubusercontent.com/MohamedFuad16/portfolio-mine/32d8ec630d54e703e65db9dafb3224bcf7648e3c/public/media/projects/ledger-en.jpg" alt="Ledger overview dashboard with benchmark accuracy, field coverage and extraction strategies" width="100%" />

</div>

---

## Overview

Ledger turns an annual report PDF into the asset side of its balance sheet and
checks the result before it is scored. Annual reports run past a hundred
pages, but the balance sheet is only a few of them. Ledger finds those pages
locally, sends only the best three to five to the model, maps the answer to a
fixed 27-row schema, and checks it arithmetically.

**Live:** <https://assignment.mohamedfuad.com>

It is also a benchmark workspace in English and Japanese. The same report can go
through four PDF parsers, with and without OCR, so every strategy is compared on
the same prompt, model settings, output contract and scoring path.

## Results

From the published Strategy 3 summary (`/api/benchmark-summary`, generated
2026-08-28 from stored run artifacts, Gemini 3.7 Flash):

| Measure | Value |
| ------- | ----- |
| Corpus | 47 annual reports from 10 companies, FY2020 to FY2025 |
| Exact rows | 966 of 966 scored rows (100%) |
| Exact documents | 47 of 47 |
| Field coverage | 100% |

On the 46 reports every strategy processed, the page gate averages 31.0 s and
about 8.9k input tokens per report, against 36.7 s and 92.9k tokens for the
whole report without OCR. A 132-page 3M report shrinks to 5 pages and about
8,500 tokens.

## Features

- **Page gate (Strategy 3)**: pdf-inspector extracts native text and routes only
  broken pages to local OCR. A deterministic scorer then picks the three to five
  complete pages most likely to hold the balance sheet.
- **Parser comparison (Strategies 1 and 2)**: PyPDF, PyMuPDF4LLM, pdf-inspector
  and Docling, each run without OCR and with OCR, individually or together.
- **Fixed output contract**: exactly 27 canonical rows, normalized and validated
  with Pydantic, then checked against balance-sheet identities.
- **Separate metrics**: exact accuracy, field coverage, precision and
  consistency are reported apart, and low-confidence values are flagged for
  review, never hidden.
- **Pinned gold answers**: gold values are bound to each PDF by SHA-256 and
  never reach the model.
- **Official-report corpus**: Firecrawl discovery, direct PDF download, health
  screening and a SHA-256 manifest.
- **Live execution**: Server-Sent Events drive each timed task in the UI.
- **Adaptive concurrency**: shared rate-limit feedback, `Retry-After` handling
  and gradual recovery.
- **English and Japanese**: locale-aware navigation, result tables and exports.
- **Private visit reporting**: bounded Upstash events and an owner-only SES
  email.

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

The published corpus holds 47 SHA-pinned reports from 10 companies (3M and nine
Japanese companies), covering FY2020 to FY2025, and all 47 are marked
verified. The public UI shows the library and lets users select stored reports
for extraction. Dataset PDFs and the manifest live only on persistent cloud
storage; they are ignored by Git and are not bundled with the repository.

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

Open the URL the server prints, normally `http://127.0.0.1:5000`. If port 5000 is
taken (macOS AirPlay Receiver often holds it), the server falls back to 5001,
5050, 8000 or 8080, or you can set `PORT`.

For React development with Flask running separately:

```bash
npm --prefix frontend run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` and proxies `/api` to
`http://127.0.0.1:5000`, so run Flask on port 5000 in this mode.

Copy `.env.example` to `.env`, then use **Settings** to test and save the provider and Firecrawl credentials. Saved keys remain server-side and are never returned to the browser or written into run artifacts.

## Verification

```bash
scripts/verify_project.sh
```

The gate runs Ruff lint and format checks, mypy, the backend unit tests, the
standalone contract checks, pip-audit, Bandit (medium and high), the Vitest
suite, the TypeScript check, npm audit and a production Vite build.

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

<div align="center">
Built by <a href="https://github.com/MohamedFuad16">Mohamed Fuad</a> · <a href="https://www.mohamedfuad.com">mohamedfuad.com</a>
</div>
