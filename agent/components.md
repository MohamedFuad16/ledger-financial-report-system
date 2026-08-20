# Components / modules

## Pipeline and extraction

- `pipeline.py` — end-to-end orchestration and run persistence; depends on all contract, extraction, and provider modules.
- `extraction.py` — parser strategy registry and text-health diagnostics.
- `api_client.py` — provider request/retry, context-preserving repair payloads, separate attempt artifacts, and reply parsing.
- `providers.py`, `ratelimit.py` — provider-specific payloads, cache metrics, concurrency, and backoff.
- `corpus/` — Firecrawl client/discovery, ranked candidate fallback, direct PDF download, screening, and manifest persistence.
- `corpus_worker.py` — CSV/JSON command-line runner for the corpus service.

## Contract and quality

- `schema.py` — canonical taxonomy, subtotal identities, and golden answers.
- `normalize.py` — explicit, reported representation repair.
- `models.py` — strict Pydantic output contract.
- `reconcile.py` — non-mutating subtotal checks.

## Delivery surfaces

- `server.py` — Flask routes, SSE streaming, and static/client delivery.
- `frontend/src/App.tsx` — route, data, theme, persisted sidebar-collapse, and Strategy-2-first keyboard-command coordination.
- `frontend/src/lib/i18n.tsx` — browser-locale detection, persisted English/Japanese selection, and shared translation helper.
- `frontend/src/pages/` — dashboard, live strategies, history, corpus, schema, settings, and research-roadmap pages.
- `frontend/src/components/` — bilingual collapsible sidebar, connected distinct-color quadrant/relative-speed/coverage charts, RareUI-derived folder uploader, selectable row-local run tables/result sheets, BeautifulUI-derived execution stage capsules, and shared UI primitives.
- `frontend/src/editor-theme.css` — final visual mapping from the user's Resume/editor application; loaded after the legacy stylesheet.
- `frontend/src/lib/api.ts` — typed HTTP and fragmented-SSE adapter.
- `static/` — archived legacy UI; no longer served.
- `app.py` — legacy Streamlit wrapper.

## Verification

- `test_contract.py` — offline contract and pipeline invariants.
- `frontend/src/lib/api.test.ts` — client request/SSE parsing regression tests.
- `frontend/src/components/ExecutionPipeline.test.tsx` — live/idle task-row rendering and streamed-status regression tests.
- `runs/` — historical artifacts used for empirical comparison.
