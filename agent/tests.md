# Tests

## Strategy

- `test_contract.py` is an offline executable suite covering schema, normalization, validation, parsing, extraction health, rate limiting, reconciliation, providers, and run layout.
- `test_traffic.py` verifies Redis event shape, credential exclusion, session deduplication, hosted-origin enforcement, structured HTML email escaping, and that corpus staging no longer depends on a deployment token.
- Vitest covers the typed API adapter and fragmented SSE parsing boundary.
- `test_corpus_review.py` verifies that review extraction is required before editing, reuses an existing prefill, and fails closed instead of returning a blank manual table.
- `test_workspace_isolation.py` verifies workspace-scoped run listing and bulk deletion plus invalid-header fallback.
- `frontend/src/pages/CorpusPage.test.tsx` verifies automatic PDF prefill, reviewer correction, confirmation/save/approval, and the extraction retry state.
- Browser QA must cover the dashboard, each live strategy, uploads, settings, run detail, responsive layout, and console errors. The pipeline component regression must prove one card per report and an animated transition between parser passes without duplicating a report card.

## Commands

```bash
.venv/bin/python test_contract.py
.venv/bin/python test_traffic.py
.venv/bin/python test_corpus_manifest.py
.venv/bin/python test_corpus_review.py
.venv/bin/python test_workspace_isolation.py
cd frontend && npm test -- --run && npm run build
```

## Current baseline

The full extraction contract, 41 unittest cases, 17 Vitest checks, production
TypeScript/Vite build, Python compile checks, and in-app browser visual/DOM sweep
passed on 2026-08-22. The newest browser pass covers the Japanese dark-theme
extracted-answer review at desktop and 390×844: embedded pinned PDF, 27 prefilled
rows, responsive scrolling, immutable assignment values, and zero console warnings.
Automated review tests cover extraction-before-input, correction, confirmation,
approval, retry, consensus artifacts and anonymous-workspace run isolation. No
paid model or Firecrawl extraction was launched during this verification.
