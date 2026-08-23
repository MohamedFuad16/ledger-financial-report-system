# Full-corpus three-strategy end-to-end evaluation

Model: `google/gemini-3.7-flash:nitro` · temperature 0.0 · 180/306 arms complete.
Gold is consulted only after inference for scoring; prompts never contain gold values.

## Aggregates per strategy

| Strategy | Complete | Scored | Mean exact accuracy | Mean coverage | P50 total s | Mean model-reported input tokens | Retries |
|---|---:|---:|---:|---:|---:|---:|---:|
| Strategy 1 (`s1`) | 25 | 25 | 96.25 | 100.0 | 19.2 | 86368.24 | 0 |
| Strategy 2 (`s2-inspector`) | 53 | 53 | 97.29 | 66.38 | 15.27 | 56278.0 | 0 |
| Strategy 3 (`s3`) | 102 | 102 | 97.98 | 78.68 | 14.81 | 7030.52 | 19 |

## Per-report results

| Company | FY | Strategy | Exact | Coverage | Consistency | Total s | Prompt tokens | Retry | Run |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 3M | 2022 | s1 | failed | — | — | 19.39 | — | — | `GLMError: HTTP 402: {'message': 'This request would exceed y` |
| 3M | 2022 | s2-inspector | 27/27 (100.0%) | 100.0 | 100.0 | 20.58 | 214385 | — | `S2FC_20260823T162416Z_001` |
| 3M | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 16.96 | 9163 | — | `S3_20260823T162416Z_002` |
| AppBank株式会社 | 2020 | s1 | failed | — | — | 2.76 | — | — | `GLMError: HTTP 402: {'message': 'This request would exceed y` |
| AppBank株式会社 | 2020 | s2-inspector | 23/23 (100.0%) | 100.0 | 100.0 | 16.08 | 79464 | — | `S2FC_20260823T171149Z_001` |
| AppBank株式会社 | 2020 | s3 | 23/23 (100.0%) | 100.0 | 100.0 | 12.05 | 7202 | — | `S3_20260823T170605Z_001` |
| AppBank株式会社 | 2021 | s1 | failed | — | — | 2.93 | — | — | `GLMError: HTTP 402: {'message': 'This request would exceed y` |
| AppBank株式会社 | 2021 | s2-inspector | 23/23 (100.0%) | 100.0 | 100.0 | 19.39 | 80177 | — | `S2FC_20260823T171149Z_002` |
| AppBank株式会社 | 2021 | s3 | 23/23 (100.0%) | 100.0 | 100.0 | 16.18 | 7725 | — | `S3_20260823T170605Z_002` |
| AppBank株式会社 | 2022 | s1 | failed | — | — | 4.66 | — | — | `GLMError: HTTP 402: {'message': 'This request would exceed y` |
| AppBank株式会社 | 2022 | s2-inspector | 27/27 (100.0%) | 100.0 | 100.0 | 18.68 | 95749 | — | `S2FC_20260823T162416Z_003` |
| AppBank株式会社 | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 19.69 | 8147 | — | `S3_20260823T162416Z_004` |
| AppBank株式会社 | 2023 | s1 | failed | — | — | 5.16 | — | — | `GLMError: HTTP 402: {'message': 'This request would exceed y` |
| AppBank株式会社 | 2023 | s2-inspector | 20/20 (100.0%) | 100.0 | 100.0 | 17.11 | 101079 | — | `S2FC_20260823T171149Z_003` |
| AppBank株式会社 | 2023 | s3 | 20/20 (100.0%) | 100.0 | 100.0 | 14.58 | 7761 | — | `S3_20260823T170605Z_003` |
| AppBank株式会社 | 2024 | s1 | 12/12 (100.0%) | 100.0 | 100.0 | 19.88 | 85820 | — | `S1_20260823T171505Z_006` |
| AppBank株式会社 | 2024 | s2-inspector | 12/12 (100.0%) | 100.0 | 100.0 | 17.69 | 86326 | — | `S2FC_20260823T171205Z_004` |
| AppBank株式会社 | 2024 | s3 | 12/12 (100.0%) | 100.0 | 100.0 | 17.07 | 7412 | — | `S3_20260823T170605Z_004` |
| AppBank株式会社 | 2025 | s1 | failed | — | — | 5.08 | — | — | `GLMError: HTTP 402: {'message': 'This request would exceed y` |
| AppBank株式会社 | 2025 | s2-inspector | 20/20 (100.0%) | 100.0 | 100.0 | 19.09 | 98393 | — | `S2FC_20260823T171206Z_005` |
| AppBank株式会社 | 2025 | s3 | 20/20 (100.0%) | 100.0 | 100.0 | 12.63 | 7372 | — | `S3_20260823T170618Z_005` |
| Byside株式会社 | 2024 | s1 | failed | — | — | 0.05 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| Byside株式会社 | 2024 | s2-inspector | 1/1 (100.0%) | 25.9 | 100.0 | 14.41 | 3994 | — | `S2FC_20260823T162433Z_005` |
| Byside株式会社 | 2024 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 16.34 | 4280 | — | `S3_20260823T162435Z_006` |
| JR九州エンジニアリング株式会社 | 2022 | s1 | failed | — | — | 0.06 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| JR九州エンジニアリング株式会社 | 2022 | s2-inspector | 1/1 (100.0%) | 40.7 | 100.0 | 13.12 | 4103 | — | `S2FC_20260823T162436Z_007` |
| JR九州エンジニアリング株式会社 | 2022 | s3 | 1/1 (100.0%) | 33.3 | 100.0 | 17.1 | 4389 | — | `S3_20260823T162436Z_008` |
| JUKI産機テクノロジー株式会社 | 2022 | s1 | failed | — | — | 0.05 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| JUKI産機テクノロジー株式会社 | 2022 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 10.57 | 4095 | — | `S2FC_20260823T162447Z_009` |
| JUKI産機テクノロジー株式会社 | 2022 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 13.24 | 4381 | — | `S3_20260823T162449Z_010` |
| note株式会社 | 2022 | s1 | 23/27 (85.2%) | 100.0 | 100.0 | 32.02 | 101830 | — | `S1_20260823T171856Z_010` |
| note株式会社 | 2022 | s2-inspector | 27/27 (100.0%) | 100.0 | 100.0 | 15.4 | 102471 | — | `S2FC_20260823T162451Z_011` |
| note株式会社 | 2022 | s3 | 23/27 (85.2%) | 100.0 | 100.0 | 20.61 | 8671 | — | `S3_20260823T162454Z_012` |
| note株式会社 | 2023 | s1 | 20/20 (100.0%) | 100.0 | 100.0 | 19.42 | 99362 | — | `S1_20260823T171857Z_011` |
| note株式会社 | 2023 | s2-inspector | 20/20 (100.0%) | 100.0 | 100.0 | 13.22 | 98527 | — | `S2FC_20260823T171209Z_006` |
| note株式会社 | 2023 | s3 | 20/20 (100.0%) | 100.0 | 100.0 | 11.08 | 7227 | — | `S3_20260823T170620Z_006` |
| note株式会社 | 2024 | s1 | 15/15 (100.0%) | 100.0 | 100.0 | 15.32 | 108201 | — | `S1_20260823T171917Z_012` |
| note株式会社 | 2024 | s2-inspector | 15/15 (100.0%) | 100.0 | 100.0 | 13.52 | 108746 | — | `S2FC_20260823T171222Z_007` |
| note株式会社 | 2024 | s3 | 15/15 (100.0%) | 100.0 | 100.0 | 23.46 | 7775 | +2 | `S3_20260823T170622Z_007` |
| note株式会社 | 2025 | s1 | 20/20 (100.0%) | 100.0 | 100.0 | 19.53 | 131668 | — | `S1_20260823T171928Z_013` |
| note株式会社 | 2025 | s2-inspector | 20/20 (100.0%) | 100.0 | 100.0 | 17.64 | 131274 | — | `S2FC_20260823T171223Z_008` |
| note株式会社 | 2025 | s3 | 20/20 (100.0%) | 100.0 | 100.0 | 24.14 | 8341 | +2 | `S3_20260823T170623Z_008` |
| キャディ株式会社 | 2024 | s1 | failed | — | — | 0.04 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| キャディ株式会社 | 2024 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 16.28 | 4138 | — | `S2FC_20260823T162458Z_013` |
| キャディ株式会社 | 2024 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 14.88 | 4424 | — | `S3_20260823T162502Z_014` |
| クラスター株式会社 | 2025 | s1 | failed | — | — | 0.05 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| クラスター株式会社 | 2025 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 12.14 | 3993 | — | `S2FC_20260823T162506Z_015` |
| クラスター株式会社 | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 16.02 | 4279 | — | `S3_20260823T162514Z_016` |
| ダイニチ工業株式会社 | 2020 | s1 | 16/18 (88.9%) | 100.0 | 85.7 | 18.05 | 55495 | — | `S1_20260823T171932Z_016` |
| ダイニチ工業株式会社 | 2020 | s2-inspector | 15/18 (83.3%) | 100.0 | 100.0 | 16.95 | 55996 | — | `S2FC_20260823T171225Z_009` |
| ダイニチ工業株式会社 | 2020 | s3 | 18/18 (100.0%) | 100.0 | 85.7 | 24.5 | 8037 | +0 | `S3_20260823T170630Z_009` |
| ダイニチ工業株式会社 | 2021 | s1 | 16/18 (88.9%) | 100.0 | 100.0 | 18.7 | 56945 | — | `S1_20260823T171948Z_017` |
| ダイニチ工業株式会社 | 2021 | s2-inspector | 15/18 (83.3%) | 100.0 | 100.0 | 15.68 | 57463 | — | `S2FC_20260823T171235Z_010` |
| ダイニチ工業株式会社 | 2021 | s3 | 18/18 (100.0%) | 100.0 | 100.0 | 18.15 | 7848 | — | `S3_20260823T170631Z_010` |
| ダイニチ工業株式会社 | 2022 | s1 | 24/27 (88.9%) | 100.0 | 100.0 | 19.15 | 55441 | — | `S1_20260823T171950Z_018` |
| ダイニチ工業株式会社 | 2022 | s2-inspector | 24/27 (88.9%) | 100.0 | 100.0 | 14.91 | 56047 | — | `S2FC_20260823T162514Z_017` |
| ダイニチ工業株式会社 | 2022 | s3 | 25/27 (92.6%) | 100.0 | 100.0 | 13.46 | 7423 | — | `S3_20260823T162517Z_018` |
| ダイニチ工業株式会社 | 2023 | s1 | 17/18 (94.4%) | 100.0 | 85.7 | 19.26 | 60962 | — | `S1_20260823T172007Z_019` |
| ダイニチ工業株式会社 | 2023 | s2-inspector | 15/18 (83.3%) | 100.0 | 85.7 | 16.79 | 61497 | — | `S2FC_20260823T171241Z_011` |
| ダイニチ工業株式会社 | 2023 | s3 | 16/18 (88.9%) | 100.0 | 85.7 | 27.6 | 7682 | +0 | `S3_20260823T170646Z_011` |
| ダイニチ工業株式会社 | 2024 | s1 | failed | — | — | 1.35 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ダイニチ工業株式会社 | 2024 | s2-inspector | 17/18 (94.4%) | 100.0 | 100.0 | 23.53 | 60932 | — | `S2FC_20260823T171242Z_012` |
| ダイニチ工業株式会社 | 2024 | s3 | 15/18 (83.3%) | 100.0 | 85.7 | 56.81 | 7450 | +0 | `S3_20260823T170647Z_012` |
| ダイニチ工業株式会社 | 2025 | s1 | failed | — | — | 1.54 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ダイニチ工業株式会社 | 2025 | s2-inspector | 15/18 (83.3%) | 100.0 | 71.4 | 17.46 | 65851 | — | `S2FC_20260823T171251Z_013` |
| ダイニチ工業株式会社 | 2025 | s3 | 18/18 (100.0%) | 100.0 | 85.7 | 21.71 | 7874 | +0 | `S3_20260823T170649Z_013` |
| ハコベル株式会社 | 2024 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| ハコベル株式会社 | 2024 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 12.69 | 4020 | — | `S2FC_20260823T162518Z_019` |
| ハコベル株式会社 | 2024 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 11.75 | 4306 | — | `S3_20260823T162529Z_020` |
| ファインディ株式会社 | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| ファインディ株式会社 | 2025 | s2-inspector | 1/1 (100.0%) | 25.9 | 100.0 | 10.63 | 3976 | — | `S2FC_20260823T162530Z_021` |
| ファインディ株式会社 | 2025 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 11.55 | 4262 | — | `S3_20260823T162530Z_022` |
| メディフォン株式会社 | 2021 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| メディフォン株式会社 | 2021 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 15.82 | 4105 | — | `S2FC_20260823T162531Z_023` |
| メディフォン株式会社 | 2021 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 13.09 | 4391 | — | `S3_20260823T162541Z_024` |
| ラクスル株式会社 | 2020 | s1 | failed | — | — | 0.82 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ラクスル株式会社 | 2020 | s2-inspector | 23/24 (95.8%) | 100.0 | 100.0 | 17.38 | 96365 | — | `S2FC_20260823T171257Z_014` |
| ラクスル株式会社 | 2020 | s3 | 24/24 (100.0%) | 100.0 | 100.0 | 18.11 | 8424 | — | `S3_20260823T170655Z_014` |
| ラクスル株式会社 | 2021 | s1 | failed | — | — | 0.83 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ラクスル株式会社 | 2021 | s2-inspector | 15/16 (93.8%) | 100.0 | 100.0 | 16.45 | 100501 | — | `S2FC_20260823T171306Z_015` |
| ラクスル株式会社 | 2021 | s3 | 16/16 (100.0%) | 100.0 | 100.0 | 15.35 | 8879 | — | `S3_20260823T170711Z_015` |
| ラクスル株式会社 | 2022 | s1 | failed | — | — | 0.84 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ラクスル株式会社 | 2022 | s2-inspector | 27/27 (100.0%) | 100.0 | 100.0 | 15.42 | 105922 | — | `S2FC_20260823T162541Z_025` |
| ラクスル株式会社 | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 13.33 | 7676 | — | `S3_20260823T162542Z_026` |
| ラクスル株式会社 | 2023 | s1 | failed | — | — | 3.8 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ラクスル株式会社 | 2023 | s2-inspector | 20/21 (95.2%) | 100.0 | 100.0 | 17.6 | 127367 | — | `S2FC_20260823T171309Z_016` |
| ラクスル株式会社 | 2023 | s3 | 21/21 (100.0%) | 100.0 | 100.0 | 21.56 | 8932 | — | `S3_20260823T170713Z_016` |
| ラクスル株式会社 | 2024 | s1 | failed | — | — | 4.55 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ラクスル株式会社 | 2024 | s2-inspector | 24/24 (100.0%) | 100.0 | 100.0 | 20.07 | 132023 | — | `S2FC_20260823T171315Z_017` |
| ラクスル株式会社 | 2024 | s3 | 24/24 (100.0%) | 100.0 | 100.0 | 15.04 | 8559 | — | `S3_20260823T170714Z_017` |
| ラクスル株式会社 | 2025 | s1 | failed | — | — | 4.37 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| ラクスル株式会社 | 2025 | s2-inspector | 21/21 (100.0%) | 100.0 | 100.0 | 23.55 | 121561 | — | `S2FC_20260823T171322Z_018` |
| ラクスル株式会社 | 2025 | s3 | 21/21 (100.0%) | 100.0 | 100.0 | 14.35 | 8257 | — | `S3_20260823T170722Z_018` |
| リソルホールディングス株式会社 | 2020 | s1 | failed | — | — | 1.71 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2020 | s2-inspector | 11/11 (100.0%) | 100.0 | 85.7 | 22.39 | 81238 | — | `S2FC_20260823T171326Z_019` |
| リソルホールディングス株式会社 | 2020 | s3 | 11/11 (100.0%) | 100.0 | 85.7 | 41.81 | 8081 | +0 | `S3_20260823T170727Z_019` |
| リソルホールディングス株式会社 | 2021 | s1 | failed | — | — | 1.19 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2021 | s2-inspector | failed | — | — | 0.95 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2021 | s3 | 11/11 (100.0%) | 100.0 | 85.7 | 23.47 | 8045 | +3 | `S3_20260823T170729Z_020` |
| リソルホールディングス株式会社 | 2022 | s1 | failed | — | — | 1.9 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2022 | s2-inspector | 22/24 (91.7%) | 100.0 | 85.7 | 18.87 | 92491 | — | `S2FC_20260823T162729Z_001` |
| リソルホールディングス株式会社 | 2022 | s3 | 24/24 (100.0%) | 88.9 | 100.0 | 13.02 | 7575 | +0 | `S3_20260823T162548Z_028` |
| リソルホールディングス株式会社 | 2023 | s1 | failed | — | — | 4.77 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2023 | s2-inspector | failed | — | — | 1.33 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2023 | s3 | 11/11 (100.0%) | 100.0 | 85.7 | 30.29 | 7810 | +3 | `S3_20260823T170736Z_021` |
| リソルホールディングス株式会社 | 2024 | s1 | failed | — | — | 5.42 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2024 | s2-inspector | failed | — | — | 1.36 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2024 | s3 | 11/11 (100.0%) | 100.0 | 85.7 | 36.21 | 8338 | +3 | `S3_20260823T170737Z_022` |
| リソルホールディングス株式会社 | 2025 | s1 | failed | — | — | 5.15 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2025 | s2-inspector | failed | — | — | 1.41 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| リソルホールディングス株式会社 | 2025 | s3 | 10/11 (90.9%) | 100.0 | 85.7 | 32.33 | 7657 | +4 | `S3_20260823T170753Z_023` |
| 吉田海運株式会社 | 2022 | s1 | failed | — | — | 0.07 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 吉田海運株式会社 | 2022 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 13.5 | 4011 | — | `S2FC_20260823T171339Z_024` |
| 吉田海運株式会社 | 2022 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 15.21 | 4297 | — | `S3_20260823T162555Z_030` |
| 坂善商事株式会社 | 2023 | s1 | failed | — | — | 0.08 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 坂善商事株式会社 | 2023 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 13.29 | 4407 | — | `S2FC_20260823T162555Z_031` |
| 坂善商事株式会社 | 2023 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 17.23 | 4693 | — | `S3_20260823T170806Z_024` |
| 大西運輸株式会社 | 2024 | s1 | failed | — | — | 0.07 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 大西運輸株式会社 | 2024 | s2-inspector | failed | — | — | 2.45 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 大西運輸株式会社 | 2024 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 8.92 | 4312 | — | `S3_20260823T170808Z_025` |
| 日本テーマパーク開発株式会社 | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 日本テーマパーク開発株式会社 | 2025 | s2-inspector | failed | — | — | 2.46 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 日本テーマパーク開発株式会社 | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 13.57 | 4492 | — | `S3_20260823T170813Z_026` |
| 株式会社FABRIC TOKYO | 2023 | s1 | failed | — | — | 0.01 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社FABRIC TOKYO | 2023 | s2-inspector | failed | — | — | 8.51 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社FABRIC TOKYO | 2023 | s3 | 1/1 (100.0%) | 29.6 | 100.0 | 14.74 | 4430 | — | `S3_20260823T170817Z_027` |
| 株式会社FLUX | 2024 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社FLUX | 2024 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 14.68 | 4016 | — | `S2FC_20260823T171349Z_028` |
| 株式会社FLUX | 2024 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 14.28 | 4302 | — | `S3_20260823T162801Z_011` |
| 株式会社Morght | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社Morght | 2025 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 14.0 | 4007 | — | `S2FC_20260823T162826Z_013` |
| 株式会社Morght | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 20.35 | 4293 | — | `S3_20260823T162840Z_014` |
| 株式会社PIGNUS（ピグナス） | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社PIGNUS（ピグナス） | 2025 | s2-inspector | 1/1 (100.0%) | 25.9 | 100.0 | 10.88 | 3974 | — | `S2FC_20260823T162925Z_017` |
| 株式会社PIGNUS（ピグナス） | 2025 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 13.54 | 4260 | — | `S3_20260823T162936Z_018` |
| 株式会社SANU | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社SANU | 2025 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 13.97 | 4014 | — | `S2FC_20260823T162950Z_019` |
| 株式会社SANU | 2025 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 17.6 | 4300 | — | `S3_20260823T163004Z_020` |
| 株式会社iCARE | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社iCARE | 2025 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 11.99 | 4017 | — | `S2FC_20260823T162609Z_041` |
| 株式会社iCARE | 2025 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 10.09 | 4303 | — | `S3_20260823T162816Z_012` |
| 株式会社mov | 2024 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社mov | 2024 | s2-inspector | 1/1 (100.0%) | 25.9 | 100.0 | 13.28 | 4143 | — | `S2FC_20260823T162900Z_015` |
| 株式会社mov | 2024 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 11.94 | 4429 | — | `S3_20260823T162913Z_016` |
| 株式会社with | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社with | 2025 | s2-inspector | 1/1 (100.0%) | 25.9 | 100.0 | 10.93 | 3978 | — | `S2FC_20260823T163021Z_021` |
| 株式会社with | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 11.69 | 4264 | — | `S3_20260823T163032Z_022` |
| 株式会社アップガレージグループ | 2022 | s1 | 26/27 (96.3%) | 100.0 | 100.0 | 19.2 | 80660 | — | `S1_20260823T171558Z_050` |
| 株式会社アップガレージグループ | 2022 | s2-inspector | 25/27 (92.6%) | 100.0 | 100.0 | 14.51 | 81123 | — | `S2FC_20260823T163044Z_023` |
| 株式会社アップガレージグループ | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 13.5 | 8254 | — | `S3_20260823T163059Z_024` |
| 株式会社アップガレージグループ | 2023 | s1 | 22/22 (100.0%) | 100.0 | 100.0 | 20.46 | 87473 | — | `S1_20260823T171559Z_051` |
| 株式会社アップガレージグループ | 2023 | s2-inspector | failed | — | — | 0.87 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社アップガレージグループ | 2023 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 16.31 | 8441 | — | `S3_20260823T170823Z_028` |
| 株式会社アップガレージグループ | 2024 | s1 | 22/22 (100.0%) | 100.0 | 100.0 | 23.92 | 85036 | — | `S1_20260823T171600Z_052` |
| 株式会社アップガレージグループ | 2024 | s2-inspector | failed | — | — | 0.67 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社アップガレージグループ | 2024 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 16.79 | 8168 | — | `S3_20260823T170825Z_029` |
| 株式会社アップガレージグループ | 2025 | s1 | 22/22 (100.0%) | 100.0 | 100.0 | 19.85 | 88920 | — | `S1_20260823T171617Z_053` |
| 株式会社アップガレージグループ | 2025 | s2-inspector | failed | — | — | 0.73 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社アップガレージグループ | 2025 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 13.44 | 8864 | — | `S3_20260823T170827Z_030` |
| 株式会社キズキ | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社キズキ | 2025 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 11.98 | 3977 | — | `S2FC_20260823T163112Z_025` |
| 株式会社キズキ | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 10.89 | 4263 | — | `S3_20260823T163124Z_026` |
| 株式会社キッズコーポレーション | 2025 | s1 | failed | — | — | 0.0 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社キッズコーポレーション | 2025 | s2-inspector | 1/1 (100.0%) | 25.9 | 100.0 | 13.64 | 3957 | — | `S2FC_20260823T163135Z_027` |
| 株式会社キッズコーポレーション | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 11.92 | 4243 | — | `S3_20260823T163149Z_028` |
| 株式会社グッドパッチ | 2020 | s1 | 18/18 (100.0%) | 100.0 | 100.0 | 14.63 | 74346 | — | `S1_20260823T171619Z_056` |
| 株式会社グッドパッチ | 2020 | s2-inspector | failed | — | — | 0.45 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社グッドパッチ | 2020 | s3 | 18/18 (100.0%) | 100.0 | 100.0 | 16.25 | 7806 | — | `S3_20260823T170832Z_031` |
| 株式会社グッドパッチ | 2021 | s1 | 18/18 (100.0%) | 100.0 | 100.0 | 13.17 | 96328 | — | `S1_20260823T171624Z_057` |
| 株式会社グッドパッチ | 2021 | s2-inspector | failed | — | — | 0.54 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社グッドパッチ | 2021 | s3 | 18/18 (100.0%) | 100.0 | 100.0 | 13.07 | 7659 | — | `S3_20260823T170840Z_032` |
| 株式会社グッドパッチ | 2022 | s1 | 27/27 (100.0%) | 100.0 | 100.0 | 13.54 | 98746 | — | `S1_20260823T171634Z_058` |
| 株式会社グッドパッチ | 2022 | s2-inspector | failed | — | — | 0.55 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社グッドパッチ | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 11.7 | 7970 | — | `S3_20260823T163201Z_030` |
| 株式会社グッドパッチ | 2023 | s1 | 22/22 (100.0%) | 100.0 | 100.0 | 16.92 | 97932 | — | `S1_20260823T171637Z_059` |
| 株式会社グッドパッチ | 2023 | s2-inspector | failed | — | — | 0.86 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社グッドパッチ | 2023 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 11.25 | 7704 | — | `S3_20260823T170840Z_033` |
| 株式会社グッドパッチ | 2024 | s1 | 22/22 (100.0%) | 100.0 | 100.0 | 24.22 | 103561 | — | `S1_20260823T171637Z_060` |
| 株式会社グッドパッチ | 2024 | s2-inspector | failed | — | — | 0.94 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社グッドパッチ | 2024 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 11.62 | 8411 | — | `S3_20260823T170842Z_034` |
| 株式会社グッドパッチ | 2025 | s1 | 27/27 (100.0%) | 100.0 | 100.0 | 15.32 | 99755 | — | `S1_20260823T171648Z_061` |
| 株式会社グッドパッチ | 2025 | s2-inspector | failed | — | — | 0.91 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社グッドパッチ | 2025 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 14.1 | 8183 | — | `S3_20260823T170848Z_035` |
| 株式会社ストライダーズ | 2020 | s1 | 16/16 (100.0%) | 100.0 | 100.0 | 14.25 | 74115 | — | `S1_20260823T171654Z_062` |
| 株式会社ストライダーズ | 2020 | s2-inspector | failed | — | — | 0.37 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ストライダーズ | 2020 | s3 | 16/16 (100.0%) | 100.0 | 100.0 | 12.65 | 8228 | — | `S3_20260823T170852Z_036` |
| 株式会社ストライダーズ | 2021 | s1 | 16/16 (100.0%) | 100.0 | 100.0 | 16.69 | 77740 | — | `S1_20260823T171702Z_063` |
| 株式会社ストライダーズ | 2021 | s2-inspector | failed | — | — | 0.49 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ストライダーズ | 2021 | s3 | 16/16 (100.0%) | 100.0 | 100.0 | 16.89 | 8199 | — | `S3_20260823T170853Z_037` |
| 株式会社ストライダーズ | 2022 | s1 | 27/27 (100.0%) | 100.0 | 100.0 | 18.2 | 80089 | — | `S1_20260823T171703Z_064` |
| 株式会社ストライダーズ | 2022 | s2-inspector | 24/27 (88.9%) | 100.0 | 100.0 | 13.04 | 80754 | — | `S2FC_20260823T163213Z_031` |
| 株式会社ストライダーズ | 2022 | s3 | 24/27 (88.9%) | 100.0 | 100.0 | 13.03 | 7817 | — | `S3_20260823T163226Z_032` |
| 株式会社ストライダーズ | 2023 | s1 | failed | — | — | 4.17 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ストライダーズ | 2023 | s2-inspector | failed | — | — | 1.02 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ストライダーズ | 2023 | s3 | 19/20 (95.0%) | 100.0 | 100.0 | 15.01 | 7667 | — | `S3_20260823T170854Z_038` |
| 株式会社ストライダーズ | 2024 | s1 | failed | — | — | 3.59 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ストライダーズ | 2024 | s2-inspector | 15/16 (93.8%) | 100.0 | 100.0 | 21.52 | 79733 | — | `S2FC_20260823T171359Z_041` |
| 株式会社ストライダーズ | 2024 | s3 | 14/16 (87.5%) | 100.0 | 100.0 | 18.81 | 7904 | — | `S3_20260823T170902Z_039` |
| 株式会社ストライダーズ | 2025 | s1 | failed | — | — | 3.24 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ストライダーズ | 2025 | s2-inspector | 15/17 (88.2%) | 100.0 | 100.0 | 15.27 | 80519 | — | `S2FC_20260823T171400Z_042` |
| 株式会社ストライダーズ | 2025 | s3 | 15/17 (88.2%) | 100.0 | 100.0 | 17.9 | 8024 | — | `S3_20260823T170904Z_040` |
| 株式会社トーエネック | 2020 | s1 | failed | — | — | 2.43 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2020 | s2-inspector | failed | — | — | 0.63 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2020 | s3 | 12/13 (92.3%) | 100.0 | 100.0 | 13.47 | 7782 | — | `S3_20260823T170909Z_041` |
| 株式会社トーエネック | 2021 | s1 | failed | — | — | 2.63 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2021 | s2-inspector | failed | — | — | 0.71 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2021 | s3 | 12/13 (92.3%) | 92.6 | 100.0 | 22.18 | 8060 | +0 | `S3_20260823T170910Z_042` |
| 株式会社トーエネック | 2022 | s1 | failed | — | — | 5.35 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2022 | s2-inspector | failed | — | — | 0.86 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2022 | s3 | 21/21 (100.0%) | 100.0 | 100.0 | 15.27 | 8099 | — | `S3_20260823T163240Z_034` |
| 株式会社トーエネック | 2023 | s1 | failed | — | — | 5.48 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2023 | s2-inspector | failed | — | — | 1.34 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2023 | s3 | 13/13 (100.0%) | 100.0 | 100.0 | 12.92 | 7683 | — | `S3_20260823T170921Z_043` |
| 株式会社トーエネック | 2024 | s1 | failed | — | — | 6.48 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2024 | s2-inspector | failed | — | — | 1.42 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2024 | s3 | 13/13 (100.0%) | 100.0 | 100.0 | 16.77 | 8030 | — | `S3_20260823T170922Z_044` |
| 株式会社トーエネック | 2025 | s1 | failed | — | — | 6.56 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2025 | s2-inspector | failed | — | — | 1.61 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社トーエネック | 2025 | s3 | 13/13 (100.0%) | 100.0 | 100.0 | 13.95 | 8204 | — | `S3_20260823T170923Z_045` |
| 株式会社ナレッジワーク | 2025 | s1 | failed | — | — | 0.08 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社ナレッジワーク | 2025 | s2-inspector | failed | — | — | 1.69 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ナレッジワーク | 2025 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 12.21 | 4315 | — | `S3_20260823T170932Z_046` |
| 株式会社ハッピートラベル | 2025 | s1 | failed | — | — | 0.01 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社ハッピートラベル | 2025 | s2-inspector | failed | — | — | 3.77 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ハッピートラベル | 2025 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 10.52 | 4389 | — | `S3_20260823T170934Z_047` |
| 株式会社プレイド | 2020 | s1 | failed | — | — | 0.66 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2020 | s2-inspector | failed | — | — | 0.35 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2020 | s3 | 23/26 (88.5%) | 100.0 | 100.0 | 13.0 | 7887 | — | `S3_20260823T170937Z_048` |
| 株式会社プレイド | 2021 | s1 | failed | — | — | 0.8 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2021 | s2-inspector | failed | — | — | 0.44 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2021 | s3 | 19/22 (86.4%) | 100.0 | 100.0 | 12.77 | 7564 | — | `S3_20260823T170939Z_049` |
| 株式会社プレイド | 2022 | s1 | failed | — | — | 1.53 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2022 | s2-inspector | failed | — | — | 0.51 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 14.4 | 8392 | — | `S3_20260823T170944Z_050` |
| 株式会社プレイド | 2023 | s1 | failed | — | — | 6.16 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2023 | s2-inspector | failed | — | — | 1.41 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2023 | s3 | 19/19 (100.0%) | 100.0 | 100.0 | 15.06 | 7994 | — | `S3_20260823T170945Z_051` |
| 株式会社プレイド | 2024 | s1 | failed | — | — | 6.76 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2024 | s2-inspector | failed | — | — | 1.51 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2024 | s3 | 19/19 (100.0%) | 100.0 | 100.0 | 21.86 | 8515 | — | `S3_20260823T170950Z_052` |
| 株式会社プレイド | 2025 | s1 | failed | — | — | 6.66 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2025 | s2-inspector | failed | — | — | 1.72 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社プレイド | 2025 | s3 | 20/20 (100.0%) | 100.0 | 100.0 | 15.99 | 8344 | — | `S3_20260823T170952Z_053` |
| 株式会社ベルク | 2020 | s1 | failed | — | — | 2.21 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2020 | s2-inspector | failed | — | — | 0.77 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2020 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 12.69 | 7361 | — | `S3_20260823T170959Z_054` |
| 株式会社ベルク | 2021 | s1 | failed | — | — | 1.9 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2021 | s2-inspector | failed | — | — | 0.62 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2021 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 12.85 | 8004 | — | `S3_20260823T171000Z_055` |
| 株式会社ベルク | 2022 | s1 | failed | — | — | 2.06 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2022 | s2-inspector | 24/24 (100.0%) | 100.0 | 100.0 | 13.67 | 70646 | — | `S2FC_20260823T163302Z_041` |
| 株式会社ベルク | 2022 | s3 | 24/24 (100.0%) | 100.0 | 100.0 | 13.76 | 8347 | — | `S3_20260823T163315Z_042` |
| 株式会社ベルク | 2023 | s1 | failed | — | — | 3.21 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2023 | s2-inspector | failed | — | — | 0.99 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2023 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 13.14 | 7667 | — | `S3_20260823T171008Z_056` |
| 株式会社ベルク | 2024 | s1 | failed | — | — | 3.62 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2024 | s2-inspector | failed | — | — | 0.97 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2024 | s3 | 20/22 (90.9%) | 100.0 | 100.0 | 14.96 | 7489 | — | `S3_20260823T171011Z_057` |
| 株式会社ベルク | 2025 | s1 | failed | — | — | 3.73 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2025 | s2-inspector | failed | — | — | 1.0 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社ベルク | 2025 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 10.81 | 7555 | — | `S3_20260823T171012Z_058` |
| 株式会社レスタス | 2025 | s1 | failed | — | — | 0.06 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社レスタス | 2025 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 10.73 | 3960 | — | `S2FC_20260823T163329Z_043` |
| 株式会社レスタス | 2025 | s3 | 1/1 (100.0%) | 14.8 | 100.0 | 15.6 | 4246 | — | `S3_20260823T163340Z_044` |
| 株式会社伊豆シャボテン公園 | 2024 | s1 | failed | — | — | 0.04 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社伊豆シャボテン公園 | 2024 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 13.27 | 4020 | — | `S2FC_20260823T163355Z_045` |
| 株式会社伊豆シャボテン公園 | 2024 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 14.34 | 4306 | — | `S3_20260823T163409Z_046` |
| 株式会社寿々 | 2021 | s1 | failed | — | — | 0.04 | — | — | `RuntimeError: No readable page text remains, so there is not` |
| 株式会社寿々 | 2021 | s2-inspector | 1/1 (100.0%) | 14.8 | 100.0 | 14.51 | 3988 | — | `S2FC_20260823T163423Z_047` |
| 株式会社寿々 | 2021 | s3 | 1/1 (100.0%) | 25.9 | 100.0 | 13.09 | 4274 | — | `S3_20260823T171013Z_059` |
| 株式会社帝国ホテル | 2020 | s1 | failed | — | — | 2.04 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2020 | s2-inspector | failed | — | — | 0.55 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2020 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 12.07 | 8004 | — | `S3_20260823T171021Z_060` |
| 株式会社帝国ホテル | 2021 | s1 | failed | — | — | 1.07 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2021 | s2-inspector | failed | — | — | 0.54 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2021 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 11.83 | 8469 | — | `S3_20260823T171023Z_061` |
| 株式会社帝国ホテル | 2022 | s1 | failed | — | — | 1.9 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2022 | s2-inspector | failed | — | — | 0.59 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2022 | s3 | 27/27 (100.0%) | 100.0 | 100.0 | 14.38 | 7939 | — | `S3_20260823T171026Z_062` |
| 株式会社帝国ホテル | 2023 | s1 | failed | — | — | 2.8 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2023 | s2-inspector | failed | — | — | 0.83 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2023 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 13.18 | 7724 | — | `S3_20260823T171026Z_063` |
| 株式会社帝国ホテル | 2024 | s1 | failed | — | — | 3.16 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2024 | s2-inspector | failed | — | — | 0.84 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2024 | s3 | 22/22 (100.0%) | 100.0 | 100.0 | 13.27 | 8011 | — | `S3_20260823T171033Z_064` |
| 株式会社帝国ホテル | 2025 | s1 | failed | — | — | 3.54 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2025 | s2-inspector | failed | — | — | 1.01 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 株式会社帝国ホテル | 2025 | s3 | 17/17 (100.0%) | 100.0 | 100.0 | 14.96 | 8000 | — | `S3_20260823T171035Z_065` |
| 西尾レントオール株式会社 | 2020 | s1 | failed | — | — | 1.73 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2020 | s2-inspector | failed | — | — | 0.55 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2020 | s3 | 13/13 (100.0%) | 100.0 | 85.7 | 35.02 | 7776 | +3 | `S3_20260823T171040Z_066` |
| 西尾レントオール株式会社 | 2021 | s1 | failed | — | — | 3.33 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2021 | s2-inspector | failed | — | — | 0.62 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2021 | s3 | 12/16 (75.0%) | 100.0 | 85.7 | 32.33 | 8185 | +5 | `S3_20260823T171040Z_067` |
| 西尾レントオール株式会社 | 2022 | s1 | 16/21 (76.2%) | 100.0 | 100.0 | 28.15 | 85529 | — | `S1_20260823T171756Z_099` |
| 西尾レントオール株式会社 | 2022 | s2-inspector | failed | — | — | 0.53 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2022 | s3 | 17/21 (81.0%) | 88.9 | 100.0 | 48.99 | 8389 | +0 | `S3_20260823T171046Z_068` |
| 西尾レントオール株式会社 | 2023 | s1 | 13/13 (100.0%) | 100.0 | 100.0 | 33.22 | 86942 | — | `S1_20260823T171757Z_100` |
| 西尾レントオール株式会社 | 2023 | s2-inspector | failed | — | — | 1.2 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2023 | s3 | 13/13 (100.0%) | 100.0 | 85.7 | 26.11 | 7931 | +3 | `S3_20260823T171050Z_069` |
| 西尾レントオール株式会社 | 2024 | s1 | 14/16 (87.5%) | 100.0 | 85.7 | 26.78 | 86310 | — | `S1_20260823T171757Z_101` |
| 西尾レントオール株式会社 | 2024 | s2-inspector | failed | — | — | 1.08 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2024 | s3 | 14/16 (87.5%) | 88.9 | 100.0 | 42.38 | 7953 | +0 | `S3_20260823T171113Z_070` |
| 西尾レントオール株式会社 | 2025 | s1 | failed | — | — | 2.59 | — | — | `GLMError: HTTP 402: {'message': 'Insufficient credits. Add m` |
| 西尾レントオール株式会社 | 2025 | s2-inspector | 13/13 (100.0%) | 100.0 | 100.0 | 21.83 | 89221 | — | `S2FC_20260823T171427Z_073` |
| 西尾レントオール株式会社 | 2025 | s3 | 13/13 (100.0%) | 88.9 | 100.0 | 22.35 | 7990 | +0 | `S3_20260823T171115Z_071` |

## Failures

- 3M FY2022 `s1`: GLMError: HTTP 402: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.', 'code': 402, 'metadata': {'reason': 'in_flight_budget_exhausted', 'limit_source': 'openrouter_in_flight_budget', 'remedy_hint': 'Retry after your in-flight requests settle (see the Retry-After header). Adding credits at https://openrouter.ai/settings/credits raises your in-flight budget, up to a capped ceiling.', 'headers': {'Retry-After': '120'}, 'provider_name': None}}
- AppBank株式会社 FY2020 `s1`: GLMError: HTTP 402: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.', 'code': 402, 'metadata': {'reason': 'in_flight_budget_exhausted', 'limit_source': 'openrouter_in_flight_budget', 'remedy_hint': 'Retry after your in-flight requests settle (see the Retry-After header). Adding credits at https://openrouter.ai/settings/credits raises your in-flight budget, up to a capped ceiling.', 'headers': {'Retry-After': '120'}, 'provider_name': None}}
- AppBank株式会社 FY2021 `s1`: GLMError: HTTP 402: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.', 'code': 402, 'metadata': {'reason': 'in_flight_budget_exhausted', 'limit_source': 'openrouter_in_flight_budget', 'remedy_hint': 'Retry after your in-flight requests settle (see the Retry-After header). Adding credits at https://openrouter.ai/settings/credits raises your in-flight budget, up to a capped ceiling.', 'headers': {'Retry-After': '120'}, 'provider_name': None}}
- AppBank株式会社 FY2022 `s1`: GLMError: HTTP 402: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.', 'code': 402, 'metadata': {'reason': 'in_flight_budget_exhausted', 'limit_source': 'openrouter_in_flight_budget', 'remedy_hint': 'Retry after your in-flight requests settle (see the Retry-After header). Adding credits at https://openrouter.ai/settings/credits raises your in-flight budget, up to a capped ceiling.', 'headers': {'Retry-After': '120'}, 'provider_name': None}}
- AppBank株式会社 FY2023 `s1`: GLMError: HTTP 402: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.', 'code': 402, 'metadata': {'reason': 'in_flight_budget_exhausted', 'limit_source': 'openrouter_in_flight_budget', 'remedy_hint': 'Retry after your in-flight requests settle (see the Retry-After header). Adding credits at https://openrouter.ai/settings/credits raises your in-flight budget, up to a capped ceiling.', 'headers': {'Retry-After': '120'}, 'provider_name': None}}
- AppBank株式会社 FY2025 `s1`: GLMError: HTTP 402: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.', 'code': 402, 'metadata': {'reason': 'in_flight_budget_exhausted', 'limit_source': 'openrouter_in_flight_budget', 'remedy_hint': 'Retry after your in-flight requests settle (see the Retry-After header). Adding credits at https://openrouter.ai/settings/credits raises your in-flight budget, up to a capped ceiling.', 'headers': {'Retry-After': '120'}, 'provider_name': None}}
- Byside株式会社 FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- JR九州エンジニアリング株式会社 FY2022 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- JUKI産機テクノロジー株式会社 FY2022 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- キャディ株式会社 FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- クラスター株式会社 FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- ダイニチ工業株式会社 FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ダイニチ工業株式会社 FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ハコベル株式会社 FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- ファインディ株式会社 FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- メディフォン株式会社 FY2021 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- ラクスル株式会社 FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ラクスル株式会社 FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ラクスル株式会社 FY2022 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ラクスル株式会社 FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ラクスル株式会社 FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- ラクスル株式会社 FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2022 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- リソルホールディングス株式会社 FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 吉田海運株式会社 FY2022 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 坂善商事株式会社 FY2023 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 大西運輸株式会社 FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 大西運輸株式会社 FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 日本テーマパーク開発株式会社 FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 日本テーマパーク開発株式会社 FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社FABRIC TOKYO FY2023 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社FABRIC TOKYO FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社FLUX FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社Morght FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社PIGNUS（ピグナス） FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社SANU FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社iCARE FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社mov FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社with FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社アップガレージグループ FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社アップガレージグループ FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社アップガレージグループ FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社キズキ FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社キッズコーポレーション FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社グッドパッチ FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社グッドパッチ FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社グッドパッチ FY2022 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社グッドパッチ FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社グッドパッチ FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社グッドパッチ FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ストライダーズ FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ストライダーズ FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ストライダーズ FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ストライダーズ FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ストライダーズ FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ストライダーズ FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2022 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2022 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社トーエネック FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ナレッジワーク FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社ナレッジワーク FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ハッピートラベル FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社ハッピートラベル FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2022 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2022 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社プレイド FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2022 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社ベルク FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社レスタス FY2025 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社伊豆シャボテン公園 FY2024 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社寿々 FY2021 `s1`: RuntimeError: No readable page text remains, so there is nothing safe to send to the model. This document needs OCR or a vision-capable strategy.
- 株式会社帝国ホテル FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2022 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2022 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2023 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2024 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 株式会社帝国ホテル FY2025 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2020 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2020 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2021 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2021 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2022 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2023 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2024 `s2-inspector`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
- 西尾レントオール株式会社 FY2025 `s1`: GLMError: HTTP 402: {'message': 'Insufficient credits. Add more using https://openrouter.ai/settings/credits', 'code': 402, 'metadata': {'limit_source': 'openrouter_credits', 'remedy_hint': 'Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance.'}}
