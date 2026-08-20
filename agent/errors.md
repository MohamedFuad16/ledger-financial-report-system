# Errors, gotchas & known issues

## Custom Vercel domain was missing from the API CORS allowlist (resolved)
- Symptom: `assignment.mohamedfuad.com` loaded the React bundle but showed “Failed to fetch” for API-backed data, while the canonical Vercel alias worked.
- Cause: The EC2 environment allowed only `ledger-financial-report-system.vercel.app` as a browser origin.
- Resolution: Add both production UI origins to the live `CORS_ALLOWED_ORIGINS` value and the repeatable EC2 bootstrap default, restart Gunicorn, and verify the custom-domain browser flow.
- First seen: 2026-08-21

## Corpus API computed output metadata but returned the original list (resolved)
- Symptom: Report corpus omitted each PDF's output directory and stored-run count even though the server computed both fields.
- Cause: The response spread the original manifest but did not replace its `documents` key with the enriched list.
- Resolution: Return the enriched `documents` collection explicitly and verify the production response after restart.
- First seen: 2026-08-21

## Corpus manifest paths must not become arbitrary file access (resolved)
- Symptom: Reusing an already-downloaded report for extraction could tempt the API to accept a caller-supplied filesystem path.
- Cause: The upload staging contract originally knew only temporary upload IDs, while corpus PDFs live in durable company/year folders.
- Resolution: `/api/corpus/stage` accepts manifest SHA-256 IDs only, resolves the pinned manifest entry server-side, and rejects any resolved path outside `CORPUS_ROOT` or missing on disk.
- First seen: 2026-08-21

## Ubuntu 24.04 bootstrap could not install `awscli` from apt (resolved)
- Symptom: The first EC2 cloud-init run stopped before creating swap, cloning the repository, or starting the API.
- Cause: The selected Ubuntu 24.04 image has no installable `awscli` package in its configured apt repositories.
- Resolution: Install AWS CLI v2 from AWS's signed distribution before retrieving the SSM SecureString. The same instance was reused and verified through SSM.
- First seen: 2026-08-21

## Linux parser install pulled unused CUDA wheels (resolved)
- Symptom: A CPU-only `t3.medium` began downloading several gigabytes of NVIDIA/CUDA packages while resolving Docling's Torch dependency.
- Cause: PyPI's default Linux Torch wheel includes GPU dependencies; the first rerun also fetched a cached pre-fix bootstrap URL.
- Resolution: Cancel the install, execute an immutable Git commit URL, preinstall `torch` and `torchvision` from PyTorch's CPU wheel index, and clear bootstrap caches. Remote verification reports `torch 2.13.0+cpu`, CUDA false, and all parser imports successful.
- First seen: 2026-08-21

## Clean Vercel alias inherited SSO protection (resolved)
- Symptom: The canonical `ledger-financial-report-system.vercel.app` alias redirected anonymous visitors to Vercel login although the initial production alias was public.
- Cause: Team defaults applied `all_except_custom_domains` SSO protection to the project.
- Resolution: Explicitly disabled project SSO protection and reverified the canonical URL anonymously in the in-app browser.
- First seen: 2026-08-21

## Contract failures were not semantically retried (resolved)
- Symptom: A provider could return evidence-bearing JSON with one schema defect, but the run failed immediately after deterministic normalization.
- Cause: Existing retries covered only 429/eligible 5xx transport responses and repeated the same request; no repair turn included the invalid assistant response or Pydantic error.
- Resolution: Added one bounded repair turn with full prior context and separate `_repair_1` request/response artifacts. Confidence prompt wording now matches the 0.80 downstream gate.
- First seen: 2026-08-21

## Final theme layer hardcoded light colors (resolved)
- Symptom: Switching to dark mode changed the page shell but left cards, task rows, result sheets, inputs, and labels in the light palette.
- Cause: `editor-theme.css` loaded last, but many of its component rules used literal light colors instead of the theme tokens it also defined.
- Resolution: Added semantic dark overrides for every component family and kept the same slate/blue/peach visual system across both modes. In-app browser checks now cover the rendered dark Settings and Strategy 2 states.
- First seen: 2026-08-21

## Runtime checkbox inherited text-input width (resolved)
- Symptom: “Automatic batch sizing” wrapped vertically and the checkbox consumed most of the Settings card.
- Cause: `.runtime-grid input:not([type='range'])` also matched checkbox inputs.
- Resolution: Added a higher-specificity checkbox rule and rendered the control as a bounded 44px switch.
- First seen: 2026-08-21

## UI had no regression boundary (resolved)
- Symptom: Strategy 1 and Strategy 2 behavior can diverge or break without test failures.
- Cause: The legacy UI is a large static HTML/CSS/JS surface with duplicated DOM-id branches; the Python contract suite does not exercise it.
- Resolution: Replaced the delivery surface with typed React components, a tested SSE adapter, and browser QA across all routes.
- First seen: 2026-08-20

## FY2021 PDF has an unusable text layer
- Symptom: All text-only strategies score approximately 3.7% on FY2021.
- Cause: The source PDF's balance-sheet text layer is broken.
- Resolution: Detect and explain the condition; a future OCR strategy is required for recovery.
- First seen: 2026-08-20

## System Python lacks test dependencies
- Symptom: `python3 -m pytest` fails because pytest is absent.
- Cause: Project dependencies are installed in `.venv`; the test suite is a standalone script, not pytest-based.
- Resolution: Use `.venv/bin/python test_contract.py`.
- First seen: 2026-08-20

## FY2025 uses a partial golden key
- Symptom: Accuracy and coverage can differ because only 19 of 27 FY2025 rows are scored.
- Cause: The supplied benchmark omits eight rows rather than inventing answers.
- Resolution: Score only defined golden rows and continue reporting 27-row output coverage independently.
- First seen: 2026-08-20
