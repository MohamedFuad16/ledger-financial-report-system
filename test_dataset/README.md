# Test dataset — 3M Annual Reports (FY2020–FY2025)

Evaluation inputs for the asset-side balance-sheet extraction task. The
assignment specifies the **FY2022** report; the other five years are here so the
system can be checked for generality rather than tuned to one document.

Files are normalized to `3M_annual_report_<fiscal year>.pdf`. The fiscal year in each
name is the year the report's financial statements **cover**, verified from the
consolidated balance sheet inside each PDF (not from the publisher's filename).

Source: <https://investors.3m.com/financials/annual-reports-proxy-statements>

| File | FY | Pages | Balance-sheet page | Text layer | Golden answers | Original filename |
|---|---|---|---|---|---|---|
| `3M_annual_report_2020.pdf` | 2020 | 160 | 71 | OK (heavy NBSP use) | yes | `2020_3M_Annual_Report.pdf` |
| `3M_annual_report_2021.pdf` | 2021 | 142 | 55 | **broken on 71 pages** | yes | `3M_2021_Annual_Report_Web-(3).pdf` |
| `3M_annual_report_2022.pdf` | 2022 | 141 | 58 | OK | yes (official, from the assignment) | `3M 2022 Annual Report_Updated.pdf` |
| `3M_annual_report_2023.pdf` | 2023 | 126 | 54 | OK | yes | `40009_3M_2023_Annual_Report_online_pdfa.pdf` |
| `3M_annual_report_2024.pdf` | 2024 | 132 | 55 | OK | yes | `2024_3M_Annual_Report FINAL.pdf` |
| `3M_annual_report_2025.pdf` | 2025 | 120 | 50 | OK | partial (19/27) | `2025 3M Annual Report - final.pdf` |

## Ground truth

Golden answers live in `schema.py` (`GOLDEN_ANSWERS_STORE`), not here, so there
is exactly one copy. The FY2022 set is the official answer key from the
assignment document; FY2020/2021/2023/2024 were derived by applying the same
mapping convention to those reports.

Two independent checks are in `test_contract.py` and are run on every test pass:

- every stored year reconciles internally (each subtotal equals the sum of its
  components, and Total Assets equals Current + Fixed + Deferred);
- the totals were cross-checked against the printed `Total assets` line in each
  PDF: 2020 = 47,344 · 2021 = 47,072 · 2022 = 46,455 · 2023 = 50,580 ·
  2024 = 39,868 (M USD).

FY2025 has a **partial** key: 19 of the 27 rows, covering only what can be read
directly off the printed FY2025 statements (balance sheet page 50, PP&E note
page 54) plus the four rows that are structurally zero in every verified year.
It reconciles: Quick 8,768 + Inventories 3,661 + Other current 3,958 =
Total current assets 16,387 as printed; Land 202 + Buildings 7,729 +
Machinery 15,328 + CIP 663 = gross PP&E 23,922 as printed, and less accumulated
depreciation 16,821 = net 7,101 as printed; Goodwill 6,419 + Intangibles 1,103 =
7,522; Total assets 37,733 as printed.

Eight rows are **deliberately omitted** rather than guessed: Other Equipment,
Tangible Assets, Fixed Assets, Financial Assets, Investments, Long-term Loan,
Other Financial Assets and Other Fixed Assets. 3M dropped the separate
"Operating lease right of use assets" line in FY2025 and folded it into "Other
assets", so those rows need the leases and other-assets notes plus a mapping
judgement that was not supplied with the assignment. `compute_metrics` scores
only the items present, so an FY2025 run reports *n*/19 — never graded against
invented values, and never compared against another year.

## Known input defect: FY2021

The FY2021 PDF embeds its financial-statement pages with subset TrueType fonts
using `Identity-H` encoding and **no `ToUnicode` CMap, no `cmap` table and no
`post` table**. Text extraction returns raw glyph ids, not characters — page 55
(the consolidated balance sheet) comes out as `\x1cIFF9BH\x015GG9HG` where the
page visually reads `Current assets`.

The mapping is not recoverable from the file: nothing in the embedded font
relates glyph id to character. 71 of 142 pages are affected, including the
balance sheet and the income statement; the notes (pages 58+) are readable, so
the PP&E breakdown can still be extracted while the face of the balance sheet
cannot.

`extraction.py` detects this (`garble_ratio`) and attaches a warning to the run
instead of sending glyph soup to the model. The stored FY2021 run scored 3.7%
(1/27) for exactly this reason — a *document* failure, not a model failure. The
remedy is OCR or a vision model over the rendered pages, which is out of scope
for the two text-based strategies here.
