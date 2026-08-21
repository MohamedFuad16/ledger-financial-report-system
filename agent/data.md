# Data

## Core models

- `AssetRow` — canonical item, value in M USD, confidence, provenance, and schema-derived descriptive fields.
- `ExtractionResult` — detected fiscal year plus exactly 27 ordered rows.
- Prediction artifact — run metadata, strategy/parser identity, accepted rows, repairs, reconciliation, metrics, usage, and timing.

## Storage

- New uploaded PDFs: `uploads/<company>/<year>/<timestamp>/<company>_annual_report_<year>.pdf`. The superseded flat upload cache was removed after confirming no manifest or run referenced it.
- New runs: `runs/<company>/FY<year>/<run_id>/` containing `request.json`, `raw_response.json`, and `prediction.json`; a bounded contract repair adds `request_repair_1.json` and `raw_response_repair_1.json` without overwriting the first attempt. Readers remain backward-compatible with legacy strategy-first folders.
- Pending runs: `runs/<strategy>/_pending/` until fiscal year is known.
- Corpus PDFs: `corpus_dataset/<company>/<year>/<company>_annual_report_<year>.pdf`. A successful company/year recrawl atomically replaces this canonical file; failed replacements preserve the previously verified PDF.
- Corpus manifest: `corpus_dataset/corpus_manifest.json`, deduplicated by SHA-256 and company/year.
- Corpus review artifacts: `verification/candidate_pass_<n>.json` retains each uncached Firecrawl pass, `candidate_answers.json` stores the provisional consensus/agreement metadata, and `approved_answers.json` stores only a human-approved table bound to the current PDF SHA-256.
- Corpus discovery jobs: `runs/_corpus_jobs/<job-id>/state.json`; active and terminal events are atomically snapshotted so a new route or browser session can rehydrate progress. An active snapshot owned by a prior backend process is retained as `interrupted` after restart rather than disappearing.
- Corpus selections are staged by durable file reference rather than copied; extraction outputs remain under `runs/<company>/FY<year>/<run_id>/` and `/api/corpus` reports that output directory and its completed-run count.
- Deleting a pinned corpus entry removes only its manifest-owned PDF and empty company/year folders; existing run artifacts are preserved.
- The current verified seed is the official 3M FY2022 filing at `corpus_dataset/3M/2022/3M_annual_report_2022.pdf` (`d5cf549543a2…`), screened `ok` with 252/252 readable pages and staged in production by manifest identity.
- Bakuraku research: `research/bakuraku/customers.csv` plus a fully linked `README.md` table.
- Provider defaults: `.env` (gitignored).
- Visit telemetry: Upstash keys `ledger:traffic:visits` (bounded to the newest
  2,000 metadata events), `ledger:traffic:count`, `ledger:traffic:daily`, and
  six-hour hashed `ledger:traffic:session:*` deduplication markers. Stored event
  fields are access time, path, referrer, client IP, locale, time zone, viewport,
  user agent, and event ID; connector credentials are never serialized.

## Client state

The React client keeps server data in typed hooks and reserves local state for selection, filters, upload/corpus input mode, per-stage execution progress/timing, and background-corpus polling. Corpus and extraction jobs are rehydrated from backend snapshots rather than treating route-local React state as their owner. A random stable workspace ID in `localStorage` scopes staged files, extraction jobs, run reads and run deletion to one anonymous browser profile; it is an isolation hint, not authentication. A separate random session ID in `sessionStorage` deduplicates visit reporting per browser tab session. English schema keys remain the stored contract; Japanese labels are a presentation-only mapping so persisted artifacts stay stable.
