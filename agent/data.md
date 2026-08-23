# Data

## Core models

- `AssetRow` — canonical item, value in millions of the run's declared source currency, confidence, provenance, and schema-derived descriptive fields. The legacy JSON field name remains `answer_m_usd` for stored-artifact compatibility.
- `ExtractionResult` — detected fiscal year plus exactly 27 ordered rows.
- Prediction artifact — run metadata, strategy/parser identity, accepted rows, repairs, reconciliation, metrics, usage, and timing.

## Storage

- New uploaded PDFs: `uploads/<company>/<year>/<timestamp>/<company>_annual_report_<year>.pdf`. The superseded flat upload cache was removed after confirming no manifest or run referenced it.
- New runs: `runs/<company>/FY<year>/<run_id>/` containing `request.json`, `raw_response.json`, and `prediction.json`; a bounded contract repair adds `request_repair_1.json` and `raw_response_repair_1.json` without overwriting the first attempt. Readers remain backward-compatible with legacy strategy-first folders.
- Pending runs: `runs/<strategy>/_pending/` until fiscal year is known.
- Corpus PDFs: `corpus_dataset/<company>/<year>/<company>_annual_report_<year>.pdf`. A successful company/year recrawl atomically replaces this canonical file; failed replacements preserve the previously verified PDF.
- Corpus manifest: `corpus_dataset/corpus_manifest.json`, deduplicated by SHA-256 and company/year.
- Corpus review artifacts: `verification/candidate_pass_<n>.json` retains source-bound provisional mapping passes, `candidate_answers.json` stores the current configured-LLM candidate table, and `approved_answers.json` stores only a human-approved table bound to the current PDF SHA-256. Legacy Firecrawl pass files remain readable until the next review replaces them.
- Corpus discovery jobs: `runs/_corpus_jobs/<job-id>/state.json`; active and terminal events are atomically snapshotted so a new route or browser session can rehydrate progress. An active snapshot owned by a prior backend process is retained as `interrupted` after restart rather than disappearing.
- Corpus selections are staged by durable file reference rather than copied; extraction outputs remain under `runs/<company>/FY<year>/<run_id>/` and `/api/corpus` reports that output directory and its completed-run count.
- Deleting a pinned corpus entry removes only its manifest-owned PDF and empty company/year folders; existing run artifacts are preserved.
- Verified benchmark sources include the official 3M FY2022 filing, the existing Bakuraku-client annual-report cohorts, and 27 exact-entity public-gazette balance sheets in `benchmark_data/bakuraku_statutory_gold.json`. Non-assignment gold is bound to exact PDF SHA-256, company, fiscal year and currency through an explicit fixture allowlist. Condensed statutory filings score only directly disclosed and twice-transcribed fields (currently Total Assets); unsupported rows remain explicitly unscorable and every partial fixture partitions all 27 schema rows between answers and omissions.
- Statutory discovery inventories are kept in `research/corpus/firecrawl_statutory_filings.json` and `research/corpus/gazette_statutory_filings.json`. They are research candidates, not gold. `research/benchmark/bakuraku_statutory_gold_audit.json` is the materialization audit that records the exact entity, public source, source-image hash, derived-PDF hash, OCR occurrence count, independent index transcription and balance reconciliation for admitted keys.
- `research/benchmark/forty_client_corpus_audit.json` is the generated completion gate for the client cohort. It proves registry membership, two distinct audit passes, a complete scorable/unscorable 27-row partition, manifest identity, local source existence and exact source-byte SHA-256 for every counted company. 3M is reported separately and never counted toward the forty-client threshold.
- Bakuraku research: `research/bakuraku/customers.csv` plus a fully linked `README.md` table.
- Provider defaults: `.env` (gitignored).
- Visit telemetry: Upstash keys `ledger:traffic:visits` (bounded to the newest
  2,000 metadata events), `ledger:traffic:count`, `ledger:traffic:daily`, and
  six-hour hashed `ledger:traffic:session:*` deduplication markers. Stored event
  fields are access time, path, referrer, client IP, locale, time zone, viewport,
  user agent, and event ID; connector credentials are never serialized.

## Client state

The React client keeps server data in typed hooks and reserves local state for selection, filters, upload/corpus input mode, per-stage execution progress/timing, and background-corpus polling. Corpus and extraction jobs are rehydrated from backend snapshots rather than treating route-local React state as their owner. A random stable workspace ID in `localStorage` scopes staged files, extraction jobs, run reads and run deletion to one anonymous browser profile; it is an isolation hint, not authentication. A separate random session ID in `sessionStorage` deduplicates visit reporting per browser tab session. English schema keys remain the stored contract; Japanese labels are a presentation-only mapping so persisted artifacts stay stable.
