# Bakuraku customer FY2022 benchmark status

Date: 2026-08-22

## Final status

The ten-company FY2022 cohort is acquired, screened, twice audited, and scored
in native-source millions. All ten exact PDFs are pinned in the corpus manifest
by SHA-256. Strategy 2 and Strategy 3 both achieve 100% exact accuracy on all
scorable rows; the exact run ledger is in `bakuraku_strategy23_results.md`.

| Company | PDF pages | Balance sheet page | Currency | Gold rows | Source quantum |
|---|---:|---:|---|---:|---:|
| AppBank株式会社 | 117 | 67 | JPY | 27 | ¥0.001M |
| note株式会社 | 109 | 75 | JPY | 27 | ¥0.001M |
| ダイニチ工業株式会社 | 70 | 34 | JPY | 27 | ¥0.001M |
| ラクスル株式会社 | 124 | 65 | JPY | 27 | ¥1M |
| リソルホールディングス株式会社 | 116 | 48 | JPY | 24 | ¥0.001M |
| 株式会社グッドパッチ | 122 | 62 | JPY | 27 | ¥0.001M |
| 株式会社ストライダーズ | 102 | 42 | JPY | 27 | ¥0.001M |
| 株式会社プレイド | 128 | 64 | JPY | 27 | ¥0.001M |
| 株式会社ベルク | 96 | 41 | JPY | 27 | ¥1M |
| 株式会社帝国ホテル | 87 | 37 | JPY | 27 | ¥1M |

Resol exposes net PPE categories and an aggregate accumulated-depreciation
figure, but not the three gross schema components Buildings, Plant & Machinery,
and Other Equipment. Those three rows are explicitly unscorable instead of
being inferred. The other 267 rows are source-verifiable.

## Audit and benchmark boundary

Each table was checked against the exact source PDF twice: once with Poppler
layout extraction and once with PyMuPDF embedded text plus deterministic schema
reconciliation. Citations, source precision, audit passes, and any unscorable
rows are stored in `benchmark_data/bakuraku_fy2022_gold.json`. The fixture is
bound to PDF SHA-256, company identity, fiscal year, and JPY; a replacement PDF
cannot inherit it.

The benchmark uses M JPY, not the legacy field name `answer_m_usd`. No FX rate
is invented. Exact-match tolerance is half the source's disclosed quantum, so a
thousands-of-yen source must match within ¥0.0005M and a whole-million source
within ¥0.5M.

The answer key is evaluation-only. Model requests contain the 27-row schema,
source pages, parser diagnostics, and mapping rules, but never expected values.
Model confidence is retained only to prioritize review and does not suppress a
returned value or determine correctness.

## Source and acquisition controls

The seed cohort comes from confirmed first-party Bakuraku customer stories in
`research/bakuraku/benchmark_10.csv`. Reports were downloaded from official
company IR/CDN or EDINET filing endpoints using
`research/bakuraku/acquire_fy2022.py`; resolved sources are recorded in
`research/bakuraku/fy2022_sources.json`. Admission requires local Annual Report
screening to return `ok`, and canonical replacement is rejected otherwise.
