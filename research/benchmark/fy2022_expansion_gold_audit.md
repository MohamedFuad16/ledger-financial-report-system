# FY2022 gold expansion audit

Five exact annual-report PDFs were pinned by SHA-256 after source discovery. Strategy 3 was run only to navigate candidate pages. No candidate confidence value and no prior answer key was used to approve a row.

## Independent checks

1. Poppler `pdftotext -layout` was used to inspect each consolidated statement and cited note.
2. PyMuPDF extracted the same pages independently. Source hash, page count, and key statement figures are reproducibly checked by `verify_fy2022_expansion_sources.py`.
3. Retained values were mapped to the 27-row schema and arithmetic identities were checked where all children were disclosed.

| Company | Exact source | Gold rows | Deliberately unscored |
|---|---:|---:|---|
| 株式会社アップガレージグループ | `dc12…e5d5` | 27 | none |
| 株式会社トーエネック | `0a90…9b57` | 22 | combined machinery/equipment and undisclosed fixed-asset residual splits |
| 西尾レントオール株式会社 | `fdf4…ff60` | 21 | PPE classes presented net and undisclosed fixed-asset residual splits |
| トヨタ自動車株式会社 | `8608…e50c` | 27 | none |
| ソニーグループ株式会社 | `262c…441` | 19 | combined receivables, combined machinery/other tangible assets, and combined long-term financial categories |

The partial keys are intentional. A directly disclosed subtotal remains scorable even when the filing does not disclose the schema's requested child split. Missing child rows are not treated as zero and are not inferred from a model response.

## Corrections made after the second pass

- Up Garage: the `7.207` million yen one-year portion of long-term loans is a short-term loan receivable; it is removed from the residual current-assets bucket.
- TOENEC: `機械、運搬具及び工具器具備品` is a single combined line, so Plant & Machinery and Other Equipment are not separately scored.
- Nishio: `34,097` million yen is leased assets included in rental assets, not accumulated depreciation. The filing's actual accumulated depreciation is `181,555` million yen, while the PPE component lines are net amounts.
- Sony: the consolidated statement is filing page 111. The parent-only balance sheet near the end of the filing is not benchmark gold.

All retained values are in millions of JPY. Thousand-yen Up Garage source values preserve a `0.001` million-yen quantum; all other sources have a `1.0` million-yen quantum.
