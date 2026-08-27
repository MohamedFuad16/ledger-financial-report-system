# Components / modules

## Pipeline and extraction

- `pipeline.py` — end-to-end orchestration and run persistence; depends on all contract, extraction, and provider modules.
- `extraction.py` — parser strategy registry and text-health diagnostics.
- `intelligent_scan.py` — Strategy 3 BM25-style complete-page scoring using the 27-field vocabulary and pdf-inspector layout metadata, plus `select_retry_pages` for the bounded evidence-retry pass over unsent ranked pages.
- `api_client.py` — provider request/retry, context-preserving repair payloads, separate attempt artifacts, and reply parsing.
- `providers.py`, `ratelimit.py` — provider-specific payloads, cache metrics, concurrency, and backoff.
- `corpus/` — Firecrawl discovery, ranked report fallback, direct PDF download, screening, model-candidate persistence, on-demand review prefill, and manifest persistence.

## Contract and quality

- `schema.py` — canonical taxonomy, subtotal identities, and golden answers.
- `normalize.py` — explicit, reported representation repair.
- `models.py` — strict Pydantic output contract.
- `reconcile.py` — auditable single-missing-term identity completion plus non-overwriting subtotal checks.

## Delivery surfaces

- `server.py` — Flask routes, SSE streaming, and static/client delivery.
- `traffic.py` — backend-only Upstash persistence, session deduplication, and escaped text/HTML-table AWS SES notification delivery.
- `frontend/src/App.tsx` — route, data, theme, persisted sidebar-collapse, Strategy-1-first keyboard-command coordination, and one private visit report per browser session.
- `frontend/src/lib/i18n.tsx` — browser-locale detection, persisted English/Japanese selection, shared interface translation, and canonical schema/result-value localization.
- `frontend/src/lib/currency.ts` — persisted USD/JPY display preference and reversible display-only conversion; native filing values remain unchanged.
- `frontend/src/pages/` — dashboard (final retained-cohort Strategy 3 headline plus separately labeled historical speed/parser charts), three live extraction strategies, history, corpus (frozen library with Firecrawl provenance explainer and company tile grid, confirmed deletion, and exact-page A4/searchable-PDF answer review — no public discovery controls), schema, and settings (merged GLM endpoint toggle plus wired OpenRouter model selector).
- `frontend/src/components/` — bilingual collapsible sidebar, connected distinct-color quadrant/relative-speed/coverage charts, RareUI-derived folder uploader, searchable single/batch `CorpusPicker`, selectable row-local run tables/result sheets, one persistent live execution card per selected PDF, and shared UI primitives.
- `frontend/src/editor-theme.css` — final visual mapping from the user's Resume/editor application; loaded after the legacy stylesheet.
- `frontend/public/favicon.png`, `frontend/public/ledger-icon.png` — transparent favicon and high-resolution app-icon assets generated for Ledger.
- `frontend/public/providers/` — locally served official OpenRouter and OpenAI marks used by the model-gateway selector.
- `frontend/src/lib/api.ts` — typed HTTP and fragmented-SSE adapter.
- `deploy/aws/restore_verified_corpus.py` — hash-checking recovery tool that restores only assignment or exact-source Bakuraku gold from a corpus backup.

## Verification

- `test_contract.py` — offline contract and pipeline invariants.
- `test_traffic.py` — private traffic storage, deduplication, credential exclusion, and origin-policy checks.
- `test_corpus_manifest.py` — corpus deletion is manifest-ID-only, remains constrained to corpus storage, and never removes prior run output.
- `test_restore_verified_corpus.py` — backup restore rejects hash mismatches and excludes non-Bakuraku benchmark controls.
- `test_audit_regressions.py` — upload, JSON, credential masking, security-header, cache, quota and benchmark-isolation regressions.
- `scripts/verify_project.sh` — Ruff, format, mypy, Python tests, contract checks, Vitest, TypeScript and production build.
- `frontend/src/lib/api.test.ts` — client request/SSE parsing regression tests.
- `frontend/src/components/ExecutionPipeline.test.tsx` — live/idle task-row rendering and streamed-status regression tests.
- `frontend/src/components/CorpusPicker.test.tsx` — corpus filtering and single/batch selection regression tests.
- `frontend/src/lib/i18n.test.ts` — canonical schema/result localization regression tests.
- `runs/` — historical artifacts used for empirical comparison.
