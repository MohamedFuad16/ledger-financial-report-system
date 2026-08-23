# Errors, gotchas & known issues

## A multi-report extraction displayed only one active report (resolved)
- Symptom: Selecting two corpus PDFs showed only the currently active PDF in the live pipeline, then showed the second only after the first disappeared; an interim result therefore read `1 of 2 reports` with no visible queued report.
- Cause: `ExecutionPipeline` grouped files by company and rendered only one `activeFile` from one `currentGroup`, despite the durable `batch_start` event already containing every selected PDF.
- Resolution: Render one persistent card for every `batch_start` file and keep a sticky batch summary with complete/running/queued counts. The regression uses two different companies so cross-company hiding cannot return.
- First seen: 2026-08-23

## Exact 3M FY2022 Strategy 3 stopped at 26/27 on a null residual (resolved)
- Symptom: Strategy 3 reported 96.3% exact accuracy and coverage even though the model extracted every disclosed amount correctly.
- Cause: The model stated that no Deferred Charges category existed and showed Total Assets equalled Current plus Fixed Assets, but returned null instead of the uniquely established residual zero.
- Resolution: Before confidence gating, complete a null only when exactly one term in a public schema identity is missing and all other terms are available. The derivation is copied into evidence, never overwrites a non-null value, never consults gold, and is reapplied when historical runs are read.
- First seen: 2026-08-23

## Human review opened a blank manual-entry table (resolved)
- Symptom: A pinned report with no candidate artifact still rendered 27 empty number inputs, while the small “Review answers” text link implied that extraction had already happened.
- Cause: `verification_payload` always synthesized the schema rows, and `/api/corpus` counted those placeholders as candidates even when no PDF extraction artifact existed. The UI had no extraction-on-review state.
- Resolution: Track `candidate_extracted` separately from schema shape, add an idempotent PDF-candidate extraction endpoint, and block editable review until the prefill exists. The review workspace now embeds the source PDF beside extracted values, supports corrections and Save & Approve, and shows a retry state on extraction failure. Backend and Vitest regressions cover the full flow.
- First seen: 2026-08-22

## Stored corpus runs still requested a deployment token (resolved)

The token form had been removed from Settings, but the shared client adapter and
Flask mutation guard still enforced `X-Ledger-Admin-Token`, so normal visitors
could browse the corpus but could not stage it. The guard, client storage/header,
bootstrap loading and SSM parameter were removed together. CORS remains an origin
policy rather than authentication; a future multi-tenant release needs a real
identity or job-budget boundary.

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
- Resolution: Install AWS CLI v2 from AWS's signed distribution before reading the SSM SecureString. The same instance was reused and verified through SSM.
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

## FY2021 PDF has an unusable text layer (historical result, not a current accuracy score)
- Symptom: All text-only strategies score approximately 3.7% on FY2021.
- Cause: The official PDF renders printed page 47 correctly, but its embedded font maps the balance-sheet text to unusable glyph codes. Ledger marks 73/142 pages unreadable; the only exact accepted row is Total Assets, recovered from a separate readable summary page (`1/27 = 3.7037%`).
- Resolution: Preserve the failure as input-health evidence. Strategy 2 now supplies compulsory or page-adaptive OCR, but FY2021 has no authoritative golden set, so the historical 3.7% must not be shown as a current exact-accuracy score. Do not treat arithmetic reconciliation or generated candidate answers as proof of ground-truth provenance.
- First seen: 2026-08-20

## Corpus discovery disappeared after route changes or refresh (resolved)
- Symptom: The EC2 thread continued after leaving Report corpus, but returning or reloading showed no active job; a backend restart erased the in-memory record entirely.
- Cause: `CORPUS_JOBS` was a process-local dictionary and the client had no recent-job listing/rehydration path.
- Resolution: Atomically snapshot every corpus job/event under `runs/_corpus_jobs`, expose recent jobs, restore the newest active/recent job on mount, and mark pre-restart active snapshots `interrupted` rather than losing their evidence.
- First seen: 2026-08-21

## Firecrawl account was repeatedly throttled (resolved)
- Symptom: A large Bakuraku crawl repeatedly consumed 11–13 requests per minute and received HTTP 429 responses despite per-request retries.
- Cause: Map, scrape and search calls were issued back-to-back; each retry slept independently, so another call could consume the account slot during cooldown.
- Resolution: Reserve every credit-consuming call through one cross-process 12.5-second gate, apply `Retry-After` as a shared account cooldown, and retain bounded jittered retries.
- First seen: 2026-08-21

## System Python lacks test dependencies
- Symptom: `python3 -m pytest` fails because pytest is absent.
- Cause: Project dependencies are installed in `.venv`; the test suite is a standalone script, not pytest-based.
- Resolution: Use `.venv/bin/python test_contract.py`.
- First seen: 2026-08-20

## FY2025 previously used a partial key as gold (resolved)
- Symptom: Accuracy and coverage can differ because only 19 of 27 FY2025 rows are scored.
- Cause: The supplied benchmark omits eight rows rather than inventing answers.
- Resolution: Remove FY2025 from runtime gold. Only the assignment-provided 3M FY2022 key is authoritative by default; any other report is scored only after a human approves all 27 candidate rows for the exact PDF SHA.
- First seen: 2026-08-20

## Official report libraries were not followed from company homepages (resolved)
- Symptom: Firecrawl successfully scraped an official corporate homepage containing an IR/securities-library link but reported zero annual-report candidates.
- Cause: Discovery inspected only the supplied page and same-domain PDFs returned directly by map/search; it did not scrape a linked official report-library HTML page.
- Resolution: Extract up to four same-domain links whose label/path identifies an annual or securities-report library, scrape those pages, and retain the existing PDF identity/year/screening gates. Corpus discovery requests now enable deep retry by default.
- First seen: 2026-08-23

## Parenthesized Japanese PDF filenames were truncated (resolved)
- Symptom: An official Alpico integrated-report link such as `report2025(印刷推奨).pdf` was downloaded as a URL ending at `(...推奨`, causing a false HTTP 404.
- Cause: The Markdown-link expression treated the filename's first closing parenthesis as the end of the Markdown destination.
- Resolution: Scan Markdown destinations character-by-character, tracking balanced parentheses and retaining the complete `.pdf` suffix. The linear-time regression includes a 500 KB page so URL repair cannot stall the API worker.
- First seen: 2026-08-23

## Search metadata admitted wrong-company and non-annual PDFs (resolved)
- Symptom: The accidental 112-client discovery job produced seven review items whose labels appeared plausible, but six PDFs belonged to unrelated companies and one was a shareholder-meeting notice.
- Cause: Search-result rejection was conditional on an official domain being present, and post-download screening checked fiscal year/balance-sheet content without rechecking expected company or annual-document identity inside the PDF.
- Resolution: Reject unmatched search/deep-search results even when the registry has no official URL, and require local text to confirm target company plus annual/securities-report type before canonical replacement. Removed all seven invalid production entries; durable job history retains the source URLs for audit.
- First seen: 2026-08-23

## Annual-report screening rejected every genuine 有価証券報告書 (resolved)
- Symptom: All year-expansion candidates failed admission with "The PDF is not an annual or securities report", and re-screening an already pinned, verified corpus member (note FY2022) failed identically — a dead gate.
- Cause: The non-annual rejection pattern matched 四半期報告書 anywhere in the document. Genuine annual securities reports routinely cross-reference their own quarterly filings (縦覧場所, audit history), so the marker intended to reject mislabeled quarterlies rejected every real annual report too.
- Resolution: `_is_annual_document` now trusts the filing's own cover label (【提出書類】, whitespace-stripped so spaced display titles cannot evade it), then the cover pages, before falling back to whole-document matching. Regression covers an annual report with an incidental quarterly cross-reference and a spaced-out quarterly cover.
- First seen: 2026-08-23

## Gazette gold recorded thousand-yen precision for million-yen sources (resolved)
- Symptom: Independent re-verification could not find JUKI産機テクノロジー, ファインディ and 株式会社with Total Assets on their gazette pages: the search looked for 19,221,000-style thousand-yen forms while the pages print 19,221 in 百万円.
- Cause: `materialize_statutory_gold.py` hardcoded `source_value_quantum: 0.001` although gazettes print in either 千円 or 百万円.
- Resolution: Quantum is now derived per entry from the printed amount and the indexed yen value; the three affected fixtures were corrected (values were always right — only the stated precision was wrong).
- First seen: 2026-08-23

## Standalone note-marker lines shifted balance-sheet column selection (resolved)
- Symptom: The gold-derivation engine read Toenec Investments as 24,253 (prior year) instead of 28,877; the audited FY2022 cross-check exposed it.
- Cause: EDINET statements sometimes print note markers (※３，※４) on their own line between the label and the amounts. Treating that line as a value shifted the two-column [prior, current] alignment so the "current" slot held the prior-year figure. A related half-width form (※1 348,663) merged the marker digit into the amount.
- Resolution: Marker-only lines are skipped outright, full-width-digit markers are stripped before NFKC folding, and half-width marker digits separated by a space are removed. The engine is cross-validated against all 13 human-audited FY2022 documents with zero mismatches, and every admitted printed value must be re-located by an independent pypdf pass.
- First seen: 2026-08-23
