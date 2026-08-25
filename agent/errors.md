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

## Two audited FY2022 gold rows contradicted their own conventions (resolved)
- Symptom: Fresh Strategy 2 and Strategy 3 runs missed the same rows on ストライダーズ (Investments/Other Fixed/Financial Assets) and トーエネック (Long-term Loan) with well-cited evidence, while every other arm scored 100%.
- Cause: The Striders audit left a 組合等への出資 of 9,239千円 (financial-instruments note ※4, p62) in the Other Fixed residual although the documented convention (Dainichi precedent, encoded in the mapping rules) classifies note-disclosed equity contributions as Investments. The Toenec audit read 15百万円 from the collateral note as the long-term loan total, but that note discloses only the pledged portion; the standalone statement shows 42百万円 of third-party loans, so the consolidated total nested in その他 is unprovable.
- Resolution: Corrected the Striders fixture per the verified note (Investments 336.796, Other Fixed 67.767, Financial Assets 336.606; the 投資その他の資産 identity still closes at 404,373千円) and marked Toenec Long-term Loan unscorable, both with dated correction notes in the citations. Found by the full-corpus evaluation, verified against the raw PDF pages before any change.
- First seen: 2026-08-23

## Belc allowance split was scored despite an unprovable target (resolved)
- Symptom: Fresh Strategy 2 and Strategy 3 runs both scored 88.9% on ベルク with identical, well-reasoned answers netting the long-term 貸倒引当金 against Other Financial Assets per the documented default, while the audited gold netted it against the Other Fixed residual with its own reasoning (a lease deposit carries no bad-debt allowance).
- Cause: The allowance's target is genuinely undisclosed; two defensible readings reconcile identically. The audited fixture predated the derivation-engine policy that marks allowance ambiguity unscorable.
- Resolution: Financial Assets, Other Financial Assets, and Other Fixed Assets are now unscorable for the Belc FY2022 key (24 scorable rows), with a dated correction note. Striders remains scored because no counter-evidence contradicts the documented default there.
- First seen: 2026-08-24

## A superseded confidence ADR stayed live in the result sheet (resolved)
- Symptom: The run drawer rendered an em dash and the CSV export dropped the value for any row below 0.80 confidence, while agent/state.md and the backend both claimed values are never hidden.
- Cause: ADR-0031 moved confidence to review-priority metadata (display and export every returned value) and the backend was migrated, but RunDrawer's display and export conditionals predate the ADR and were never revisited — UI drift across roughly ten commits.
- Resolution: Both conditionals removed; every returned value renders and exports, with the dimmed is-rejected style and the accepted-count badge preserved as the review signal. A regression test pins the sub-0.80 display path. Also made summary input tokens the sum of the main, repair, and evidence-retry calls (with output tokens surfaced), and a failed evidence retry now contributes its real wall-clock to the run timing.
- First seen: 2026-08-24

## Transient 429s were classified as exhausted quota and abandoned paid batches (resolved)
- Symptom: An extraction batch stopped scheduling every remaining file after a single provider throttle, reporting "Skipped — <quota message>" for work that was never attempted.
- Cause: `api_client._quota_message` matched `_QUOTA_MARKERS` against `json.dumps(error)` — the whole serialized error dict, keys included. A request id containing `1308`, a key named `quota_reset_at`, or the word "credits" in prose all matched, and `QuotaExhaustedError` is raised before any retry, which both batch runners treat as terminal.
- Resolution: Phrases match the `message` field only and are narrowed (`quota exceeded`, `insufficient balance`, …); the numeric code is compared against `error.code`/`error.type` exactly. A missed quota signal only costs a retry, a false one costs a batch, so the classifier now errs toward retrying. Regression tests pin four false-positive shapes and three genuine ones.
- First seen: 2026-08-25

## A code fence sharing a line with the payload deleted the whole reply (resolved)
- Symptom: Valid 27-row replies were reported as "Model output was not valid JSON" and burned a contract-repair call.
- Cause: `_strip_code_fence` dropped `splitlines()[0]` unconditionally. For a single-line fence (```json {"rows": …), the payload *is* the first line, so the function returned "" and the `_first_json_value` salvage path had nothing left to scan.
- Resolution: The opener is parsed with a regex so any payload on the fence line survives, and a closing fence glued to the last content line is stripped too. Four fence shapes are pinned by tests.
- First seen: 2026-08-25

## An oversized integer escaped the contract as OverflowError (resolved)
- Symptom: A run died after the paid model call instead of attempting its one bounded repair.
- Cause: `json.loads` keeps a long digit run as an arbitrary-precision `int`; `float()` on it raises `OverflowError`, which is not a `ValidationError`, so `models.validate_extraction` never converted it and `pipeline`'s `except (GLMError, SchemaValidationError)` never caught it.
- Resolution: The finiteness check catches `OverflowError`/`ValueError` and raises the contract error, so the repair path engages normally.
- First seen: 2026-08-25

## Legacy GLM_ENABLE_REASONING outranked the current LLM_ name (resolved)
- Symptom: A `.env` carrying both names billed reasoning tokens against an explicit `LLM_ENABLE_REASONING=false`.
- Cause: `settings._reasoning_effort_from_env` read `GLM_*` before `LLM_*`, inverting the precedence every other setting in the module uses.
- Resolution: `LLM_*` first, matching the rest of the module. Pinned by a regression test.
- First seen: 2026-08-25

## A bulk selection survived a filter change and deleted invisible runs (resolved)
- Symptom: "Delete selected (3)" destroyed runs that were no longer on screen; the confirm dialog names only a count, so nothing warned the user.
- Cause: `HistoryPage` pruned `selectedRunIds` against the full `runs` list, never against the filtered rows, and the delete handler resolved ids against `runs` too.
- Resolution: Selection prunes against the visible rows and the handler passes those. Two regression tests, verified to fail against the unfixed component.
- First seen: 2026-08-25

## Re-running a report showed the first run's elapsed time (resolved)
- Symptom: A second run of the same PDF opened with a live timer already reading minutes.
- Cause: `ExecutionPipeline`'s `startedAt` ref was written once per key and never cleared, and the component never unmounts between runs, so the fallback stamp from the first run kept counting.
- Resolution: The ref is cleared when a run starts, and the backend's own step timestamp is preferred on every render instead of being cached at first sight.
- First seen: 2026-08-25

## One hydration effect served two Settings cards and discarded unsaved edits (resolved)
- Symptom: Saving the concurrency slider wiped an unsaved Model ID; saving the provider snapped the slider back.
- Cause: A single `useEffect` keyed on the `settings` object identity re-hydrated every field, and `onSaved()` always produces a new object.
- Resolution: Two effects, each re-hydrating only when its own server-side values change. Separately, re-clicking the already-selected provider tile no longer resets a hand-typed Model ID and Base URL.
- First seen: 2026-08-25

## Security exposures on the public deployment (documented, not fixed — owner decision 2026-08-25)
- Symptom: none observed; found by audit. Recorded so the decision stays revisitable.
- Findings, ranked: (1) HIGH — no inbound rate limiting and no authentication on the paid endpoints; `ratelimit.py` governs *outbound* LLM concurrency only, and the "(rate-limited)" comment at `server.py:122` is inaccurate, so any visitor can spend the operator's LLM budget without bound. (2) MEDIUM — no security headers anywhere (no CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, HSTS) on Flask, `vercel.json`, or the Caddyfile; the app is clickjackable. (3) MEDIUM — `GET /api/settings` returns `mask_key` output, exposing the first and last four characters of the LLM and Firecrawl keys to any anonymous request. (4) MEDIUM — `STAGED` and `uploads/` are unbounded on an unauthenticated endpoint, with no TTL or cap. (5) MEDIUM — no PDF magic-byte or content-type validation; untrusted bytes are written to disk and then fed to `pypdf`, `pymupdf`, `docling` and the native-Rust `pdf-inspector`. (6) MEDIUM — `ACTIVE_PROMPT` is process-global, so one visitor's system prompt becomes every visitor's. (7) `debug=True` in the `__main__` block (dev only; production uses gunicorn). (8) 500 responses echo `str(exc)`, leaking absolute server paths.
- Resolution: Deliberately none on this deployment — the owner chose to leave the live site unchanged rather than add spend controls that would gate the public demo. Every one of these is fixed in the standalone submission package instead.
- First seen: 2026-08-25
