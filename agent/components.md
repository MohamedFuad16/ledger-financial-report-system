# Components / modules

## Pipeline and extraction

- `pipeline.py` — end-to-end orchestration and run persistence; depends on all contract, extraction, and provider modules.
- `extraction.py` — parser strategy registry and text-health diagnostics.
- `api_client.py` — provider request/retry, context-preserving repair payloads, separate attempt artifacts, and reply parsing.
- `providers.py`, `ratelimit.py` — provider-specific payloads, cache metrics, concurrency, and backoff.
- `corpus/` — Firecrawl discovery, ranked report fallback, direct PDF download, screening, model-candidate persistence, on-demand review prefill, and manifest persistence.
- `corpus_worker.py` — CSV/JSON command-line runner for the corpus service.

## Contract and quality

- `schema.py` — canonical taxonomy, subtotal identities, and golden answers.
- `normalize.py` — explicit, reported representation repair.
- `models.py` — strict Pydantic output contract.
- `reconcile.py` — non-mutating subtotal checks.

## Delivery surfaces

- `server.py` — Flask routes, SSE streaming, and static/client delivery.
- `traffic.py` — backend-only Upstash persistence, session deduplication, and escaped text/HTML-table AWS SES notification delivery.
- `frontend/src/App.tsx` — route, data, theme, persisted sidebar-collapse, Strategy-1-first keyboard-command coordination, and one private visit report per browser session.
- `frontend/src/lib/i18n.tsx` — browser-locale detection, persisted English/Japanese selection, shared interface translation, and canonical schema/result-value localization.
- `frontend/src/pages/` — dashboard, two live extraction strategies, the planned Strategy 3 specification, history, corpus (including confirmed deletion and a searchable embedded-PDF answer-review workspace), schema, and settings.
- `frontend/src/components/` — bilingual collapsible sidebar, connected distinct-color quadrant/relative-speed/coverage charts, RareUI-derived folder uploader, searchable single/batch `CorpusPicker`, selectable row-local run tables/result sheets, BeautifulUI-derived neutral execution capsules, and shared UI primitives.
- `frontend/src/editor-theme.css` — final visual mapping from the user's Resume/editor application; loaded after the legacy stylesheet.
- `frontend/public/favicon.png`, `frontend/public/ledger-icon.png` — transparent favicon and high-resolution app-icon assets generated for Ledger.
- `frontend/public/providers/` — locally served official OpenRouter, Z.AI and OpenAI marks used by the model-gateway selector.
- `frontend/src/lib/api.ts` — typed HTTP and fragmented-SSE adapter.
- `app.py` — legacy Streamlit wrapper.

## Verification

- `test_contract.py` — offline contract and pipeline invariants.
- `test_traffic.py` — private traffic storage, deduplication, credential exclusion, and origin-policy checks.
- `test_corpus_manifest.py` — corpus deletion is manifest-ID-only, remains constrained to corpus storage, and never removes prior run output.
- `frontend/src/lib/api.test.ts` — client request/SSE parsing regression tests.
- `frontend/src/components/ExecutionPipeline.test.tsx` — live/idle task-row rendering and streamed-status regression tests.
- `frontend/src/components/CorpusPicker.test.tsx` — corpus filtering and single/batch selection regression tests.
- `frontend/src/lib/i18n.test.ts` — canonical schema/result localization regression tests.
- `runs/` — historical artifacts used for empirical comparison.
