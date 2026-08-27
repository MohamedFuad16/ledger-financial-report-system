# Architecture decisions

## Index

| ID | Decision | Status |
|---|---|---|
| ADR-0001 | Keep a clean local submission separate from the cloud runtime | Accepted |
| ADR-0002 | Use bounded Strategy 3 evidence selection with deterministic acceptance | Accepted |
| ADR-0003 | Publish the retained 34-company benchmark as a separate final aggregate | Accepted |
| ADR-0004 | Keep tests and runtime data deliberately separated | Accepted |

## ADR-0001 — Keep a clean local submission separate from the cloud runtime

- Date: 2026-08-27
- Status: Accepted
- Context: The hosted service requires AWS, persistent cloud corpus storage and operational integrations that do not belong in an assignment submission.
- Decision: Keep the production application and cloud corpus in the main project. Ship a separate, local-only submission folder containing only the code, tests, public assets, documentation and reproducible local verification needed for assessment.
- Consequences: The submitted folder never contains AWS configuration, cloud corpus PDFs, runtime run artifacts, secrets, Git metadata or agent-maintenance material. The hosted demo remains a separate operational system.

## ADR-0002 — Use bounded Strategy 3 evidence selection with deterministic acceptance

- Date: 2026-08-27
- Status: Accepted
- Context: Full-document model input is expensive and can obscure the balance-sheet evidence. A retry must improve a failed arithmetic relationship without allowing broad, untraceable remapping.
- Decision: Strategy 3 performs deterministic complete-page ranking, routes OCR only where needed, sends three to five relevant pages to the model, and permits at most one evidence retry. The retry receives only the permitted first-pass rows, their compact baseline evidence, the exact failed identity and its discrepancy. Deterministic code accepts a replacement only when reconciliation or source fidelity strictly improves; all other rows remain unchanged.
- Consequences: The model never receives answer-key values, arithmetic and acceptance remain auditable, and retry cost is bounded.

## ADR-0003 — Publish the retained 34-company benchmark as a separate final aggregate

- Date: 2026-08-27
- Status: Accepted
- Context: The dashboard retained older historical run artifacts for speed/parser comparison. Those artifacts include pre-fix and partial-statutory passes, so averaging them produces 99.5% rather than the result of the final retained-cohort validation.
- Decision: Publish the final Gemini 3.7 Flash Strategy 3 aggregate as a small, row-free metadata file and API response: 34 companies, 75 SHA-pinned documents, 1,099/1,099 exact scored rows, 75/75 exact documents, 100.0% row-micro accuracy, 100.0% document-macro accuracy and 100.0% field coverage. The dashboard headline uses that final aggregate; historical charts remain explicitly labeled as historical comparisons.
- Consequences: The public headline is current and truthful without rewriting or concealing historical observations. The aggregate carries no per-row gold values or private PDFs.

## ADR-0004 — Keep tests and runtime data deliberately separated

- Date: 2026-08-27
- Status: Accepted
- Context: The application is a flat Python layout, so root-level `test_*.py` files are the explicit discovery convention. Corpus tests and intelligent-scan tests protect active workflows, while runtime data and generated caches should never become source artifacts.
- Decision: Retain the current test files: `test_contract.py` is the standalone offline gate; `test_intelligent_scan.py` protects Strategy 3; corpus, staging and workspace tests protect the cloud library. Retain the root layout to avoid unnecessary import/path churn. Remove only generated caches and empty runtime directories; keep `.venv` and `frontend/node_modules` as local development dependencies and keep `.git` because this is the working repository.
- Consequences: Verification stays stable and meaningful. The clean submission exporter, rather than the active working tree, is responsible for excluding local dependencies and Git metadata.
