# Bakuraku FY2022 Strategy 2 / Strategy 3 benchmark

Run date: 2026-08-22. Model: GLM-5.3 coding endpoint, medium reasoning,
temperature 0.0. Unit: M JPY. Gold values were evaluation-only and were never
included in a model request.

| Company | Strategy | Run | Exact | Approx. prompt tokens | Selected pages |
|---|---|---|---:|---:|---|
| AppBank株式会社 | S2 pdf-inspector + local OCR | `S2FC_20260822T104905Z_001` | 27/27 (100%) | 34,705 | full report |
| AppBank株式会社 | S3 intelligent gate | `S3_20260822T102508Z_001` | 27/27 (100%) | 1,280 | 67, 73, 76, 97, 106 |
| note株式会社 | S2 pdf-inspector + local OCR | `S2FC_20260822T104905Z_002` | 27/27 (100%) | 37,436 | full report |
| note株式会社 | S3 intelligent gate | `S3_20260822T102704Z_002` | 27/27 (100%) | 1,636 | 14, 75, 82, 89, 100 |
| ダイニチ工業株式会社 | S2 pdf-inspector + local OCR | `S2FC_20260822T110228Z_001` | 27/27 (100%) | 17,527 | full report |
| ダイニチ工業株式会社 | S3 intelligent gate | `S3_20260822T110454Z_004` | 27/27 (100%) | 946 | 34, 35, 45, 53, 61 |
| ラクスル株式会社 | S2 pdf-inspector + local OCR | `S2FC_20260822T105206Z_004` | 27/27 (100%) | 37,641 | full report |
| ラクスル株式会社 | S3 intelligent gate | `S3_20260822T110615Z_005` | 27/27 (100%) | 1,073 | 65, 71, 78, 80, 101 |
| リソルホールディングス株式会社 | S2 pdf-inspector + local OCR | `S2FC_20260822T111228Z_001` | 24/24 (100%) | 31,062 | full report |
| リソルホールディングス株式会社 | S3 intelligent gate | `S3_20260822T111537Z_002` | 24/24 (100%) | 1,064 | 48, 56, 61, 72, 82 |
| 株式会社グッドパッチ | S2 pdf-inspector + local OCR | `S2FC_20260822T105338Z_006` | 27/27 (100%) | 36,450 | full report |
| 株式会社グッドパッチ | S3 intelligent gate | `S3_20260822T103557Z_006` | 27/27 (100%) | 1,626 | 62, 79, 97, 102, 118 |
| 株式会社ストライダーズ | S2 pdf-inspector + local OCR | `S2FC_20260822T105547Z_007` | 27/27 (100%) | 27,368 | full report |
| 株式会社ストライダーズ | S3 intelligent gate | `S3_20260822T103803Z_007` | 27/27 (100%) | 1,615 | 42, 60, 75, 81, 101 |
| 株式会社プレイド | S2 pdf-inspector + local OCR | `S2FC_20260822T105614Z_008` | 27/27 (100%) | 35,738 | full report |
| 株式会社プレイド | S3 intelligent gate | `S3_20260822T111728Z_003` | 27/27 (100%) | 1,281 | 64, 71, 76, 84, 104 |
| 株式会社ベルク | S2 pdf-inspector + local OCR | `S2FC_20260822T105850Z_009` | 27/27 (100%) | 23,329 | full report |
| 株式会社ベルク | S3 intelligent gate | `S3_20260822T104214Z_009` | 27/27 (100%) | 1,377 | 41, 52, 68, 74, 95 |
| 株式会社帝国ホテル | S2 pdf-inspector + local OCR | `S2FC_20260822T110432Z_003` | 27/27 (100%) | 24,455 | full report |
| 株式会社帝国ホテル | S3 intelligent gate | `S3_20260822T104406Z_010` | 27/27 (100%) | 1,311 | 37, 48, 59, 65, 80 |

Across the cohort, each strategy scores 267/267 source-verifiable rows. Strategy
3 sends five complete source pages per report and reduces approximate prompt
input by about 93.5%–97.1% relative to Strategy 2. It does not split pages into
arbitrary token fragments.

Confidence-accepted coverage is intentionally not the accuracy metric. For
example, the final Plaid Strategy 3 run is 27/27 exact while only 23 returned
values have confidence at or above 0.80. Confidence identifies review priority;
source-bound exact comparison determines correctness.
