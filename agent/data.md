# Data

## Core models

- `AssetRow` — canonical item, value in M USD, confidence, provenance, and schema-derived descriptive fields.
- `ExtractionResult` — detected fiscal year plus exactly 27 ordered rows.
- Prediction artifact — run metadata, strategy/parser identity, accepted rows, repairs, reconciliation, metrics, usage, and timing.

## Storage

- New uploaded PDFs: `uploads/<company>/<year>/<timestamp>/<company>_annual_report_<year>.pdf`; historical flat uploads are retained.
- New runs: `runs/<company>/FY<year>/<run_id>/` containing `request.json`, `raw_response.json`, and `prediction.json`; a bounded contract repair adds `request_repair_1.json` and `raw_response_repair_1.json` without overwriting the first attempt. Readers remain backward-compatible with legacy strategy-first folders.
- Pending runs: `runs/<strategy>/_pending/` until fiscal year is known.
- Corpus PDFs: `corpus_dataset/<company>/<year>/<downloaded_at>/<company>_annual_report_<year>.pdf`.
- Corpus manifest: `corpus_dataset/corpus_manifest.json`, deduplicated by SHA-256 and company/year.
- Corpus selections are staged by durable file reference rather than copied; extraction outputs remain under `runs/<company>/FY<year>/<run_id>/` and `/api/corpus` reports that output directory and its completed-run count.
- Bakuraku research: `research/bakuraku/customers.csv` plus a fully linked `README.md` table.
- Provider defaults: `.env` (gitignored).
- Visit telemetry: Upstash keys `ledger:traffic:visits` (bounded to the newest
  2,000 metadata events), `ledger:traffic:count`, `ledger:traffic:daily`, and
  six-hour hashed `ledger:traffic:session:*` deduplication markers. Stored event
  fields are access time, path, referrer, client IP, locale, time zone, viewport,
  user agent, and event ID; connector credentials are never serialized.

## Client state

The React client keeps server data in typed hooks and reserves local state for selection, filters, upload/corpus input mode, per-stage execution progress/timing, and background-corpus polling. A random session ID in `sessionStorage` deduplicates visit reporting per browser tab session. English schema keys remain the stored contract; Japanese labels are a presentation-only mapping so persisted artifacts stay stable.
