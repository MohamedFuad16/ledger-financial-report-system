# Dependency & impact graph

> Regenerate after structural changes. Generated data lives beside this file; the high-level diagram is `architecture.d2` → `architecture.svg`.

| Module | Depends on | Depended on by | Blast radius |
|---|---|---|---|
| `schema.py` | — | models, prompts, normalize, reconcile, pipeline, server, tests | Changes affect the contract, prompt, assignment fallback gold, exact-SHA audited gold, scoring, API, and UI |
| `extraction.py` | parser libraries | pipeline, server, tests | Changes affect every strategy run and preflight estimate |
| `intelligent_scan.py` | fixed schema | Strategy 3 extraction, focused tests | Changes affect Strategy 3 page ranking, selected evidence and model input size |
| `pipeline.py` | extraction, prompts, providers, contract, scoring | server, React API consumers, tests | Changes affect all executions and stored predictions |
| `server.py` | pipeline/settings/schema/corpus, evidence-backed company registry | browser client | Changes affect every client workflow, the source-verified dashboard feed, and 100-company corpus target library |
| `traffic.py` | Upstash REST, AWS SES v2 | `server.py` | Changes affect private visit persistence and owner notifications |
| `corpus/service.py` | discovery/fetch/manifest | Flask corpus jobs, CLI worker | Changes affect discovery and source acquisition only; answer mapping is on-demand through the pipeline |
| `corpus/discover.py` | Firecrawl client | corpus service | Changes affect link ranking and Firecrawl credits |
| `corpus/client.py` | Firecrawl REST API | discovery, runtime-settings verification | Changes affect discovery calls and credential-save safety |
| `runs/_corpus_jobs` | server corpus-job registry | corpus job list/detail API, client rehydration | Changes affect navigation-safe discovery visibility and restart audit state |
| `corpus/fetch.py` | download/screen/manifest | corpus service | Changes affect PDF trust, Unicode canonical naming, screening-before-replacement, and SHA-bound candidate artifacts |
| `corpus/manifest.py` | schema, file/OS locks | corpus API, pipeline scoring | Changes affect canonical corpus identity, human approval, deletion, and exact-accuracy eligibility |
| `benchmark_data/*_gold.json` (explicit allowlist in `schema.py`) | twice-audited exact PDF sources | schema, corpus review, pipeline scoring | Changes affect native-JPY gold, citations, immutable review tables, and exact-source accuracy; duplicate hashes are rejected |
| `research/benchmark/run_five_company_bakeoff.py` | pipeline, source-bound gold, five pinned FY2022 PDFs | benchmark Markdown/CSV/JSON | Changes affect the reproducibility and completeness of the 45-arm cross-parser comparison |
| `research/benchmark/acquire_fy2022_expansion_sources.py` | reviewed exact-source registry, corpus fetch/screen/manifest | five-report FY2022 expansion corpus | Changes affect exact-source acquisition and replacement safety |
| `research/corpus/discover_statutory_filings.py` | Bakuraku registry, Firecrawl search API | statutory candidate inventory | Changes affect broad public-filing recall only; search results are never gold |
| `research/corpus/discover_gazette_filings.py` | Bakuraku registry, public gazette index | exact-entity gazette candidate inventory | Changes affect statutory source discovery and alias matching, not runtime extraction |
| `research/benchmark/materialize_statutory_gold.py` | gazette inventory, RapidOCR, canonical schema, corpus manifest | `bakuraku_statutory_gold.json`, statutory audit, exact-source PDFs | Changes affect the 27-company partial-gold cohort, hashes, reconciliation evidence, and scorable-row boundaries |
| `research/benchmark/audit_forty_client_corpus.py` | Bakuraku registry, three explicit gold fixtures, canonical schema, corpus manifest and source bytes | forty-client completion audit | Changes affect whether the maintained client corpus can be claimed complete |
| browser client | Flask API, locale provider | users | Changes affect all visible product behavior |
| `frontend/src/pages/StrategyPage.tsx` | extraction job API, parser metadata, corpus picker | three strategy routes | Changes affect all active extraction controls, including Strategy 3 execution and rehydration |
| `frontend/src/lib/api.ts` | Vite API origin | every client API call | Changes affect cross-origin deployment, visit reporting, staging, settings and extraction |
| `deploy/aws/` | EC2, SSM, Gunicorn, Caddy, live/seed manifest merge | production API | Changes affect instance bootstrap, TLS, persistent service startup, and corpus-safe rollout |
| `frontend/src/lib/i18n.tsx` | browser locale/storage | all React pages and shared UI | Changes affect all translated product copy |
| `frontend/src/components/ExecutionPipeline.tsx` | SSE-derived execution state, locale provider | strategy pages | Changes affect live parser progress and task state |
| `frontend/src/components/CorpusPicker.tsx` | corpus manifest, locale provider | strategy pages | Changes affect stored-report search and single/batch selection |
| `frontend/src/components/RunTable.tsx` | runs API, row-local result sheet | dashboard, history, strategy pages | Changes affect where every stored result opens |
| `frontend/src/lib/format.ts` | stored run identities and metrics | dashboard, strategy comparison, tests | Changes affect matched-cohort membership, parser averages, and equal-weight OCR/no-OCR arm means |
| `runs/_extraction_jobs` | server job registry | job list/detail/events API, client rehydration | Changes affect navigation-safe long-running extraction state |

Hotspots: `schema.py`, `pipeline.py`, `corpus/service.py`, and the client/API boundary. Corpus review prefill now crosses `server.py` → `pipeline.py` → `corpus/fetch.py`; Firecrawl is no longer on that path.
> **DEGRADED GRAPH** — generated by heuristic import scan (dynamic imports,
> aliases, and re-exports may be missing). Install dependency-cruiser / madge
> (JS/TS) or pydeps (Python) and re-run for a precise graph.


## Last generated
- 2026-08-23 via `graphify update . --no-cluster` (1,123 nodes, 2,492 edges) plus the curated research-pipeline rows above.
