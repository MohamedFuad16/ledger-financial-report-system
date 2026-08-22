# Bakuraku customer FY2022 benchmark status

Date: 2026-08-22

## Scope

The ten-company seed list is recorded in `research/bakuraku/benchmark_10.csv`:
AppBank, note, Dainichi, Raksul, Resol, Imperial Hotel, Goodpatch, Striders,
Plaid, and Belc. Each company is directly evidenced as a public Bakuraku
customer; annual reports must still come from the company's official IR archive.

## Acquisition status

- AppBank FY2022: downloaded, screened `ok`, 117 pages, exact PDF SHA-256
  `e6ee6133...`; balance sheet begins on PDF page 67.
- Dainichi FY2022: downloaded, screened `ok`, 70 pages, exact PDF SHA-256
  `2a68998f...`; balance sheet begins on PDF page 34.
- Official IR/archive routes are identified for the remaining eight companies.
  Goodpatch's FY2022 securities filing has also been resolved to its direct
  official XJ-Storage PDF URL, but it has not been admitted to a benchmark run.

The acquisition path was hardened during this pass. A year-stamped Resol news
release had been accepted by the old broad PDF heuristic. That file and manifest
entry were removed, discovery now requires explicit annual/securities-report
language, and canonical replacement is forbidden unless local screening returns
`ok`. Japanese company names are now preserved as Unicode filesystem slugs.

## Benchmark boundary

These Japanese filings report JPY, commonly in thousands of yen. The extraction
contract currently labels every answer `answer_m_usd`. Relabeling JPY as USD
would create false gold, while currency conversion would require a documented FX
date/source/rounding policy and would reduce exact comparability with the source
tables.

No human-reviewed golden tables or Strategy 2/3 accuracy claims will be created
for this cohort until the benchmark contract explicitly chooses either:

1. Native-currency millions, with currency and source-unit fields; or
2. M USD conversion under a fixed, auditable FX policy.

The first option is recommended because it tests extraction and semantic mapping
without mixing exchange-rate error into the benchmark.
