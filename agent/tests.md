# Tests

## Strategy

- `test_contract.py` is an offline executable suite covering schema, normalization, validation, parsing, extraction health, rate limiting, reconciliation, providers, and run layout.
- `test_traffic.py` verifies Redis event shape, credential exclusion, session deduplication, hosted-origin enforcement, structured HTML email escaping, and that corpus staging no longer depends on a deployment token.
- Vitest covers the typed API adapter and fragmented SSE parsing boundary.
- `test_corpus_review.py` verifies that review extraction is required before editing, reuses an existing prefill, and fails closed instead of returning a blank manual table.
- `test_intelligent_scan.py` verifies complete-page scoring, three-to-five-page selection, pdf-inspector OCR routing, 200-DPI page replacement and Strategy 3 diagnostics.
- `test_workspace_isolation.py` verifies workspace-scoped run listing and bulk deletion plus invalid-header fallback.
- `test_extraction_jobs.py` verifies durable job rehydration and proves three independent workspaces share two parser/OCR slots, never exceed that limit, remain isolated and all complete.
- `frontend/src/pages/CorpusPage.test.tsx` verifies automatic PDF prefill, reviewer correction, confirmation/save/approval, and the extraction retry state.
- Browser QA must cover the dashboard, each live strategy, uploads, settings, run detail, responsive layout, and console errors. The pipeline component regression must prove one card per report and an animated transition between parser passes without duplicating a report card.

## Commands

```bash
scripts/verify_project.sh
```

## Current baseline

The standalone extraction contract (108 checks), 132 backend `unittest` checks, 32 Vitest checks, Ruff,
mypy, Bandit, `pip-audit`, `npm audit`, TypeScript and the production Vite build passed on 2026-08-28. The batch regression proves two different-company
PDFs stay visible together as separate running/queued cards, and the arithmetic regression proves
one null identity term is derived without mutating the model response or consulting gold. The newest browser pass covers the active Strategy 3
desktop execution page plus the Japanese dark-theme
extracted-answer review at desktop and 390×844 plus the two-strategy-only dashboard:
embedded pinned PDF, 27 prefilled rows, responsive scrolling, immutable assignment
values, cleaned navigation/dashboard scope, and zero console warnings.
Automated review tests cover extraction-before-input, correction, confirmation,
approval, retry, consensus artifacts, anonymous-workspace run isolation, PDF magic-byte rejection,
staging expiry, non-object JSON rejection, key-fragment exclusion and browser security headers. No
paid model or Firecrawl extraction was launched during this verification. A dedicated concurrency regression
also stages three jobs under three workspace IDs, observes exactly two simultaneous pipeline entries, and
confirms the queued third job completes without cross-workspace state leakage.
