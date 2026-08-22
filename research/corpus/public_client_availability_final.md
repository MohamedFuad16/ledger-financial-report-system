# Public Bakuraku client annual-report availability

Audit date: 2026-08-23 (Asia/Tokyo).

## Public-client ceiling

The evidence-backed Bakuraku registry contains 112 exact client legal names.
The official JPX list dated 2026-07-31 contains 16 current TSE-listed matches
under the same legal name (including the verified ホーライ/ホウライ orthographic
alias). The machine-readable match ledger is `jpx_public_bakuraku_clients.csv`.
The requested target of 50 public Bakuraku clients is therefore not present in
the supplied 112-client population; parent companies were not substituted for
private subsidiaries.

JPX source: https://www.jpx.co.jp/markets/statistics-equities/misc/01.html

## Firecrawl audit

| Pass | Job | Scope | Requested company-years | Raw downloads | Valid new annual reports |
|---|---|---:|---:|---:|---:|
| All Bakuraku clients | `7d7afbcac4a7` | 112 clients × FY2020-FY2025 | 672 | 5 | 0 |
| Deep exact company/year retry | `7d066af8e8c1` | 16 candidate public clients × FY2020-FY2025 | 96 | 1 | 0 |
| JPX completion retry | `d48327f247ea` | NS Group × FY2020-FY2025 | 6 | 0 | 0 |
| **Total** |  |  | **774** | **6** | **0** |

The six raw downloads were rejected during post-run identity audit: quarterly
reports, a future-period FY2026 report relabelled as FY2025, and/or reports whose
selected balance-sheet page did not confirm the requested current fiscal year.
No Firecrawl/model candidate was promoted to gold.

## Production state

- Stored corpus documents: 0.
- New complete five-year client series: 0.
- New gold keys: 0.
- Existing audited runtime gold remains available: 19 SHA-bound source keys
  with 486 scorable rows, plus the assignment-supplied 3M FY2022 key with 27
  rows (513 scorable rows across 20 company-years in total).
- Recoverable pre-clean corpus backup:
  `/opt/ledger/backups/corpus-before-50x6-20260822T143000Z.tar.gz`
  (SHA-256 `303b5233d8a9e832feec10f7eceabe00b8bf9d9b60da97e1a7500640747c94db`).

## Admission rules now enforced

1. Reject quarterly, interim and earnings-release vocabulary after NFKC and
   whitespace normalization.
2. Assign each search result to one primary reporting year only.
3. Do not hide a newer out-of-range reporting period to force a match.
4. Require the requested year to be current on the selected balance-sheet page.
5. Require exact entity provenance through the official domain/official page
   chain or exact-entity EDINET metadata.
6. Treat every accepted PDF as review-required until two independent source
   reviews approve a SHA-bound 27-row key.
