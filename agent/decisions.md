## Index

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0001 | — Keep a clean local submission separate from the cloud runtime | — |
| ADR-0002 | — Use bounded Strategy 3 evidence selection with deterministic acceptance | — |
| ADR-0003 | — Publish the selected 10-company agreement cohort as a separate final aggregate | — |
| ADR-0004 | — Keep tests and runtime data deliberately separated | — |
| ADR-0005 | — Bound local extraction to two concurrent pipelines | — |

# Architecture decisions

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

## ADR-0003 — Publish the selected 10-company agreement cohort as a separate final aggregate

- Date: 2026-08-27
- Status: Accepted
- Context: The dashboard retains older historical run artifacts for speed/parser comparison. The current report instead uses a deliberately selected agreement cohort: only annual reports for which both Gemini 3.7 Flash medium and GLM-5.3 medium scored 100% are retained.
- Decision: Publish the final Strategy 3 aggregate as a small, row-free metadata file and API response: 10 companies, 47 SHA-pinned documents, 966/966 exact scored rows, 47/47 exact documents, 100.0% row-micro accuracy, 100.0% document-macro accuracy and 100.0% field coverage for each model. The dashboard headline uses that aggregate; historical charts remain explicitly labeled as historical comparisons.
- Consequences: The headline is reproducible from the exact-source benchmark feed and carries no per-row gold values or private PDFs. The result must always be labeled as a best-case agreement set, not a random or representative sample.

## ADR-0004 — Keep tests and runtime data deliberately separated

- Date: 2026-08-27
- Status: Accepted
- Context: The application is a flat Python layout, so root-level `test_*.py` files are the explicit discovery convention. Corpus tests and intelligent-scan tests protect active workflows, while runtime data and generated caches should never become source artifacts.
- Decision: Retain the current test files: `test_contract.py` is the standalone offline gate; `test_intelligent_scan.py` protects Strategy 3; corpus, staging and workspace tests protect the cloud library. Retain the root layout to avoid unnecessary import/path churn. Remove only generated caches and empty runtime directories; keep `.venv` and `frontend/node_modules` as local development dependencies and keep `.git` because this is the working repository.
- Consequences: Verification stays stable and meaningful. The clean submission exporter, rather than the active working tree, is responsible for excluding local dependencies and Git metadata.

## ADR-0005 — Bound local extraction to two concurrent pipelines

- Date: 2026-08-28
- Status: Accepted
- Context: Workspace isolation and per-job executors kept user data separate but did not impose one host-wide limit on CPU- and memory-heavy PDF parsing, rendering and OCR. Three visitors could therefore start three heavy pipelines on a two-vCPU, 3.7-GiB production host even though outbound model calls had their own limiter.
- Decision: Wrap every `pipeline.run_pipeline` entry in one process-wide `BoundedSemaphore(2)`. Keep the existing one-worker, ten-thread Gunicorn runtime so the gate is host-wide on the current deployment. Let a third extraction wait for a slot while request threads continue serving status polling; keep the adaptive OpenRouter limiter independent.
- Consequences: Three simultaneous workspaces are supported with at most two heavy local pipelines active and no state mixing. The third job may have queue latency. If production later adds Gunicorn workers or multiple instances, replace this in-process gate with a shared durable work queue or distributed semaphore.
