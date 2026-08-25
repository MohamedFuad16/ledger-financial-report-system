## Index

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0001 | — Adopt the `agent/` knowledge base | — |
| ADR-0002 | — Serve a typed React SPA from Flask | — |
| ADR-0003 | — Preserve experiment purity and fail closed | — |
| ADR-0004 | — Keep corpus acquisition separate from extraction | — |
| ADR-0005 | — Share one adaptive request gate across strategies | — |
| ADR-0006 | — Use the Resume editor as Ledger's visual source of truth | — |
| ADR-0007 | — Make locale and live task state first-class client concerns | — |
| ADR-0008 | — Verify connector credentials before local persistence | — |
| ADR-0009 | — Bound semantic contract repair to one preserved attempt | — |
| ADR-0010 | — Split static UI and persistent parser backend across Vercel and EC2 | — |
| ADR-0011 | — Reuse corpus documents through durable-reference staging | — |
| ADR-0012 | — Keep visit telemetry private and backend-only | — |
| ADR-0013 | — Publish the assignment mutation API without a browser token | — |
| ADR-0014 | — Delete corpus files only through their pinned manifest identity | — |
| ADR-0015 | — Remove the retired static client and orphaned experiment data | — |
| ADR-0016 | — Reduce live comparison events to one card per report | — |
| ADR-0017 | — Keep one canonical PDF per corpus company and fiscal year | — |
| ADR-0018 | — Persist extraction jobs independently of browser routes | — |
| ADR-0019 | — Aggregate parser results on a matched report cohort | — |
| ADR-0020 | — Screen Japanese filings without weakening the M-USD contract | — |
| ADR-0021 | — Pace Firecrawl globally and persist corpus-job evidence | — |
| ADR-0022 | — Treat answer-key provenance separately from reconciliation | — |
| ADR-0023 | — Separate the no-OCR and OCR-enabled parser arms | — |
| ADR-0024 | — Coordinate Firecrawl pacing and manifest writes across processes | — |
| ADR-0025 | — Isolate public run state by anonymous browser workspace | — |
| ADR-0026 | — Require PDF extraction before human answer review | — |
| ADR-0027 | — Limit the product to two extraction strategies | — |
| ADR-0028 | — Restore Strategy 3 as guarded page selection and separate discovery from answer mapping | — |
| ADR-0029 | — Finalize Strategy 3 on pdf-inspector metadata and selective OCR | — |
| ADR-0030 | — Align public strategy numbers with durable backend scopes | — |

## ADR-0001 — Adopt the `agent/` knowledge base
- Date: 2026-08-20
- Status: Accepted
- Context: The repository had no compact architecture, state, or impact map despite a multi-module pipeline and a large UI surface.
- Decision: Maintain a routed `agent/` knowledge base, rolling state, append-only ADRs, and deterministic dependency/architecture graphs.
- Consequences: Future work can load the relevant subsystem without rescanning the repository, but structural changes must refresh the graph and state.

## ADR-0002 — Serve a typed React SPA from Flask
- Date: 2026-08-20
- Status: Accepted
- Context: The large static client duplicated strategy behavior, had no typed API boundary, and was difficult to verify or extend.
- Decision: Make `frontend/` the source of truth, build it with React 19, TypeScript, and Vite, and serve `frontend/dist/` from the existing Flask application. Keep the legacy `static/` files only as an archive.
- Consequences: Strategy workflows and shared UI now compose from reusable components and can be type-checked/tested; production startup requires a frontend build after client changes.

## ADR-0003 — Preserve experiment purity and fail closed
- Date: 2026-08-20
- Status: Accepted
- Context: Silent defaults could turn missing confidence into certainty, run an unknown strategy as Strategy 1, OCR a supposedly text-only parser, or export confidence-rejected values.
- Decision: Keep parser strategies representation-only, reject unknown strategy keys and incomplete contracts, block model calls without readable text, and expose accepted values only after the 0.80 confidence gate.
- Consequences: Some previously tolerated payloads now fail with actionable errors; experimental comparisons and exports better represent what the system actually proved.

## ADR-0004 — Keep corpus acquisition separate from extraction
- Date: 2026-08-20
- Status: Accepted
- Context: Large company/year datasets must be acquired, screened and reviewed without accidentally spending model quota or admitting mislabeled/unreadable documents.
- Decision: Use Firecrawl v2 map/search only for discovery, download candidate PDFs directly, validate and SHA-256-pin them, screen document-internal fiscal year/balance-sheet/text health, and require a later explicit extraction action.
- Consequences: Discovery is credit-predictable and auditable; review documents remain visible rather than silently dropped, and corpus jobs cannot trigger LLM calls.

## ADR-0005 — Share one adaptive request gate across strategies
- Date: 2026-08-20
- Status: Accepted
- Context: Independent Strategy 1/2 rate sliders could jointly exceed the same provider allowance and did not incorporate batch token load or observed throttling.
- Decision: Store one global ceiling in Settings, size initial batches from file count/token load, and make HTTP 429/Retry-After feedback authoritative for shrinking, pausing and gradual recovery.
- Consequences: Parallel work remains adjustable without inventing RPM/TPM limits; all strategy jobs observe the same live provider state.

## ADR-0006 — Use the Resume editor as Ledger's visual source of truth
- Date: 2026-08-21
- Status: Accepted
- Context: The earlier editorial palette and decorative metric rails did not match the user's preferred application UI, obscured hierarchy, and lacked a direct relative-speed view.
- Decision: Map tokens and layout proportions from the user's `Documents/Resume/editor` application into a dedicated final theme layer; keep color mostly for data and actions, express speed relative to Strategy 1, separate field coverage from exact accuracy, and adapt the official RareUI folder component for PDF staging.
- Consequences: Ledger and the reference editor now share a coherent shell, density and chart language; `editor-theme.css` intentionally loads after legacy styles, and upstream RareUI attribution remains in the component source.

## ADR-0007 — Make locale and live task state first-class client concerns
- Date: 2026-08-21
- Status: Accepted
- Context: Static English copy and a dotted execution timeline made parser progress difficult to understand, while modal result inspection hid the surrounding experiment context.
- Decision: Resolve the initial English/Japanese locale from the browser, persist explicit user choice, and route visible copy through a shared locale provider. Map existing SSE execution state into BeautifulUI-derived expandable task rows with streamed status text, and render result details inline below their source table. Keep parser warnings and arithmetic diagnostics in stored artifacts but out of the current UI.
- Consequences: Pages and shared components must supply both English and Japanese labels; new execution states can be tested without model calls, and users retain page context while reviewing results.

## ADR-0008 — Verify connector credentials before local persistence
- Date: 2026-08-21
- Status: Accepted
- Context: Runtime settings could previously report success after writing an unverified Firecrawl key, while saved and replacement credentials were visually ambiguous.
- Decision: Keep saved credentials masked, accept blank replacement fields as “keep existing,” and probe Firecrawl's authenticated credit-usage endpoint before writing runtime settings or resizing the shared limiter. Keep model-provider saves on their existing test-before-write path.
- Consequences: A bad or unavailable Firecrawl credential leaves local runtime settings unchanged; the settings UI can truthfully distinguish saved secrets from unsaved replacements without ever exposing the stored value.

## ADR-0009 — Bound semantic contract repair to one preserved attempt
- Date: 2026-08-21
- Status: Accepted
- Context: Transport retries repeated identical requests, but malformed JSON or a Pydantic contract violation ended a run even when the provider had returned a nearly correct answer. The prompt also calibrated confidence at 0.5 while accepted output uses a measured 0.80 gate.
- Decision: Keep deterministic normalization first, then make at most one semantic repair call containing the original system/user messages, the invalid assistant response, and the exact contract error. Persist the repair request/response separately and align prompt confidence wording with the 0.80 acceptance boundary.
- Consequences: Recoverable shape errors no longer discard a full extraction, while the single-attempt bound prevents unbounded spend and preserves both model attempts for audit. Failures after the repair still fail closed.

## ADR-0010 — Split static UI and persistent parser backend across Vercel and EC2
- Date: 2026-08-21
- Status: Accepted
- Context: The React bundle is a natural fit for Vercel, but the Flask pipeline needs persistent run/upload storage, long-lived SSE requests, large PDF uploads, and a native Docling/Torch environment that exceeds practical serverless function limits.
- Decision: Publish the Vite client on Vercel and run the Flask API on a single Tokyo `t3.medium` EC2 instance behind Caddy HTTPS. Require a strong SSM Parameter Store token for every mutating API call, store that token only in the operator's browser, keep GET endpoints public, limit CORS to production UI origins, manage the instance through SSM with no SSH ingress, require IMDSv2, and use an encrypted 40 GiB gp3 volume plus CPU-only PyTorch wheels.
- Consequences: The deployed application retains the local file-backed semantics and supports long parser calls, but it has a continuously billed VM and one availability zone. Production writes require the browser token; backups, horizontal scaling, and a custom API hostname remain separate follow-up infrastructure work.

## ADR-0011 — Reuse corpus documents through durable-reference staging
- Date: 2026-08-21
- Status: Accepted
- Context: Firecrawl downloads already live in stable company/year/timestamp folders, but Strategy 1 and Strategy 2 previously accepted only new browser uploads. Copying corpus PDFs into upload storage would duplicate large reports and weaken provenance.
- Decision: Add an Upload/Corpus input switch to both active strategies. Select corpus entries by their manifest SHA-256 ID, resolve and validate the path only on the server, then place a short-lived reference into the same staged-extraction abstraction used by uploads. Keep English canonical schema keys in artifacts and localize them only at render/export time.
- Consequences: Single reports or batches can run through the existing SSE pipeline without moving the source PDF; outputs remain discoverable under the matching company/FY run namespace. Manifest paths outside the corpus root fail closed, while Japanese result sheets can change language without changing the stored contract.

## ADR-0012 — Keep visit telemetry private and backend-only
- Date: 2026-08-21
- Status: Accepted
- Context: The owner needs a timestamped notification when someone opens the public site, but exposing a Redis or email credential in a static Vite bundle would make the connector publicly reusable.
- Decision: Let the browser submit only bounded visit metadata to an origin-restricted Flask endpoint. Deduplicate by a hashed browser-session/IP marker, retain only the newest 2,000 Upstash events plus aggregate counters, and send notifications from the EC2 role through a verified, recipient-restricted SES identity. Store connector values in SSM Parameter Store and load them only into the backend service environment.
- Consequences: Public visitors never receive connector credentials and cannot choose the notification recipient. Telemetry remains intentionally small and private, while delivery depends on Upstash, SES, and the single EC2 service.

## ADR-0013 — Publish the assignment mutation API without a browser token
- Date: 2026-08-21
- Status: Accepted
- Context: Durable corpus staging and extraction from the public Vercel UI still depended on an operator-only deployment token, contradicting the requested no-access-token workflow and making available-data runs fail for normal visitors.
- Decision: Remove the Flask mutation-token guard, client token storage/header injection, bootstrap token loading, and SSM mutation-token parameter. Keep the browser CORS allowlist, existing input/path validation, provider credential isolation, adaptive concurrency and bounded request sizes. Document explicitly that CORS is not authentication.
- Consequences: A normal visitor can stage and run a configured extraction without a separate credential. Direct callers can also invoke mutation routes and potentially consume configured model/Firecrawl quota, so authentication or a job-budget boundary is required before this becomes a multi-tenant production service.

## ADR-0014 — Delete corpus files only through their pinned manifest identity
- Date: 2026-08-21
- Status: Accepted
- Context: Downloaded reports need a user-visible removal action, but accepting a client path would create an arbitrary-file-deletion risk and deleting a source document must not erase historical extraction evidence.
- Decision: Add a confirmation-gated delete endpoint keyed exclusively by a manifest SHA-256 identifier. Resolve the stored path server-side, require that it stays inside `CORPUS_ROOT`, atomically remove the manifest entry with its PDF, prune only empty corpus subdirectories, and retain `runs/` artifacts.
- Consequences: The Pinned Manifest can safely remove a downloaded source without breaking run history. A stale/malicious path fails closed and the action remains auditable through the manifest update time.

## ADR-0015 — Remove the retired static client and orphaned experiment data
- Date: 2026-08-21
- Status: Accepted; supersedes the archive clause in ADR-0002
- Context: React/Vite has been the only served client since ADR-0002, while the former `static/` implementation, 643 MB of unreferenced upload copies, one superseded corpus PDF, and one obsolete run remained in the workspace and could be mistaken for current state.
- Decision: Keep `frontend/` as the sole client source, remove the retired `static/` files, and recoverably move only filesystem artifacts that are absent from the corpus manifest and current run references to macOS Trash. Preserve the verified manifest-owned corpus PDF and maintained golden test dataset.
- Consequences: The repository has one UI source of truth and the local workspace no longer carries misleading history. Trashed local artifacts can be restored if needed; future uploads and runs continue using the normalized company/year/timestamp layouts.

## ADR-0016 — Reduce live comparison events to one card per report
- Date: 2026-08-21
- Status: Accepted
- Context: A Strategy 2 batch previously expanded every report into one parser container plus six stage capsules for every pass. Six reports and four parsers produced a very tall wall of repeated content that obscured the file-level progress the user needed.
- Decision: Preserve the existing per-file/per-parser SSE event model, but reduce it in the React client to exactly one animated live card per report. The card displays the active parser, current stage, streamed message and timer; a compact rail shows completed, active and queued parsers without reproducing their stages. Replace the decorative sparkle used for New extraction with a restrained file-plus action glyph.
- Consequences: Backend execution and stored artifacts remain unchanged, while batch progress is legible at a glance. Component tests now assert one-card-per-report identity and parser transitions; future stages can be added without multiplying the page height.

## ADR-0017 — Keep one canonical PDF per corpus company and fiscal year
- Date: 2026-08-21
- Status: Accepted; refines ADR-0004 and ADR-0011
- Context: Timestamped corpus download folders allowed repeated crawls of the same company/year to accumulate parallel PDFs, made the picker identity harder to understand, and obscured the user's expectation that the latest verified report replaces the prior copy.
- Decision: Store exactly one manifest-owned PDF at `corpus_dataset/<company>/<year>/<company>_annual_report_<year>.pdf`. Download to a unique temporary file, screen it fully, then atomically replace the canonical target and upsert the manifest by company/year. On startup, safely migrate manifest-owned legacy timestamp paths to the canonical location and remove only superseded manifest-owned files.
- Consequences: Refreshes and service restarts continue to see the same AWS EBS-backed corpus, and successful recrawls overwrite rather than fork a company/year. Failed downloads or screening cannot destroy the previous verified PDF. The current encrypted root EBS volume is still single-instance storage, not a cross-instance backup, and is configured with delete-on-termination.

## ADR-0018 — Persist extraction jobs independently of browser routes
- Date: 2026-08-21
- Status: Accepted
- Context: Strategy 1/2 batches are long-running backend operations, but the client previously treated the active route and in-memory SSE reducer as the authoritative job state. Navigating away or refreshing could therefore hide an otherwise continuing extraction.
- Decision: Assign every extraction a backend job identity, atomically snapshot its lifecycle under `runs/_extraction_jobs`, expose list/detail/event endpoints, and let the React client rehydrate unfinished jobs before resuming event consumption. The visible route is only an observer; it does not own execution lifetime.
- Consequences: Jobs continue through route changes and refreshes and their terminal evidence is inspectable after disconnects. The current file-backed job registry shares the single-EC2 durability and availability limits of the rest of `runs/`.

## ADR-0019 — Aggregate parser results on a matched report cohort
- Date: 2026-08-21
- Status: Accepted
- Context: Averaging every successful parser run independently rewards parsers that fail on difficult reports and allows repeated runs of one PDF to overweight that document.
- Decision: Define a report identity from company, fiscal year and source file; keep only the newest result for each parser/report pair; admit a report to Strategy 2 aggregates only when every selected parser has a successful result; and average report-level metrics with equal report weight. Preserve per-PDF metrics and disclose scheduled, successful and failed counts.
- Consequences: Dashboard and live comparison averages are directly comparable across parsers and avoid survivorship/rerun bias. A parser failure removes that report from the aggregate, so the UI must continue to surface the excluded/failed counts rather than presenting the matched average alone.

## ADR-0020 — Screen Japanese filings without weakening the M-USD contract
- Date: 2026-08-21
- Status: Accepted
- Context: Official Japanese filings use Japanese balance-sheet/fiscal-year vocabulary and commonly report JPY. English-only screening rejected valid documents, while silently sending JPY into the fixed M-USD extraction contract would produce invalid benchmark values.
- Decision: Recognize Japanese balance-sheet, fiscal-year and currency evidence during corpus screening and record the detected currency in the manifest. Treat screening readiness as acquisition evidence only; do not reinterpret or convert currencies inside Strategy 1/2. A currency-aware benchmark contract must be introduced explicitly before Japanese reports enter M-USD evaluation runs.
- Consequences: Official Japanese reports can be discovered, screened, stored and selected without false negatives, as demonstrated by AppBank FY2024. The current extractor still cannot validly score JPY filings against the M-USD schema, so bulk Bakuraku extraction remains gated on an explicit currency design and budget boundary.

## ADR-0021 — Pace Firecrawl globally and persist corpus-job evidence
- Date: 2026-08-21
- Status: Accepted
- Context: Company discovery issues map, scrape and search requests under one Firecrawl account. Independent per-request retry sleeps allowed other calls to consume the same account slot, causing repeated HTTP 429s. Corpus threads survived browser navigation but their only registry was process memory, so route reloads hid progress and backend restarts erased its audit state.
- Decision: Reserve all credit-consuming Firecrawl requests through one process-wide gate with a seven-second default interval; apply Retry-After as an account-wide cooldown and keep bounded jittered retries. Atomically snapshot corpus jobs and their newest 200 events under `runs/_corpus_jobs`, expose a recent-job list, and rehydrate the latest active/recent job in React. Preserve a pre-restart active snapshot as `interrupted`; do not claim that a dead Python thread resumed.
- Consequences: One Gunicorn process stays below the observed ten-request-per-minute limit and concurrent jobs cannot bypass cooldown. Navigation and refresh retain live visibility, while a service restart retains an honest terminal audit record and requires an explicit new job. Multi-process or horizontally scaled workers would need a distributed limiter/queue rather than this process-local gate.

## ADR-0022 — Treat answer-key provenance separately from reconciliation
- Date: 2026-08-21
- Status: Accepted
- Context: The test suite proves that maintained year keys have valid shape and balance-sheet arithmetic, but the assignment problem statement supplies a complete authoritative key only for FY2022. Calling every project-derived year “official ground truth” overstates what those tests establish, and FY2021's broken text layer makes the distinction especially important.
- Decision: Describe FY2022 as assignment-supplied and every other maintained year key as provisional until it is pinned to the evaluated PDF SHA-256 and independently transcribed with page/table/column/unit/derivation citations. Keep arithmetic reconciliation as a separate document-independent consistency signal. Preserve FY2021's `1/27 = 3.7%` result as a text-layer failure and exclude it from parser-representation claims until OCR/vision is an explicit strategy.
- Consequences: Dashboard arithmetic remains unchanged, but research claims now disclose the provenance boundary. A future audited golden-set artifact should carry row-level citations and reviewer status rather than relying on an in-code dictionary alone.

## ADR-0023 — Separate the no-OCR and OCR-enabled parser arms
- Date: 2026-08-21
- Status: Accepted; refines ADR-0003, ADR-0004 and ADR-0022
- Context: The previous Strategy 1/2 labeling conflated a direct PyPDF baseline, a representation bake-off and OCR recovery. The assignment requires the same four selectable parsers in both strategies, with OCR completely disabled in Strategy 1 and enabled in Strategy 2. Only parsers with a real page-level detector may be called adaptive, and Firecrawl-generated answers must not become ground truth automatically.
- Decision: Register PyPDF, PyMuPDF4LLM, pdf-inspector and Docling in both strategies. Disable OCR for all Strategy 1 passes. In Strategy 2, force OCR for PyPDF and Docling, use PyMuPDF4LLM's integrated adaptive recovery, and route pdf-inspector page-by-page: native Rust extraction for text pages, exact 200-DPI render plus local OCR for OCR-needed pages, then page-ordered Markdown assembly. Use Firecrawl for report discovery. Permit unverified corpus execution with an explicit warning, but expose exact accuracy only for assignment gold, an independently audited exact-source fixture, or a human-approved table bound to the executed PDF SHA-256.
- Consequences: Dashboard strategy comparisons now reflect two explicit end-to-end experimental arms, OCR routing remains observable per page, and machine candidates cannot silently contaminate accuracy. Because Strategy 2 parsers use different OCR engines/routing, it is an end-to-end capability comparison rather than a pure OCR-only causal ablation; a shared OCR-normalized control would be needed for that claim.

## ADR-0024 — Coordinate Firecrawl pacing and manifest writes across processes
- Date: 2026-08-21
- Status: Accepted; refines ADR-0021
- Context: ADR-0021's process-local seven-second gate was still vulnerable to a second worker process and exceeded the observed account limit once request timing and retries overlapped. The JSON manifest's thread-only lock had the same cross-process lost-update risk.
- Decision: Reserve every credit-consuming Firecrawl call through an OS-file-locked, cross-process 12.5-second gate, extend the same shared state with account-wide `Retry-After` cooldowns, and protect manifest read-modify-write operations with a separate OS file lock. Keep the implementation file-backed while the worker remains single-host.
- Consequences: Gunicorn threads and local worker processes on the EC2 host cannot bypass pacing or overwrite each other's manifest updates. A horizontally scaled deployment still requires a distributed lease/transaction store such as Redis or DynamoDB; the local lock is not a multi-host queue.

## ADR-0025 — Isolate public run state by anonymous browser workspace
- Date: 2026-08-22
- Status: Accepted; refines ADR-0013 and ADR-0018
- Context: Removing the browser access token made the assignment usable, but all visitors still shared staged-upload IDs, extraction-job listings, run history, output counts and destructive run actions through one public API surface.
- Decision: Generate one random stable workspace identifier in browser local storage and send it as `X-Ledger-Workspace`. Stamp staged files, extraction jobs and predictions with that identifier; filter job/run reads and require the same workspace for run deletion and evaluation. Keep corpus documents shared because they are the public benchmark library.
- Consequences: Ordinary visitors no longer see or delete each other's run state, while legacy artifacts remain in the `legacy-public` workspace. The header is an isolation hint, not authentication: a caller that knows another identifier can impersonate it, so real identity and quota controls remain required for a multi-tenant product.

## ADR-0026 — Require PDF extraction before human answer review
- Date: 2026-08-22
- Status: Accepted; refines ADR-0023
- Context: The review API synthesized 27 schema rows even when no candidate artifact existed, and the corpus list counted those placeholders as candidates. The UI therefore opened a blank table and effectively asked the reviewer to author the benchmark key from scratch, contradicting the intended extract-review-correct-approve workflow.
- Decision: Treat candidate-artifact existence as a first-class state. Run up to three uncached Firecrawl PDF passes, retain each pass, form a provisional consensus with agreement metadata, and expose an idempotent on-demand extraction route for legacy documents. Do not render editable review inputs until extraction succeeds. Present the pinned PDF beside the prefilled table, allow corrections, then require a separate confirmation to save SHA-bound human approval.
- Consequences: “Human review required” now means machine extraction is ready for validation, not manual data entry. A failed or unavailable extractor produces an explicit retry state and cannot be approved as a blank table. Multi-pass agreement measures repeatability only and never promotes candidates to gold automatically.

## ADR-0027 — Limit the product to two extraction strategies
- Date: 2026-08-22
- Status: Accepted
- Context: Two planned navigation branches described future architectures that are not part of this assignment. Keeping them in the sidebar, dashboard, route type and public documentation made unfinished work look like required product scope.
- Decision: Keep only the Overview, Strategy 1, Strategy 2, History, Report corpus, Target schema and Settings surfaces. Delete the unused planned-strategy page and roadmap document. Both active strategies retain the same direct lifecycle: parse the PDF, send its representation to the configured model for semantic mapping, validate the fixed 27-row result, and let a reviewer verify corpus candidates against the pinned PDF.
- Consequences: The navigation and public documentation now describe only implemented assignment behavior. Any additional extraction architecture would require a new scoped decision and implementation rather than a dormant public stub.

## ADR-0028 — Restore Strategy 3 as guarded page selection and separate discovery from answer mapping
- Date: 2026-08-22
- Status: Accepted; supersedes ADR-0027 and the public numbering in ADR-0023/ADR-0026
- Context: The project needs a third planned experiment that reduces the full Markdown context sent to the model, while the corpus screenshots showed Firecrawl structured extraction repeatedly failing and the public Strategy 1/2 OCR labels reversed from the required product language. The review modal was also too short and its embedded PDF did not make native find discoverable.
- Decision: Define public Strategy 1 as the no-OCR four-parser arm and Strategy 2 as the OCR-enabled arm while preserving historical run artifacts. Add Strategy 3 as complete-page selection using 27-schema terms, accounting synonyms, BM25-style lexical scores and explicit reject patterns; require balance-sheet/neighbor retention, evidence-page recall measurement and a full-document fallback. Limit Firecrawl to official-report discovery/download. Run one configured-LLM semantic-mapping pass when Review answers opens, store its provisional 27 rows, replace legacy Firecrawl candidates, and require human correction plus SHA-bound approval. Use a taller 50/50 review workspace with a native PDF iframe and visible Cmd/Ctrl+F guidance.
- Consequences: The dashboard has three evenly spaced strategy cards and no redundant OCR arm switch. Strategy 3 is honest planned scope rather than an active endpoint, and its token-saving claim cannot pass if evidence or accuracy regresses. Corpus acquisition no longer spends repeated Firecrawl extraction passes, while every unverified report still starts review from machine-prefilled values rather than blank input. Historical run identifiers remain compatible even though their public number is now mapped by experiment rather than key prefix.

## ADR-0029 — Finalize Strategy 3 on pdf-inspector metadata and selective OCR
- Date: 2026-08-22
- Status: Accepted; refines the Strategy 3 portion of ADR-0028
- Context: The finalized architecture requires pdf-inspector to be the sole parser, route OCR per page, replace only routed pages in unified Markdown, then reduce semantic-mapping input to three to five relevant complete pages. The implementation had to use metadata the library actually exposes rather than assume document-layout capabilities.
- Decision: Require pdf-inspector 1.15+. Use `detect_pdf` for document type, confidence, encoding health and OCR routing, and `extract_pages_markdown` for 0-indexed page bodies plus 1-indexed aggregate OCR/table/column metadata. Normalize all boundaries to 1-indexed PDF pages. Render only routed pages at 200 DPI, replace them with local RapidOCR PP-OCRv6 ONNX text, and retain native Markdown for every other page. Score complete unified pages in deterministic Python using BM25-style 27-schema/accounting terms, financial headings, table presence, column/layout metadata, numeric density and bounded boilerplate penalties. Send the top three to five pages in original order to the existing semantic mapper, exact JSON contract, confidence gate and arithmetic reconciliation. Persist full selection scores and page provenance.
- Consequences: Strategy 3 is an active backend/UI execution path rather than a roadmap stub. LLM input falls by roughly 96–97% in representative readable 3M reports, but OCR work happens before selection: pdf-inspector routes 73/142 FY2021 pages because of its damaged text layer, so OCR cost may remain high even when LLM-token cost falls. The fixed three-to-five-page ceiling must be evaluated on held-out reports for evidence recall and exact accuracy; diagnostics make misses and routing costs auditable.

## ADR-0030 — Align public strategy numbers with durable backend scopes
- Date: 2026-08-22
- Status: Accepted; supersedes the Strategy 1/2 numbering decision in ADR-0028 and restores ADR-0023
- Context: Public labels mapped Strategy 1 to backend `s2` and Strategy 2 to backend `s1`. Durable jobs derive their scope from those stable keys, so an OCR job launched from the page labelled Strategy 1 could be discovered and rendered by the page labelled Strategy 2. Routine preflight also surfaced a non-actionable Z.AI RPM/TPM advisory as an error toast on every run.
- Decision: Define Strategy 1 as the `s1*` no-OCR arm and Strategy 2 as the `s2*` OCR-enabled arm everywhere. Keep job scope, route identity, parser selection, dashboard experiment and history filtering aligned. Reject a persisted job whose scope does not match the observing page before replaying any events. Retain adaptive 429 handling internally but do not emit the static unpublished-limit advisory.
- Consequences: Live execution is visible only on its owning strategy page, historical run keys remain compatible, and normal extraction startup no longer produces an alarming non-actionable popup. Real scheduling reductions, observed limits and throttle events remain available as advisories.

## ADR-0031 — Keep OCR local and treat model confidence as review metadata
- Date: 2026-08-22
- Status: Accepted; supersedes the hosted-OCR portions of ADR-0023 and ADR-0029
- Context: pdf-inspector correctly owns the native-text/OCR page boundary, but sending routed page images to a hosted OCR service added an unrelated external dependency, credential and latency path. The FY2022 audit also proved that the model returned correct values below the 0.80 confidence threshold: gating those values reduced displayed accuracy and made arithmetic checks skip otherwise complete identities. Separately, the two genuine FY2022 misses came from ambiguous economic mapping of right-of-use assets, not missing source evidence or answer-key leakage.
- Decision: Render only pdf-inspector-routed pages at 200 DPI and recognize them locally with RapidOCR's bundled PP-OCRv6 ONNX detector/recognizer, preserving page-level provenance. Keep the 0.80 flag only as review-priority metadata. Display and export every returned value; compute coverage, exact accuracy, precision and arithmetic consistency from the returned values; expose confidence-accepted coverage/precision separately. Default extraction temperature to 0.0 for reproducibility. Clarify general mapping guidance for right-of-use assets and long-lived financial claims without including company values or golden answers. Rank all corpus balance-sheet heading candidates so an audited statement outranks earlier MD&A prose.
- Consequences: Strategy 2/3 OCR is private, credential-free and CPU-bound; EC2 sizing now constrains OCR throughput. Confidence remains observable without pretending to be calibrated correctness. Fresh 3M FY2022 runs reached 27/27 exact and 7/7 consistent in both pdf-inspector Strategy 2 and Strategy 3, while Strategy 3 still flagged three correct rows below 0.80—direct evidence that confidence must remain diagnostic. Historical artifacts can be recomputed under the new metric semantics, so reports must disclose the scoring version when comparing old exports.

## ADR-0032 — Bind cross-year gold to exact sources and preserve critical evidence
- Date: 2026-08-22
- Status: Accepted; refines ADR-0022 and ADR-0031
- Context: Cross-year accuracy claims require independently transcribed values to match the exact evaluated PDF rather than only a company/year label. The first FY2025 Strategy 3 run selected the face statement and PP&E note but omitted the separate right-of-use-assets page, producing two incorrect derived values even though the full-document Strategy 2 run was correct.
- Decision: Bind every non-assignment audit fixture to exact PDF SHA-256, company and fiscal year, and score only its explicitly audited fields. Keep the assignment FY2022 dictionary as a fallback only for its existing contract. Add a bounded, general critical-evidence signal for explicit right-of-use-asset disclosures so the complete-page gate can retain a lease note within its three-to-five-page budget; do not add company values, golden answers or answer-derived search terms.
- Consequences: Strategy 2 and Strategy 3 now score 27/27 on FY2021–FY2024 and 22/22 on FY2025, where five supplemental Other-assets rows are not disclosed by the source. A different PDF edition cannot inherit those results. The gate remains deterministic and answer-independent, but future field families may require similarly bounded evidence-recall tests.

## ADR-0033 — Admit only screened reports and preserve Unicode corpus identity
- Date: 2026-08-22
- Status: Accepted; refines ADR-0017 and ADR-0020
- Context: A year-stamped two-page Resol news release passed the prior broad `.pdf` discovery heuristic, and Japanese company names collapsed to the same `Unknown_Company` filesystem slug. Either behavior can overwrite or misidentify a company/year benchmark source.
- Decision: Require year evidence plus explicit annual-report, securities-report or equivalent filing language during discovery. Download into a temporary path, run local screening, and refuse canonical replacement unless the result is `ok`. Generate safe Unicode-aware slugs so distinct Japanese company names remain distinct. Keep native JPY filings out of M-USD exact scoring until the benchmark contract adopts an explicit currency policy.
- Consequences: Rejected or ambiguous PDFs cannot replace a verified canonical source, and Japanese manifests preserve company identity. The ten-company Bakuraku corpus can be acquired safely, but its golden-set work remains intentionally blocked on native-currency versus FX-converted evaluation semantics.

## ADR-0034 — Score exact-source gold in native currency and preserve source precision
- Date: 2026-08-22
- Status: Accepted; supersedes the benchmark block in ADR-0033 and refines ADR-0032
- Context: Ten verified Japanese FY2022 filings report JPY at either thousands or whole millions. Treating their values as USD would be false, while conversion would mix exchange-rate policy into extraction accuracy. pdf-inspector also returns empty Markdown for some text-based Japanese PDFs even though PyMuPDF can read their embedded text layer.
- Decision: Carry currency, millions scale and source quantum through prompts, predictions, corpus review and scoring while retaining the legacy `answer_m_usd` JSON key for compatibility. Bind audited gold to PDF SHA-256, company, fiscal year and currency; use half the disclosed source quantum for exact comparison and a propagation-aware reconciliation tolerance. Recover readable embedded text locally when pdf-inspector classifies a document as text-based but emits an empty page, and reserve RapidOCR for pages that still require OCR. Add Japanese headings, schema terms and critical-note signals to the complete-page gate. Keep independently audited corpus tables immutable and viewable beside the exact PDF.
- Consequences: Strategy 2 and Strategy 3 each score 267/267 source-verifiable rows across the ten-company Bakuraku FY2022 cohort. Resol's three undisclosed gross PPE rows remain unscorable instead of inferred. Japanese text PDFs avoid unnecessary whole-document OCR, and every answer surface displays M JPY where appropriate.

## ADR-0035 — Separate corpus-review clarity from the full parser bake-off
- Date: 2026-08-22
- Status: Accepted
- Context: The review sheet showed a generic extraction spinner even when the deployed backend had not yet learned the PDF-hash-bound audited keys, its native PDF viewer defaulted to a cropped page-width view, and the stored-report picker repeated long human-review warnings inside a clipped list. Strategy 3 also repeated its five implementation steps as oversized decorative cards. The requested evaluation is a five-company experiment, not another dashboard surface.
- Decision: Load source-bound audited answers directly through the existing verification GET contract and explain draft generation only when no verified sheet exists for the exact PDF hash. Keep the native searchable PDF iframe but constrain it to the A4 aspect ratio and request page-fit zoom. Reduce corpus rows to company, year/file and a short Verified/Review badge, with a bounded stable scroll region. Remove the five Strategy 3 process cards. Run and checkpoint the evaluation outside the UI as 45 arms: four no-OCR parsers in Strategy 1, the matched four OCR-enabled parsers in Strategy 2, and pdf-inspector plus the intelligent gate in Strategy 3 across five exact-source Japanese FY2022 reports.
- Consequences: Verified tables appear immediately after the current backend is deployed, while an unverified PDF cannot be mistaken for stored gold. Corpus selection is denser without hiding score eligibility. The bake-off preserves failures as observations, resumes from exact matching runs, never injects gold into prompts, and produces Markdown/CSV/JSON evidence without adding a public benchmark widget.

## ADR-0036 — Separate public benchmark evidence from private history and distinguish corpus targets from reports
- Date: 2026-08-22
- Status: Accepted
- Context: Anonymous workspace isolation correctly hid one visitor's runs from another, but it also left the shared dashboard empty even when exact-source benchmark runs existed. Dashboard charts compared individual parsers when the requested experiment was the mean of two arms. The report table repeated companies by fiscal year, and expanding its scope to 100 companies risked presenting research seeds as downloaded or verified reports.
- Decision: Keep `/api/runs` private to the anonymous workspace and add a read-only `/api/benchmark-runs` feed filtered by exact executed PDF SHA-256 against assignment, human, or independently verified sources. Average repeated attempts per parser/report pass before computing equal-weight no-OCR and OCR arm means. Build the corpus library from stored report identities first, then fill to exactly 100 unique companies from the evidence-backed Bakuraku registry; label entries with no stored report as acquisition pending and never score them. Group stored fiscal years under one company row.
- Consequences: Public benchmark charts can show reproducible shared evidence without leaking arbitrary visitor history or letting reruns overweight a parser. The corpus UI reaches the requested 100-company browsing scale while truthfully separating customer/company evidence, report acquisition, answer verification, and gold eligibility. Expanding independently verified gold beyond the existing audited cohort still requires source-bound row-level review; the UI count alone cannot satisfy that evidence requirement.

## ADR-0037 — Allow multiple explicit exact-source fixtures and require honest partial keys
- Date: 2026-08-22
- Status: Accepted; refines ADR-0032 and ADR-0034
- Context: A second independently audited FY2022 cohort should become runtime gold without folding unrelated public controls into the Bakuraku fixture. Several filings disclose a requested subtotal but combine child categories that the 27-row schema asks to split.
- Decision: Load only an explicit filename allowlist of reviewed fixtures, merge by exact PDF SHA-256, and fail on duplicate source authority. For every partial key, require `answers` and `unscorable_rows` to be disjoint and together partition all 27 canonical rows. Preserve directly disclosed subtotals while omitting unsupported child splits; do not infer them from model candidates or force them to zero.
- Consequences: Five new exact sources contribute 116 scorable rows without weakening provenance. Adding another fixture requires a deliberate loader edit, and incomplete audits fail the contract test if any schema row is silently unaccounted for.

## ADR-0038 — Normalize schema locale independently from source language
- Date: 2026-08-22
- Status: Accepted
- Context: Source-bound rows can outlive the UI locale that created them. The prior schema helper translated canonical English labels into Japanese but could not recover canonical English when a stored row already contained a Japanese schema label. The review workspace also constrained the source PDF more aggressively than the evidence table needed.
- Decision: Treat the 27 canonical English labels as the storage/output contract and make UI localization bidirectional for known schema labels. Preserve raw source evidence in its filing language. Use nearly the full viewport for review, assign 46% to the searchable native PDF with single-page vertical fit, and reserve a fixed 42% table column for wrapping evidence.
- Consequences: Selecting English consistently shows English schema labels even for legacy Japanese rows, while Japanese quotations remain faithful evidence rather than machine-translated text. The modal fits substantially more source and evidence content without introducing a second horizontal table scrollbar.

## ADR-0039 — Treat EDINET as a source-bound filing authority, not an arbitrary CDN
- Date: 2026-08-22
- Status: Accepted
- Context: The all-client Firecrawl run returned no candidates for note even though its exact FY2022 EDINET filing was already independently audited. The discovery guard rejected every search result outside the supplied corporate-homepage domain. That protected against parent-company contamination but also made a government filing authority invisible. Six year-specific searches repeated the same false-negative path for every client.
- Decision: Test all 112 Bakuraku clients without pre-classifying their filing availability. Accept an off-domain search result only when its host is an explicit Japanese FSA/EDINET filing domain and its title or description contains the normalized exact requested legal entity; continue rejecting generic CDNs and parent-company results. Search once for the issuer's PDF filing series and continue to require a year plus securities/annual-report language, successful local PDF screening, exact SHA pinning and two independent reviews before gold status. Persist an availability ledger for every client/year so discovery, download and gold cannot be conflated.
- Consequences: Firecrawl can reach authoritative Japanese filings without weakening same-entity provenance. Private/no-report clients consume one bounded series search rather than six near-duplicates. EDINET discovery remains only acquisition evidence: downloaded documents still do not become benchmark gold automatically, and disclosure-CDN links need an official-page chain or a separately audited source record.

## ADR-0040 — Present completed execution time and strategy identity, not the last micro-step
- Date: 2026-08-23
- Status: Accepted
- Context: After a Strategy 3 pass completed, the live card remained on the `output` step and displayed its roughly 10 ms file-write duration. The result looked impossible because it was visually interpreted as the entire pdf-inspector/OCR/gate/model runtime. The compact comparison omitted pages, token estimate and model timing, and historical page filtering trusted only an experiment label.
- Decision: Once a pass is complete, show its backend-recorded total elapsed seconds regardless of the last active step. Format sub-second values as `<1 s`, values below one minute in seconds, and longer values as minutes plus seconds. Show report, parser/mode, exact accuracy, field coverage, pages, estimated tokens, parse time, model time and total time in the completed comparison and latest-output summary. Scope history by both the page's experiment and its exact allowed parser keys.
- Consequences: Strategy 3 timing is directly comparable with Strategies 1 and 2, no completed run is mislabeled in milliseconds, and a malformed or stale Strategy 2 record cannot appear on the Strategy 3 page. Low-level step durations remain available in stored events for debugging without being promoted as the headline runtime.

## ADR-0041 — Retry observed Firecrawl gaps by exact company and year
- Date: 2026-08-23
- Status: Accepted
- Context: The first corrected 112-client series sweep found multiple years for Raksul but missed known audited years for note and Resol. A single corporate-homepage map plus general PDF-series search is efficient evidence of availability, but it is not a complete acquisition strategy for inconsistently indexed Japanese filings.
- Decision: Preserve the first-pass job as an availability audit. Add an explicit deep-search mode that, for each year still missing after map, page-link and series search, runs both an exact-company Japanese securities-report query and an exact-company English annual-report query. Keep the same official-domain or exact-entity EDINET trust rule, local annual-report screening and SHA pinning. Invoke deep mode only for first-pass gaps rather than recrawling successful company/years indiscriminately.
- Consequences: The retry spends substantially more Firecrawl credits and time only where empirical gaps exist. It improves search recall without accepting arbitrary search PDFs, but it still cannot guarantee 50 complete five-year client series; the final ledger must report any residual absence honestly, and only a separate two-pass source audit can create gold.

## ADR-0042 — Bind each discovered PDF to one annual reporting period
- Date: 2026-08-23
- Status: Accepted; refines ADR-0033 and ADR-0041
- Context: The first 112-client Firecrawl audit downloaded the same Imperial Hotel quarterly PDF as two fiscal years, accepted a Nishio quarterly report, and assigned a Striders FY2026 filing to FY2025 because the old checks accepted any requested year mentioned in a search snippet or PDF.
- Decision: Reject quarterly, interim and earnings-release vocabulary during discovery. Derive one primary year per search result by preferring title, then URL, then description, without hiding a newer out-of-range period. After download, identify the selected balance-sheet page and require the expected fiscal year to be the newest calendar year printed on that statement when year evidence is present. Preserve the raw audit ledger, delete invalid live-corpus entries and never promote discovery output to gold.
- Consequences: Comparative dates can no longer cause one PDF to occupy multiple company/year identities, and an FY2026 document cannot be backfilled into FY2025. Search recall may be lower for ambiguous snippets, but deep exact-year queries can recover candidates without weakening source identity.

## ADR-0043 — Normalize display spacing before document-type admission
- Date: 2026-08-23
- Status: Accepted; refines ADR-0042
- Context: Firecrawl returned `四 半 期 報 告 書` with whitespace between Japanese characters. The semantic text was still "quarterly report," but a literal exclusion for `四半期` did not match and the file reached the corpus.
- Decision: Apply Unicode NFKC normalization and remove whitespace solely for the non-annual document-type check, while preserving original titles and descriptions as evidence. Delete every live document admitted through the older rule and retain it only in the audit job record.
- Consequences: Typography cannot turn a quarterly/interim/earnings document into an annual-report candidate. Original source metadata remains inspectable, and no search/download result becomes gold without the separate exact-source review contract.

## ADR-0044 — Recover only exact-source client gold and retire the duplicate UI
- Date: 2026-08-23
- Status: Accepted; tightens ADR-0032, ADR-0034 and ADR-0036
- Context: Production corpus deletion left a recoverable archive containing verified sources alongside provisional candidates and non-Bakuraku public controls. The assignment FY2022 dictionary was still selected by company/year/currency labels, so a different PDF could inherit gold. Firecrawl also stopped at corporate homepages even when they linked to a same-domain securities-report library. A separate Streamlit application and its Pandas dependency remained installed despite Flask/React being the maintained product.
- Decision: Admit assignment gold only when the source SHA-256 is the exact supplied 3M FY2022 hash. Restore archives by recomputing every PDF hash and accepting only that assignment source or an explicit SHA-bound fixture whose exact normalized company occurs in the Bakuraku registry. Exclude provisional reports and benchmark controls. Pin 3M first in corpus APIs and UI. Follow at most four same-domain official annual/securities-report library pages before applying the existing PDF identity, year and screening gates. Delete the unused Streamlit surface and its exclusive dependencies.
- Consequences: Labels and filenames can no longer grant benchmark authority, corpus recovery cannot silently turn public controls into client gold, and the application has one maintained delivery stack. Authenticated/private PDFs remain usable only with caller-authorized headers, cookies, browser profiles or local file parsing; Firecrawl does not authorize bypassing access controls, and discovery success still does not create gold without two source reviews.

## ADR-0045 — Preserve balanced PDF filenames from Firecrawl Markdown
- Date: 2026-08-23
- Status: Accepted
- Context: A live official-library retry returned an Alpico PDF whose filename contains a Japanese parenthesized print/view annotation. The Markdown-link expression stopped at the filename's inner closing parenthesis, removed the `.pdf` suffix and caused a false 404.
- Decision: Scan Firecrawl Markdown destinations in linear time while tracking balanced parentheses, and keep the raw complete destination for download and screening. Continue to apply annual-document vocabulary, fiscal-year identity, official-source trust and local PDF screening after URL recovery. Exercise the scanner against a 500 KB regression page to prevent pathological backtracking from occupying the API worker.
- Consequences: Ordinary Japanese IR filenames remain downloadable without relaxing report admission. An integrated report may now reach screening, but it still cannot become corpus gold merely because its link was parsed successfully.

## ADR-0046 — Admit exact-entity public-gazette balance sheets only as partial gold
- Date: 2026-08-23
- Status: Accepted; refines ADR-0037 and ADR-0044
- Context: Thirteen Bakuraku-client companies already had source-bound full-report keys, but the requested forty-client corpus could not be reached from complete annual reports alone. Broad Firecrawl searches frequently returned parent-company filings or pages where a client was merely mentioned. Public gazette announcements provide exact-entity balance-sheet images for additional private clients, but condensed statements do not disclose every one of the canonical 27 rows and the searchable mirror is not itself an official company domain.
- Decision: Admit a public-gazette source only when its normalized legal entity exactly matches the Bakuraku registry and its fiscal date falls in FY2020–FY2025. Pin the downloaded source image and the one-page derived PDF by SHA-256. Require local RapidOCR to read the indexed Total Assets amount in at least two balance-sheet positions, require an independent gazette-index transcription of the same amount, and require the balance equation to reconcile. Score only Total Assets; mark the other 26 canonical rows explicitly unscorable. Preserve the mirror provenance without calling it an official issuer source. Firecrawl headers, cookies and browser profiles may carry authorization supplied by the caller, but discovery never bypasses access controls or creates gold by itself.
- Consequences: Twenty-seven new partial keys combine with thirteen existing full-report client companies to produce forty unique Bakuraku-client companies, while 3M FY2022 remains a separate assignment control pinned first. The expanded corpus has broad exact-source coverage without fabricated values, although condensed statutory filings contribute one scorable row rather than a full 27-row key. Complete issuer reports remain preferable and may supersede these partial keys after the same two-pass source audit.

## ADR-0047 — Verify discovery identity inside the PDF and separate A4 evidence from full-document search
- Date: 2026-08-23
- Status: Accepted; tightens ADR-0042 and ADR-0044
- Context: An accidental all-client crawl admitted seven misleading results: six belonged to different companies and one was a shareholder-meeting notice. Search metadata looked plausible, and the old rejection branch did not run when the registry lacked an official domain. Safari also ignored embedded PDF fit fragments, leaving a small page at the left of a mostly blank review pane.
- Decision: Search/deep-search candidates without an official-domain match must be trusted public filings or be rejected. Before canonical replacement, locally extracted PDF text must confirm both expected company identity and annual/securities-report type while proxy, meeting, quarterly and interim material is rejected. Render the detected page to a SHA-bound PNG for deterministic A4 fit and retain the original PDF as a separate searchable mode. Currency conversion is display-only; native filing values remain the scoring and approval contract.
- Consequences: Recall is intentionally lower when identity cannot be established, but misleading search metadata cannot overwrite a corpus slot. Human review gets a legible single page without losing full-report search, and changing display currency cannot alter exact accuracy or stored gold.

## ADR-0048 — Keep batch reports simultaneously visible and complete only uniquely solvable nulls
- Date: 2026-08-23
- Status: Accepted
- Context: Durable extraction jobs correctly emitted every selected PDF at `batch_start`, but the live component grouped the batch and rendered only one active report, hiding cross-company queued/running work. The exact 3M FY2022 Strategy 3 pass returned 26 correct values and a null Deferred Charges row while its own extracted values established `46,455 - 14,688 - 31,767 = 0`.
- Decision: Render one persistent live card per selected PDF and summarize batch state without replacing cards as activity advances. After contract validation and before confidence gating, complete a null only when exactly one term in a canonical subtotal identity is missing and every other term is numeric. Preserve all non-null model values, set derived confidence from the weakest operand, record the identity and result in evidence/artifacts, and apply the same derivation when historical runs are read. Never consult assignment or corpus gold during completion.
- Consequences: A two-report selection is visible as two cards at once and completed results accumulate rather than appearing serially. The affected 3M FY2022 run scores 27/27 using transparent balance-sheet algebra; conflicting values still fail reconciliation, and ambiguous identities with two or more nulls remain unmodified and unscored.

## ADR-0049 — One provider UI: merged GLM tile with endpoint toggle and wired OpenRouter models
- Date: 2026-08-23
- Status: Accepted
- Context: Settings offered OpenRouter, "Z.AI (GLM)" and "Z.AI Coding Plan endpoint" as three sibling tiles even though the two GLM entries differ only in base URL, and OpenRouter had no curated model choice while the owner plans to standardize on an OpenRouter key.
- Decision: Render one GLM (Z.AI) tile whose Coding Plan / Open Platform endpoint is picked by a segmented control that still maps onto the existing `zai` / `zai-coding` provider keys, so saved settings and the backend contract are unchanged. Give the OpenRouter tile two wired selectable models — `google/gemini-3.7-flash` (new default) and `openai/gpt-5-mini` — while free-text model entry and the datalist remain.
- Consequences: Switching GLM endpoints still requires re-entering the matching key (coding-plan keys are endpoint-bound). Benchmarks default to a pinned cheap fast OpenRouter model once a key is saved; no persisted provider setting migrates.

## ADR-0050 — Freeze the public corpus surface: provenance explainer instead of discovery controls
- Date: 2026-08-23
- Status: Accepted; supersedes the public discovery UI portion of ADR-0047
- Context: The corpus is complete for benchmarking and the Firecrawl account holds limited credits; leaving "Discover and download reports" and the 112-customer loader public invited accidental crawls like the one ADR-0047 cleaned up.
- Decision: Remove the discovery-job and activity cards from the Report corpus page. Replace them with a provenance card that explains the one bounded Firecrawl acquisition pass (map/search official sources → direct download and local screening → SHA-256 pinning and verification) plus a company tile grid (favicon or monogram, fiscal years) for every company with stored data. Backend discovery endpoints and the CLI worker remain for owner-driven use.
- Consequences: Public visitors cannot start crawls or spend credits; the corpus page is documentation plus library. Regression tests assert the discovery controls stay gone.

## ADR-0051 — Strategy 3 evaluation loop: one bounded evidence retry over unsent ranked pages
- Date: 2026-08-23
- Status: Accepted
- Context: When the intelligent scanning gate's three-to-five-page packet lacked the evidence for some schema rows, the model returned nulls and the run simply scored lower; nothing verified whether the needed pages had actually been retrieved or fetched more.
- Decision: After validation, identity completion and confidence gating, if Strategy 3 still has null rows and readable ranked pages remain unsent, run exactly one follow-up model call: up to three next-best pages (global gate score plus a bonus for the missing rows' schema terms) with a prompt that names only the missing rows. The retry can only fill nulls — it never overwrites a first-pass value — and its pages, scores, usage, recovered rows and any failure are persisted under `evidence_retry`. A retry failure never fails the run. Extraction now retains all readable unified pages in memory (`ExtractedText.retained_pages`) without persisting page bodies per run.
- Consequences: Missing-evidence failures become a verifiable, bounded recovery path with an audit trail; worst case adds one model call. Prompts still never contain gold.

## ADR-0052 — Year expansion with manual EDINET acquisition and dual-pass derived gold
- Date: 2026-08-23
- Status: Accepted; extends ADR-0044/ADR-0046
- Context: The corpus held mostly one fiscal year per company. Firecrawl credits are reserved, but IR BANK's per-ticker EDINET indexes list annual securities-report docIDs that download anonymously from disclosure2dl.edinet-fsa.go.jp. Document-type screening was rejecting genuine annual reports because they cross-reference their own quarterly filings; three gazette fixtures recorded thousand-yen precision for million-yen sources.
- Decision: Acquire the 13 exact-source clients' missing FY2020–FY2025 filings (60 found, 4 honestly unavailable pre-IPO) through the existing screening/manifest path. Fix `_is_annual_document` to trust the filing's own cover label (【提出書類】) over incidental cross-references. Derive gold for all 61 gold-less documents with a deterministic dual-pass engine: PyMuPDF layout parse of the primary balance sheet (consolidated when present), documented mapping conventions, exact identity closure, then independent pypdf re-location of every admitted printed value; ambiguity (unknown labels, loan maturity splits, long-term allowance targets, net-only tangibles) marks rows unscorable, never guessed. Store per-source print precision (`source_value_quantum`) from the actual gazette/statement unit.
- Consequences: 102 corpus documents across 41 companies, all gold-backed (101 independently verified, 1 assignment control); the engine reproduces the human-audited FY2022 answers with zero mismatches on 254 comparable rows. Judgment rows on new years stay unscorable until a human review or a deeper audited pass upgrades them.

## ADR-0053 — Published Gemini benchmark blends efforts per arm role
- Date: 2026-08-24
- Status: Accepted
- Context: The Gemini 3.7 Flash medium-effort sweep completed all 102 Strategy 3 arms and 53 Strategy 2 arms before OpenRouter credits ran out, leaving Strategy 1 mostly covered only by the earlier low-effort run. Matching the dashboard source on "any gemini run" would pool low- and medium-effort passes of the same arm, double-counting documents and mixing effort tiers within one strategy series.
- Decision: `runMatchesSource` for the Gemini source selects medium-effort runs for Strategy 2/3 and low-effort runs for the Strategy 1 control only (`experiment === 'no_ocr'`), so exactly one effort tier represents each strategy. The S1 control is a no-reasoning-sensitive PyPDF baseline, so the low-effort pass is representative; remaining medium S2 arms replace nothing until they exist and match the same rule.
- Consequences: The published Gemini view is internally consistent today and self-heals as the medium sweep completes (medium S2 runs appear as they land; S1 stays pinned to low until a deliberate rule change). GLM sources remain split by thinking mode, unaffected.


## ADR-0054 — Public deployment is a read-only control plane
- Date: 2026-08-24
- Status: Accepted
- Context: Caddy forwards the whole public domain to Flask with no authentication; CORS never blocked direct HTTP. Any caller could replace the prompt, change credentials, start paid jobs, delete runs, or overwrite golden answers.
- Decision: A server-side before_request gate, enabled by LEDGER_PUBLIC_READONLY=1 in the production environment file, rejects every mutating request except the demo surfaces (/api/extract*, /api/extraction/jobs, /api/uploads, /api/traffic) with HTTP 403. Operator changes ship through the git deploy channel. Full authentication (per-user claims-derived workspaces) remains the follow-up.
- Consequences: The public dashboard and demo keep working; the control plane is writable only from the operator's channel. The production Settings UI cannot save changes — by design.

## ADR-0055 — Deliver the technical report as native Word with code-generated portrait figures
- Date: 2026-08-24
- Status: Accepted
- Context: The earlier report used a manually simulated contents page, mixed decorative colors, and wide text-heavy images that were difficult to read on portrait Word pages. The submission must retain the supplied cover while remaining editable and understandable to non-specialists.
- Decision: Use native Word Heading 1/2 styles and an updatable linked table of contents with dotted leaders and right-aligned page numbers. Use MS Mincho and black text for all report content. Generate technical figures from HTML/SVG code at 2400×3200, restrict figure labels to short Japanese phrases, place each figure on an A4 portrait page, and explain the evidence and interpretation in adjacent prose. Preserve benchmark artifacts and product code as read-only evidence.
- Consequences: The report is a 20-page A4 Word artifact with reliable navigation and print layout. Figures remain reproducible from source code and can be regenerated without image-generation tools. Future report edits must refresh the Word TOC and repeat page-by-page rendering checks before delivery.

## ADR-0056 — Use wide inline architecture maps and report retry metrics as conditional observations
- Date: 2026-08-24
- Status: Accepted; supersedes the figure placement and page-count details of ADR-0055
- Context: Full-page vertical box diagrams did not match the requested reference style, and benchmark `reported_prompt_tokens` omits evidence-retry usage. The run artifacts record successful retry tokens, but 2 GLM and 4 Gemini failed retry calls have no provider usage block. Retry-triggered documents are also a harder, non-random subset, so they cannot be treated as a paired architecture experiment.
- Decision: Generate five 2400×1350 code-based figures and embed them at text width within portrait Word pages. Use left-to-right semantic diagrams for problem decomposition, hypothesis progression, and the PDF Inspector → selective OCR → selected pages → LLM → validation → output flow, with an explicit one-time retry branch. Present Strategy 3 as two conditional observed modes: `単発抽出ベースライン（Single-pass baseline）` and `選択的再試行アーキテクチャ（Selective retry architecture）`. Include whole-pipeline retry timing, recorded token components, recovered-row outcomes, and an explicit lower-bound marker where failed calls lack usage. Do not estimate missing tokens or claim a causal comparison.
- Consequences: The final report is 19 A4 pages, figures remain legible without occupying full pages, and the evaluation communicates both retry cost and data limitations honestly. Any future causal claim requires a same-document counterfactual benchmark that stores pre-retry scores and complete usage for every call.

## ADR-0057 — Separate retry cohort profiles from same-document recovery evidence
- Date: 2026-08-24
- Status: Accepted; tightens ADR-0056
- Context: The earlier quality figure placed the no-retry and retry cohorts side by side even though retry is triggered by harder documents. Its token stack also looked like a complete total despite missing provider usage for two GLM and four Gemini failed retry calls. Table continuation and forced major-section breaks created avoidable layout gaps.
- Decision: Use the agreed labels `単発抽出ベースライン` and `フルリトライアーキテクチャ`, and describe their time and per-document token values only as different-cohort profiles. Mark retry token values as lower bounds. Make the sole retry-benefit claim from the same triggered documents by reporting initial missing rows, recovered rows and rate, final missing rows, improved documents, residual arithmetic failures, incremental latency, incremental tokens, usage coverage, and failed calls. Keep every table row intact, repeat only column headers, place captions outside tables, and remove page breaks that strand short continuations. Record benchmark hashes, model settings, parser/OCR versions, and run dates in the report.
- Consequences: The report distinguishes descriptive cohort differences from evidence of actual retry recovery, does not turn incomplete token usage into a false total, and renders as 17 A4 pages without spacer-only pages. Product code and benchmark snapshots remain unchanged.

## ADR-0058 — Persist Word fields before exporting the matching PDF
- Date: 2026-08-24
- Status: Accepted
- Context: Refreshing the native table of contents on document open updated Word's in-memory view without reliably updating the DOCX file on disk. Exporting before an explicit same-name Word save could therefore produce a PDF whose pagination and TOC state differed from the delivered DOCX.
- Decision: For the release pair, refresh fields, explicitly save the DOCX under its final name, confirm Word's stored page metadata and visible pagination, and only then export the matching PDF from the same open document. Close without a further save after export, and verify the PDF independently with `pdfinfo`, text extraction, and page renders. Give the TOC title an explicit 18 pt top gap after its page break so Word and PDF exports keep it clear of the printable top edge.
- Consequences: Both final artifacts now resolve to 17 A4 pages with the same linked TOC and section starts. Future report releases must follow this save-before-export order; a normal Save after an automatic field refresh is not sufficient evidence that the field result reached disk.

## ADR-0059 — Compare strategies on one document and keep retry evidence out of the main result
- Date: 2026-08-24
- Status: Accepted; supersedes the main-results chart scope in ADR-0057
- Context: Retry-triggered and non-triggered runs are different cohorts, so their time and token bars distracted from the requested comparison of the three input strategies. The architecture figures also used oversized bespoke icons, and the report mixed model-provider timing with input-strategy conclusions.
- Decision: Use one small, consistent Lucide-style stroke icon system for Figures 1–3. Use the same 3M FY2022 document, model, reasoning setting, and temperature for the Strategy 1/2/3 speed and input-token charts. Normalize speed to Strategy 1 and show no sample-count labels in these same-document charts. Remove the retry before/after figure and retry evaluation subsection from the current report. Report full-corpus Strategy 3 accuracy separately by stored model/reasoning snapshot, with macro and micro calculations and completion counts.
- Consequences: The 15-page report now answers two distinct questions without cohort confusion: model/reasoning accuracy comes from the saved corpus snapshots, while speed and token efficiency come from a controlled same-document three-strategy comparison. The bounded retry remains visible in the architecture but is not presented as a measured headline result.

## ADR-0060 — Preserve report aggregates and disclose a missing historical raw snapshot
- Date: 2026-08-24
- Status: Accepted
- Context: The GLM-thinking benchmark output was still being updated after the report export. Its live contents no longer match the 99.71% historical aggregate printed in Table 3a, and the exact row-level snapshot behind that value was not archived.
- Decision: Do not overwrite or roll back the live benchmark. Store the exact Table 3a aggregate values in a sidecar JSON manifest, label them as report-generation historical values, retain the historical source digest for audit context, and state explicitly that the GLM-thinking row cannot be fully recomputed without the missing raw snapshot.
- Consequences: The report remains honest about the evidence available at export time and no longer overclaims reproducibility. Future runs must archive immutable row-level results before using them in a release report.

## ADR-0061 — Size diagram icons with SVG symbols and reserve a branch gutter
- Date: 2026-08-24
- Status: Accepted; refines ADR-0059
- Context: The report diagrams defined reusable icons as ordinary `<g>` elements. SVG `<use>` width and height do not scale a referenced group, so several glyphs appeared oversized or off-center. In the final architecture figure, the direct-text/OCR split and merge occupied the same narrow horizontal interval as the evidence-page label, while the retry connector crossed primary labels at report scale.
- Decision: Define reusable glyphs as `<symbol viewBox="0 0 24 24">` assets, place them with explicit 22–30 px dimensions, and keep one consistent circular-node scale. Enlarge the final architecture figure to the maximum safe portrait text width. Reserve a wider gutter between the text-layer decision and evidence pages; use smaller auxiliary nodes for direct text and selective OCR; separate their labels vertically; merge them before the evidence node. Route the one-time retry from validation below the full main flow and return it to the text-layer decision without crossing labels.
- Consequences: Icon dimensions are deterministic across Chromium and Word exports, the branch is readable at normal page scale, and the architecture remains a compact left-to-right figure instead of expanding into a full-page vertical diagram. Future figure edits must be checked in the exported PDF, not only in the standalone SVG/PNG.

## ADR-0062 — Recompute release evidence from the current benchmark snapshots
- Date: 2026-08-24
- Status: Accepted; supersedes ADR-0060 and the same-document chart scope in ADR-0059
- Context: The three full-corpus benchmark JSON files were replaced with complete, traceable 102-document snapshots. Retaining the earlier historical aggregate and its missing raw snapshot would make the report stale. The assignment also requires the hypotheses, trial-and-error, prompt/source assumptions, final output, accuracy, failures, solution outlook, and generality to be visible in the submitted document.
- Decision: Recompute every reported aggregate directly from the current GLM-thinking, GLM-no-thinking, and Gemini benchmark records without modifying those records. Report completion separately from macro and pooled/micro accuracy. Compare Strategy 1/2/3 speed and mean input tokens only on the same 75 documents completed by all three GLM-thinking arms; preserve the 3M FY2022 result as the assignment-specific final-output check. Place every external figure caption below and centered, use `Active RAG` consistently, and add explicit prompt/source excerpts plus a requirement-compliance appendix. Refresh Word fields before exporting the matching PDF.
- Consequences: The release is an 18-page synchronized DOCX/PDF pair whose values are reproducible from the current snapshots. Strategy 3 is not presented as universally fastest: on the matched 75 documents its speed index is 0.95× versus Strategy 1, while mean input tokens fall by 92.1% and pooled/micro accuracy reaches 99.12%. Historical non-reproducible values are removed from the report.

## ADR-0063 — Count all recorded model-call tokens and reproduce the required output contract
- Date: 2026-08-24
- Status: Accepted; corrects the token-accounting and release-size consequences of ADR-0062
- Context: The first refreshed report labeled the benchmark's initial-prompt field as total input and therefore understated Strategy 3 cost by omitting contract repair and the bounded evidence retry. The assignment also specifies a five-column final table, while a value-only appendix was insufficient to prove conformance to that contract.
- Decision: Keep the full-corpus model tables explicitly labeled as mean initial input tokens. For the matched 75-document strategy comparison, sum input-token usage from every recorded model call in each `prediction.json`, including repair and evidence-retry calls; do not estimate missing usage. Reproduce the assignment's exact five-column structure—classification, subclassification, item, description, and answer—for all 27 rows. Preserve current benchmark files read-only and bind GLM-thinking results to SHA-256 `452a747733a251f8f41a87b47b0dee5b39bda2cdedaad1e3b46dad19319f07fb`.
- Consequences: On the matched cohort, Strategy 1 averages 97,306 all-call input tokens, Strategy 2 averages 96,768, and Strategy 3 averages 9,586, a 90.1% reduction from Strategy 1. The current GLM-thinking Strategy 3 snapshot reports 102/102 completion, 99.23% macro accuracy, 99.14% pooled/micro accuracy, P50 256.92 seconds, and 6,712 mean initial input tokens. The synchronized release is 20 A4 pages in both Word and PDF and includes the complete required output table.

## ADR-0064 — Use Gemini for the controlled strategy charts and leave Luna pending
- Date: 2026-08-24
- Status: Accepted; supersedes the matched-cohort chart values in ADR-0062 and ADR-0063
- Context: The report charts needed to reflect the updated Gemini benchmark while retaining a same-document, same-model comparison of the three input strategies. The requested GPT-5.6 Luna benchmark could not be launched because the repository exposes no Luna model identifier or callable provider route.
- Decision: Build Figures 4–5 and Table 4 from the 75 Gemini 3.7 Flash documents completed by all three strategies. Count all recorded model-call input tokens, including repair and evidence-retry calls. Report Strategy 1/2/3 P50 speed indices as 1.00×, 1.09×, and 1.30×, and all-call input-token averages as 88,936, 89,414, and 9,715. Do not substitute another model for Luna and do not add a third-model result until an exact callable endpoint and official model ID are available. Preserve the user's saved DOCX and publish the change as a versioned revision.
- Consequences: The released strategy comparison is traceable to one Gemini cohort and shows an 89.1% Strategy 3 token reduction versus Strategy 1. The report explicitly marks the Luna comparison as pending instead of presenting synthetic data. The exact runtime prompt and reader-facing reproduction instructions are included without internal hashes or answer leakage.

## ADR-0065 — Consolidate the report and use one-page prompt plus code appendices
- Date: 2026-08-25
- Status: Accepted; supersedes the versioned-artifact and six-page prompt layout in ADR-0064
- Context: Multiple Word/PDF versions caused stale exports and a Word in-memory copy introduced stray cover text. The full prompt was complete but fragmented over six pages, while the source-code appendix did not visibly separate the main Python files as code blocks. A read-only live check also disproved the draft's OpenRouter claim: the hosted settings reported `zai-coding` and `glm-5.3`.
- Decision: Keep only `バクラク事業部技術_実験報告書_完成版.docx` and its matching PDF in `docs/`; move duplicate report artifacts to the macOS Trash. Place the complete runtime prompt on one A4 page using three ordered columns at small type. Show concise exact excerpts from `extraction.py`, `intelligent_scan.py`, `pipeline.py`, and `prompts.py` in separate shaded code blocks. State the observed hosted provider truthfully and do not promise a fixed trial count. Export the PDF only from a freshly reopened Word document and render-check every page.
- Consequences: The final pair is synchronized at 24 A4 pages, the prompt remains exactly reconstructable at 9,322 characters, the Python implementation is visibly formatted as code, and the report no longer contains stale version files, duplicate figure titles, a cover artifact, or a blank final page. Luna remains explicitly pending until a callable endpoint and official model ID exist.

## ADR-0066 — Quota exhaustion is classified from the error code and message, never the serialized error
- Date: 2026-08-25
- Status: Accepted
- Context: `_quota_message` matched its markers against `json.dumps(error)`, so a request id containing `1308`, a key named `quota_reset_at`, or the word "credits" in marketing prose all produced `QuotaExhaustedError`. That exception is raised before any retry and both batch runners treat it as terminal, so a single transient 429 abandoned every remaining file in a paid run.
- Decision: Match quota phrases against the provider's `message` field only, narrow them to phrases that unambiguously mean an exhausted allowance, and compare numeric provider codes against `error.code`/`error.type` exactly rather than as substrings. Where the classification is uncertain, fall through to the ordinary retry path.
- Consequences: The two failure directions are no longer symmetric by accident. A missed quota signal costs one retry; a false quota signal costs a whole batch, so the classifier is now biased toward retrying. Genuine exhaustion (`usage limit reached`, `insufficient balance`, code `1308`) is still detected, and both directions are pinned by regression tests.

## ADR-0067 — Public-deployment hardening is deferred to the standalone package, not applied to the live demo
- Date: 2026-08-25
- Status: Accepted
- Context: An audit found the public deployment has no inbound rate limiting and no authentication on the endpoints that spend the operator's LLM budget, no security headers of any kind, an anonymous endpoint that reveals the first and last four characters of the API key, unbounded staging state, and no PDF content validation before untrusted bytes reach native parsers.
- Decision: Record all eight findings with citations and severities in `agent/errors.md`, and change nothing on the deployed site. The owner's judgement is that gating the public demo costs more than the exposure. The same defects are fixed in the standalone submission package, which is the artifact that gets reviewed.
- Consequences: The live site keeps its zero-friction demo and its current spend exposure; the decision is written down with evidence so it can be revisited rather than rediscovered. Anyone reading `server.py:122` should note the "(rate-limited)" comment there describes outbound concurrency, not request volume.
