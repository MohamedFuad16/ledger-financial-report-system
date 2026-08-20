# Architecture

The app turns Annual Report PDFs into a fixed 27-row asset-side balance sheet. A Flask API stages uploads and coordinates extraction strategies, provider calls, validation, reconciliation, scoring, and file-backed run persistence. The browser UI configures and observes those workflows.

## Major components

- **Web client** — `frontend/` is a typed React/Vite SPA; Vercel serves the public production bundle, while Flask can still serve `frontend/dist/` locally.
- **HTTP API** — `server.py` exposes settings, upload, extraction, streaming, run, schema, and evaluation endpoints.
- **Pipeline** — `pipeline.py` orchestrates the strategy-independent lifecycle.
- **Extraction strategies** — `extraction.py` wraps PyPDF, PyMuPDF4LLM, Docling, and pdf-inspector behind one result type.
- **Contract and repair** — `normalize.py`, `models.py`, and `schema.py` normalize representations and enforce the 27-row contract.
- **Quality** — `reconcile.py` checks arithmetic identities; `pipeline.compute_metrics` compares accepted rows with year-specific golden data.
- **Provider boundary** — `api_client.py`, `providers.py`, and `ratelimit.py` handle compatible LLM APIs and adaptive concurrency.
- **Corpus boundary** — `corpus/` discovers official Annual Reports through Firecrawl, downloads directly, screens locally, and atomically updates a SHA-256 manifest. `corpus_worker.py` exposes the same service to long-lived CLI jobs.
- **Persistence** — uploads, runs, corpus PDFs, manifests, and customer research are stored on disk with company/year/timestamp namespaces.
- **Production runtime** — Caddy terminates TLS on one SSM-managed Tokyo EC2 instance and proxies to Gunicorn on loopback. SSM Parameter Store holds the mutation token; no secret is bundled into Vercel.

## Control flow

1. The React client stages one or more PDFs with the API and renders real SSE lifecycle events.
2. `pipeline.run_pipeline` extracts text, builds the prompt, calls the selected provider, parses and normalizes JSON, validates the contract, and makes at most one context-preserving repair call when JSON/Pydantic validation fails. It then applies the confidence gate, reconciles, scores, and files the run.
3. Streaming endpoints emit per-file phase events; completed predictions are served to the UI and exports.

Corpus flow is deliberately separate: React or the CLI supplies companies and FY2020–FY2025, Firecrawl discovers candidates, direct download verifies the PDF, local screening records health, and only a later explicit extraction action may consume it.

See `agent/graph/architecture.svg` and `agent/graph/graph.md`.
