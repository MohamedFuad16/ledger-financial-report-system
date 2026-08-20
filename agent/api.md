# API & external connectors

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Public service/region health probe |
| GET/POST | `/api/settings` | Read or test-and-save provider settings |
| POST | `/api/runtime-settings` | Verify Firecrawl, then save its credential and the global adaptive request ceiling |
| GET/POST/DELETE | `/api/prompt` | Manage the extraction system prompt |
| GET | `/api/strategies` | List registered parser strategies |
| POST | `/api/uploads` | Stage PDFs and return a preflight plan |
| POST | `/api/extract` | Run a single synchronous extraction |
| POST | `/api/extract/stream` | Stream batch progress as SSE |
| GET | `/api/runs` | List stored predictions |
| GET/DELETE | `/api/runs/<run_id>` | Read or remove one run |
| GET/POST | `/api/golden/<year>` | Read or save local benchmark values |
| GET | `/api/schema` | Return the canonical 27-row schema |
| GET | `/api/corpus` | Read the pinned local corpus manifest and screening summary |
| POST | `/api/corpus/jobs` | Start a background company/year discovery and download job |
| GET | `/api/corpus/jobs/<job_id>` | Poll background corpus job events and results |
| GET | `/api/bakuraku/customers` | Return the 112-company evidence-backed research seed list |

In hosted environments, every non-GET `/api/*` request requires the
`X-Ledger-Admin-Token` header. Browser preflight is allowed only for configured
`CORS_ALLOWED_ORIGINS`; local development remains unprotected when
`LEDGER_ADMIN_TOKEN` is unset.

## External services

OpenAI-compatible chat-completions providers configured in `providers.py`:
OpenRouter, OpenAI, Z.AI, Z.AI Coding, or a custom endpoint. Authentication uses
an API key from local environment settings. No credentials belong in this file.

Firecrawl v2 map/search is used only for link discovery. Candidate PDFs are
downloaded directly, validated, hashed and screened locally; crawling never
starts an LLM extraction automatically. Runtime credential verification uses
`GET /v2/team/credit-usage`, which authenticates without starting a crawl.
