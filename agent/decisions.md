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

# Decisions (ADRs) — append-only

## ADR-0001 — Adopt the `agent/` knowledge base
- Date: 2026-08-20
- Status: Accepted
- Context: The repository had no compact architecture, state, or impact map despite a multi-module pipeline and a large UI surface.
- Decision: Maintain a routed `agent/` knowledge base, rolling state, append-only ADRs, and deterministic dependency/architecture graphs.
- Consequences: Future work can retrieve the relevant subsystem without rescanning the repository, but structural changes must refresh the graph and state.

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
