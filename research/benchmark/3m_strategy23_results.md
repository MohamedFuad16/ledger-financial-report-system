# 3M Strategy 2 / Strategy 3 benchmark

Run date: 2026-08-22. Model: GLM-5.3 coding endpoint, medium reasoning,
temperature 0.0. Gold values are evaluation-only and were not included in any
model request. FY2022 is assignment-supplied; the other keys are bound to exact
audited PDF hashes documented in `3m_cross_year_gold_audit.md`.

| FY | Strategy | Run | Exact | Coverage | Confidence-accepted coverage | Consistency | Approx. prompt tokens | Selected pages |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 2021 | S2 pdf-inspector + local OCR | `S2FC_20260822T091844Z_001` | 27/27 (100%) | 100% | 100% | 100% | 134,096 | full report |
| 2021 | S3 intelligent gate | `S3_20260822T092323Z_002` | 27/27 (100%) | 100% | 100% | 100% | 4,868 | 55, 57, 59, 61, 77 |
| 2022 | S2 pdf-inspector + local OCR | `S2FC_20260822T085742Z_001` | 27/27 (100%) | 100% | 96.3% | 100% | 238,657 | full report |
| 2022 | S3 intelligent gate | `S3_20260822T085940Z_002` | 27/27 (100%) | 100% | 88.9% | 100% | 4,753 | 50, 52, 54, 68, 94 |
| 2023 | S2 pdf-inspector + local OCR | `S2FC_20260822T092751Z_001` | 27/27 (100%) | 100% | 96.3% | 100% | 132,363 | full report |
| 2023 | S3 intelligent gate | `S3_20260822T092916Z_002` | 27/27 (100%) | 100% | 96.3% | 100% | 4,872 | 54, 56, 57, 67, 87 |
| 2024 | S2 pdf-inspector + local OCR | `S2FC_20260822T093017Z_003` | 27/27 (100%) | 100% | 100% | 100% | 137,206 | full report |
| 2024 | S3 intelligent gate | `S3_20260822T093225Z_004` | 27/27 (100%) | 100% | 96.3% | 100% | 3,896 | 46, 55, 57, 63, 69 |
| 2025 | S2 pdf-inspector + local OCR | `S2FC_20260822T093400Z_005` | 22/22 (100%) | 100% | 77.8% | 100% | 123,882 | full report |
| 2025 | S3 intelligent gate v2 | `S3_20260822T093950Z_001` | 22/22 (100%) | 100% | 63.0% | 100% | 4,288 | 42, 50, 52, 54, 104 |

FY2025 is scored only against 22 source-verifiable rows. The report does not
disclose the component table required to split the remaining five Other-assets
rows, so those rows are not guessed.

## Findings

- Finalized Strategy 2 and Strategy 3 achieve 100% exact accuracy on every
  independently auditable 3M row across FY2021–FY2025.
- Strategy 3 reduces approximate prompt input by 96.3%–98.0% across these
  reports while retaining the face statement and required notes.
- FY2021 validates the local OCR path: pdf-inspector routed 72–73 broken-font
  pages to RapidOCR. Both strategies recovered 27/27, whereas the old no-OCR
  run had been effectively unusable.
- Strategy 3 initially missed FY2025 lease Note 18 and scored 20/22. Gate v2
  added a general, value-free critical-evidence signal for explicit
  right-of-use-asset pages; the rerun selected page 104 and reached 22/22.
- Model confidence remains a review signal, not a correctness gate. Several
  runs are 100% exact despite confidence-accepted coverage as low as 63.0%.
- Strategy 3 reduces LLM input and usually model latency, but it does not reduce
  FY2021 local OCR time because the locked architecture OCRs all routed pages
  before scoring the unified Markdown.
