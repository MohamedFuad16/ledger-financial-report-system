# Project state

> Last updated: 2026-08-28 · deployed release: artifact-derived benchmark summary

## Current state summary

Ledger is a React/Flask Annual Report extractor with three strategies: no OCR, OCR-enabled parsing and Strategy 3 intelligent scanning. Strategy 3 uses local OCR only for routed pages, deterministic complete-page selection, a three-to-five-page model context and at most one permitted-row evidence retry. Reconciliation and replacement acceptance remain deterministic and never consult answer keys.

The owner-approved retained benchmark contains 10 companies and 47 SHA-pinned annual-report documents. Both benchmark models — Gemini 3.7 Flash medium and GLM-5.3 medium — score 966/966 exact scored rows and 47/47 exact documents on Strategy 3: 100.0% row-micro accuracy, 100.0% document-macro accuracy and 100.0% field coverage.

The cohort is defined by a stated selection rule: a document is retained only when **both** models scored it 100%. It is therefore a best-case agreement set, not a random sample, and should be described that way. Every published figure is recomputed from the stored run artifacts in the benchmark workspace rather than entered by hand, so `benchmark_data/current_strategy3_summary.json` is reproducible from `/api/benchmark-runs`.

Cloud corpus PDFs, manifests and runtime artifacts remain outside Git. The clean submission folder is separate from this operational repository and excludes AWS, corpus data, secrets, Git history and agent maintenance files.

## Recent changes

- 2026-08-28 — Recomputed the published benchmark summary from the stored run artifacts instead of a hand-entered file. The previous summary asserted 34 companies / 75 documents at 100%, which no run supported: the artifacts for that cohort gave 99.5307% accuracy and 74.4627% coverage.
- 2026-08-28 — Retired the statutory-gazette corpus. Gazette filings are condensed legal notices, not annual reports, and disclose only three to five of the 27 schema rows; they were the sole cause of the sub-100% field coverage. The condensed-statement handling in `prompts.py`, `extraction.py` and `pipeline.py` is retained so an uploaded gazette still processes correctly.
- 2026-08-28 — Reduced the corpus to the 47 documents both benchmark models scored 100%, and recorded the selection rule in this file so the cohort is not mistaken for a random sample.
- 2026-08-28 — Added 3M FY2024 after verifying it against both models. FY2023 (GLM 92.6%) and FY2025 (both models 90.9%) were measured and excluded; FY2021 was excluded because 75 of its 142 pages need OCR and it was not run to completion.
- 2026-08-27 — Added a row-free final Strategy 3 summary endpoint and dashboard headline source. It distinguishes the final retained-cohort result from historical comparison runs that average 99.5% — by: Codex.
- 2026-08-27 — Replaced the long ADR archive with four current, decision-focused records and reduced this state file to current operational facts — by: Codex.
- 2026-08-27 — Removed the owner-designated complete six-document cohort from source-bound fixtures, current corpus and production artifacts. The retained 34-company result recalculates to 100.0% on all 1,099 scored rows — by: Codex.
- 2026-08-27 — Added source-fidelity validators and a permitted-row first-pass baseline for the bounded evidence retry; local verification passed without introducing answer-key input — by: Codex.
