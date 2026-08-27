# Project state

> Last updated: 2026-08-27 · deployed release: dashboard-summary rollout pending

## Current state summary

Ledger is a React/Flask Annual Report extractor with three strategies: no OCR, OCR-enabled parsing and Strategy 3 intelligent scanning. Strategy 3 uses local OCR only for routed pages, deterministic complete-page selection, a three-to-five-page model context and at most one permitted-row evidence retry. Reconciliation and replacement acceptance remain deterministic and never consult answer keys.

The owner-approved retained benchmark contains 34 companies and 75 SHA-pinned documents. The latest fresh Gemini 3.7 Flash Strategy 3 validation, filtered to that cohort, is 1,099/1,099 exact scored rows and 75/75 exact documents: 100.0% row-micro accuracy, 100.0% document-macro accuracy and 100.0% field coverage. Older stored comparison runs are preserved for historical speed/parser charts and are not the final validation result.

Cloud corpus PDFs, manifests and runtime artifacts remain outside Git. The clean submission folder is separate from this operational repository and excludes AWS, corpus data, secrets, Git history and agent maintenance files.

## Recent changes

- 2026-08-27 — Added a row-free final Strategy 3 summary endpoint and dashboard headline source. It distinguishes the final retained-cohort result from historical comparison runs that average 99.5% — by: Codex.
- 2026-08-27 — Replaced the long ADR archive with four current, decision-focused records and reduced this state file to current operational facts — by: Codex.
- 2026-08-27 — Removed the owner-designated complete six-document cohort from source-bound fixtures, current corpus and production artifacts. The retained 34-company result recalculates to 100.0% on all 1,099 scored rows — by: Codex.
- 2026-08-27 — Added source-fidelity validators and a permitted-row first-pass baseline for the bounded evidence retry; local verification passed without introducing answer-key input — by: Codex.
