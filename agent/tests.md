# Tests

## Strategy

- `test_contract.py` is an offline executable suite covering schema, normalization, validation, parsing, extraction health, rate limiting, reconciliation, providers, and run layout.
- `test_traffic.py` verifies Redis event shape, credential exclusion, session deduplication, hosted-origin enforcement, and the deliberate admin-token exemption for visit telemetry.
- Vitest covers the typed API adapter and fragmented SSE parsing boundary.
- Browser QA must cover the dashboard, each live strategy, uploads, settings, run detail, responsive layout, and console errors.

## Commands

```bash
.venv/bin/python test_contract.py
.venv/bin/python test_traffic.py
cd frontend && npm test -- --run && npm run build
```

## Current baseline

The Python suite, four Vitest checks, production TypeScript/Vite build, Python
compile checks, and in-app browser visual/DOM sweep passed on 2026-08-21. The
browser pass covered light/dark themes, English/Japanese, the creator link,
closed-by-default system prompt, Strategy 2 parser capsules, connected quadrant
legend placement, and guarded History selection/delete controls. Component
tests cover the six separate live execution capsules. Offline checks also prove
that a repair payload preserves prior model context and writes separate attempt
artifacts. Firecrawl's authenticated credit-usage probe passed against the saved
local credential without launching a crawl; no paid model extraction was launched.
