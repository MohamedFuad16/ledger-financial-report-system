# API & external connectors

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Public service/region health probe |
| POST | `/api/traffic` | Record one deduplicated browser-session visit in private Upstash storage and queue an owner-only SES email |
| GET/POST | `/api/settings` | Read or test-and-save provider settings |
| POST | `/api/runtime-settings` | Verify Firecrawl, then save its credential and the global adaptive request ceiling |
| GET/POST/DELETE | `/api/prompt` | Manage the extraction system prompt |
| GET | `/api/strategies` | List registered parser strategies |
| POST | `/api/uploads` | Stage PDFs and return a preflight plan |
| POST | `/api/extract` | Run a single synchronous extraction |
| POST | `/api/extract/stream` | Stream batch progress as SSE |
| GET/POST | `/api/extraction/jobs` | List or start backend-owned, browser-rehydratable extraction batches |
| GET | `/api/extraction/jobs/<job_id>` | Poll persisted job state and replay unseen execution events by offset |
| GET | `/api/runs` | List stored predictions |
| GET/DELETE | `/api/runs/<run_id>` | Read or remove one run |
| GET/POST | `/api/golden/<year>` | Read or save local benchmark values |
| GET | `/api/schema` | Return the canonical 27-row schema |
| GET | `/api/corpus` | Read the pinned local corpus manifest and screening summary |
| DELETE | `/api/corpus/<sha256>` | Delete one manifest-owned corpus PDF after an explicit client confirmation; extraction runs remain intact |
| POST | `/api/corpus/stage` | Validate selected SHA-256 corpus entries and stage their durable PDFs for the normal extraction stream |
| POST | `/api/corpus/jobs` | Start a background company/year discovery and download job |
| GET | `/api/corpus/jobs/<job_id>` | Poll background corpus job events and results |
| GET | `/api/bakuraku/customers` | Return the 112-company evidence-backed research seed list |

The assignment API has no browser access-token layer. Browser preflight is
allowed only for configured `CORS_ALLOWED_ORIGINS`, while the traffic endpoint
also enforces the configured production origins, accepts a small metadata-only
JSON body, and never returns connector details. CORS is not authentication:
direct API callers can still reach mutation routes, so this boundary must be
revisited before a multi-tenant or quota-bearing public product launch.

## External services

OpenAI-compatible chat-completions providers configured in `providers.py`:
OpenRouter, OpenAI, Z.AI, Z.AI Coding, or a custom endpoint. Authentication uses
an API key from local environment settings. No credentials belong in this file.

Firecrawl v2 map/search is used only for link discovery. Candidate PDFs are
downloaded directly, validated, hashed and screened locally; crawling never
starts an LLM extraction automatically. Runtime credential verification uses
`GET /v2/team/credit-usage`, which authenticates without starting a crawl.

Upstash Redis stores a bounded private visit log and aggregate counters. AWS
SES v2 sends one notification to the verified owner identity for each new
browser session. Both connectors run only in Flask; their credentials are not
part of the Vite environment or bundle.
