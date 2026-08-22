# Five-company, three-strategy parser bake-off

Model: `glm-5.3` · temperature 0.0 · unit M JPY · 39/45 arms complete.
Gold is used only after inference for evaluation and is never included in model requests.

| Company | Strategy | Parser | OCR | Exact | Coverage | Parser s | Model s | Total s | Approx tokens | Run |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| AppBank株式会社 | Strategy 1 | pypdf | off | 27/27 (100.0%) | 100.0 | 3.86 | 103.15 | 107.01 | 34877 | `S1_20260822T115305Z_002` |
| AppBank株式会社 | Strategy 1 | pymupdf | off | 27/27 (100.0%) | 100.0 | 25.33 | 147.41 | 172.74 | 38011 | `S1PM_20260822T115305Z_001` |
| AppBank株式会社 | Strategy 1 | s1-inspector | — | failed | — | — | — | 1.39 | — | `—` |
| AppBank株式会社 | Strategy 1 | s1-docling | — | failed | — | — | — | 709.88 | — | `—` |
| AppBank株式会社 | Strategy 2 | pypdf | force | 25/27 (92.6%) | 100.0 | 35.54 | 197.7 | 233.24 | 38172 | `S2PY_20260822T115453Z_005` |
| AppBank株式会社 | Strategy 2 | pymupdf | adaptive | 25/27 (92.6%) | 100.0 | 12.35 | 160.98 | 173.33 | 38272 | `S2_20260822T115558Z_006` |
| AppBank株式会社 | Strategy 2 | inspector | adaptive | 27/27 (100.0%) | 100.0 | 1.67 | 179.35 | 181.02 | 34705 | `S2FC_20260822T104905Z_001` |
| AppBank株式会社 | Strategy 2 | docling | force | 9/27 (33.3%) | 100.0 | 82.28 | 560.64 | 642.92 | 21375 | `S2DL_20260822T115846Z_007` |
| AppBank株式会社 | Strategy 3 | inspector-gate | adaptive | 27/27 (100.0%) | 100.0 | 0.92 | 114.27 | 115.19 | 1280 | `S3_20260822T102508Z_001` |
| ダイニチ工業株式会社 | Strategy 1 | pypdf | off | 27/27 (100.0%) | 100.0 | 1.45 | 195.34 | 196.79 | 17530 | `S1_20260822T115851Z_008` |
| ダイニチ工業株式会社 | Strategy 1 | pymupdf | off | 27/27 (100.0%) | 100.0 | 7.06 | 165.32 | 172.38 | 22257 | `S1PM_20260822T120208Z_009` |
| ダイニチ工業株式会社 | Strategy 1 | s1-inspector | — | failed | — | — | — | 0.22 | — | `—` |
| ダイニチ工業株式会社 | Strategy 1 | docling | off | 25/27 (92.6%) | 100.0 | 79.63 | 208.14 | 287.77 | 31945 | `S1DL_20260822T120457Z_011` |
| ダイニチ工業株式会社 | Strategy 2 | pypdf | force | 27/27 (100.0%) | 100.0 | 29.8 | 149.01 | 178.81 | 22380 | `S2PY_20260822T120501Z_012` |
| ダイニチ工業株式会社 | Strategy 2 | pymupdf | adaptive | 26/27 (96.3%) | 100.0 | 9.56 | 141.67 | 151.23 | 22446 | `S2_20260822T120800Z_013` |
| ダイニチ工業株式会社 | Strategy 2 | inspector | adaptive | 27/27 (100.0%) | 100.0 | 0.7 | 146.09 | 146.79 | 17527 | `S2FC_20260822T110228Z_001` |
| ダイニチ工業株式会社 | Strategy 2 | docling | force | 27/27 (100.0%) | 100.0 | 64.63 | 142.0 | 206.63 | 31945 | `S2DL_20260822T120929Z_014` |
| ダイニチ工業株式会社 | Strategy 3 | inspector-gate | adaptive | 27/27 (100.0%) | 100.0 | 0.31 | 116.71 | 117.02 | 946 | `S3_20260822T110454Z_004` |
| ラクスル株式会社 | Strategy 1 | pypdf | off | 27/27 (100.0%) | 100.0 | 1.03 | 70.17 | 71.2 | 37651 | `S1_20260822T120945Z_015` |
| ラクスル株式会社 | Strategy 1 | pymupdf | off | 27/27 (100.0%) | 100.0 | 13.0 | 82.29 | 95.29 | 41545 | `S1PM_20260822T121031Z_016` |
| ラクスル株式会社 | Strategy 1 | s1-inspector | — | failed | — | — | — | 0.45 | — | `—` |
| ラクスル株式会社 | Strategy 1 | docling | off | 27/27 (100.0%) | 100.0 | 98.62 | 94.09 | 192.71 | 56136 | `S1DL_20260822T121056Z_018` |
| ラクスル株式会社 | Strategy 2 | pypdf | force | 27/27 (100.0%) | 100.0 | 48.4 | 110.49 | 158.89 | 41669 | `S2PY_20260822T121206Z_019` |
| ラクスル株式会社 | Strategy 2 | pymupdf | adaptive | 27/27 (100.0%) | 100.0 | 13.87 | 140.16 | 154.03 | 41778 | `S2_20260822T121256Z_020` |
| ラクスル株式会社 | Strategy 2 | inspector | adaptive | 27/27 (100.0%) | 100.0 | 0.45 | 91.59 | 92.04 | 37641 | `S2FC_20260822T105206Z_004` |
| ラクスル株式会社 | Strategy 2 | docling | force | 27/27 (100.0%) | 100.0 | 94.48 | 118.4 | 212.88 | 56160 | `S2DL_20260822T121409Z_021` |
| ラクスル株式会社 | Strategy 3 | inspector-gate | adaptive | 27/27 (100.0%) | 100.0 | 0.44 | 126.75 | 127.19 | 1073 | `S3_20260822T110615Z_005` |
| 株式会社プレイド | Strategy 1 | pypdf | off | 27/27 (100.0%) | 100.0 | 1.02 | 119.6 | 120.62 | 35264 | `S1_20260822T121445Z_022` |
| 株式会社プレイド | Strategy 1 | pymupdf | off | 27/27 (100.0%) | 100.0 | 22.48 | 116.23 | 138.71 | 38515 | `S1PM_20260822T121530Z_023` |
| 株式会社プレイド | Strategy 1 | s1-inspector | — | failed | — | — | — | 0.43 | — | `—` |
| 株式会社プレイド | Strategy 1 | docling | off | 27/27 (100.0%) | 100.0 | 108.22 | 164.96 | 273.18 | 56423 | `S1DL_20260822T121646Z_025` |
| 株式会社プレイド | Strategy 2 | pypdf | force | 27/27 (100.0%) | 100.0 | 58.13 | 133.76 | 191.89 | 38646 | `S2PY_20260822T121742Z_026` |
| 株式会社プレイド | Strategy 2 | pymupdf | adaptive | 27/27 (100.0%) | 100.0 | 27.13 | 176.84 | 203.97 | 38743 | `S2_20260822T121748Z_027` |
| 株式会社プレイド | Strategy 2 | inspector | adaptive | 27/27 (100.0%) | 100.0 | 3.67 | 164.82 | 168.49 | 35738 | `S2FC_20260822T105614Z_008` |
| 株式会社プレイド | Strategy 2 | docling | force | 27/27 (100.0%) | 100.0 | 111.66 | 100.57 | 212.23 | 56425 | `S2DL_20260822T122054Z_028` |
| 株式会社プレイド | Strategy 3 | inspector-gate | adaptive | 27/27 (100.0%) | 100.0 | 0.43 | 180.8 | 181.23 | 1281 | `S3_20260822T111728Z_003` |
| 株式会社帝国ホテル | Strategy 1 | pypdf | off | 27/27 (100.0%) | 100.0 | 1.0 | 143.28 | 144.28 | 24567 | `S1_20260822T122112Z_029` |
| 株式会社帝国ホテル | Strategy 1 | pymupdf | off | 27/27 (100.0%) | 100.0 | 11.37 | 156.72 | 168.09 | 28306 | `S1PM_20260822T122120Z_030` |
| 株式会社帝国ホテル | Strategy 1 | s1-inspector | — | failed | — | — | — | 0.48 | — | `—` |
| 株式会社帝国ホテル | Strategy 1 | docling | off | 27/27 (100.0%) | 100.0 | 115.89 | 168.82 | 284.71 | 42919 | `S1DL_20260822T122337Z_032` |
| 株式会社帝国ホテル | Strategy 2 | pypdf | force | 27/27 (100.0%) | 100.0 | 40.58 | 164.28 | 204.86 | 28328 | `S2PY_20260822T122408Z_033` |
| 株式会社帝国ホテル | Strategy 2 | pymupdf | adaptive | 27/27 (100.0%) | 100.0 | 23.37 | 105.74 | 129.11 | 28415 | `S2_20260822T122426Z_034` |
| 株式会社帝国ホテル | Strategy 2 | inspector | adaptive | 27/27 (100.0%) | 100.0 | 0.38 | 102.35 | 102.73 | 24455 | `S2FC_20260822T110432Z_003` |
| 株式会社帝国ホテル | Strategy 2 | docling | force | 27/27 (100.0%) | 100.0 | 91.57 | 166.78 | 258.35 | 42929 | `S2DL_20260822T122635Z_035` |
| 株式会社帝国ホテル | Strategy 3 | inspector-gate | adaptive | 27/27 (100.0%) | 100.0 | 0.39 | 165.95 | 166.34 | 1311 | `S3_20260822T104406Z_010` |

## Aggregate timing and reliability

Means include successful arms only; `Completed` preserves failures as reliability outcomes.

| Strategy | Parser | Completed | Mean parser s | Mean model s | Mean total s | Mean tokens | Mean accuracy |
|---|---|---:|---:|---:|---:|---:|---:|
| Strategy 1 | pypdf | 5/5 | 1.67 | 126.31 | 127.98 | 29977.8 | 100.0% |
| Strategy 1 | pymupdf | 5/5 | 15.85 | 133.59 | 149.44 | 33726.8 | 100.0% |
| Strategy 1 | s1-inspector | 0/5 | — | — | — | — | — |
| Strategy 1 | docling | 4/5 | 100.59 | 159.0 | 259.59 | 46855.75 | 98.15% |
| Strategy 2 | pypdf | 5/5 | 42.49 | 151.05 | 193.54 | 33839.0 | 98.52% |
| Strategy 2 | pymupdf | 5/5 | 17.26 | 145.08 | 162.33 | 33930.8 | 97.78% |
| Strategy 2 | inspector | 5/5 | 1.37 | 136.84 | 138.21 | 30013.2 | 100.0% |
| Strategy 2 | docling | 5/5 | 88.92 | 217.68 | 306.6 | 41766.8 | 86.66% |
| Strategy 3 | inspector-gate | 5/5 | 0.5 | 140.9 | 141.39 | 1178.2 | 100.0% |

## Failure details

| Company | Arm | Elapsed s | Error |
|---|---|---:|---|
| AppBank株式会社 | `s1-inspector` | 1.39 | RuntimeError: pdf-inspector reports encoding problems in this document's text layer: some characters cannot be mapped to real text. |
| AppBank株式会社 | `s1-docling` | 709.88 | GLMError: Request timed out after 600 seconds. |
| ダイニチ工業株式会社 | `s1-inspector` | 0.22 | RuntimeError: pdf-inspector reports encoding problems in this document's text layer: some characters cannot be mapped to real text. |
| ラクスル株式会社 | `s1-inspector` | 0.45 | RuntimeError: pdf-inspector reports encoding problems in this document's text layer: some characters cannot be mapped to real text. |
| 株式会社プレイド | `s1-inspector` | 0.43 | RuntimeError: pdf-inspector reports encoding problems in this document's text layer: some characters cannot be mapped to real text. |
| 株式会社帝国ホテル | `s1-inspector` | 0.48 | RuntimeError: pdf-inspector reports encoding problems in this document's text layer: some characters cannot be mapped to real text. |
