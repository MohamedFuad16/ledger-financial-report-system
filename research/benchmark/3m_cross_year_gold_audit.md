# 3M cross-year source-bound gold audit

Audit date: 2026-08-22. Units are USD millions. These keys are evaluation-only
and are never included in an LLM prompt.

## Method

Each report received two independent checks:

1. Read the printed face statement and the cited note visually. For FY2021,
   whose embedded font has no usable character map, render at 200 DPI and run
   local RapidOCR PP-OCRv6, then compare the OCR output back to the rendered
   page. For FY2023–FY2025, use both native layout text and the rendered page.
2. Recalculate all schema subtotals from the cited source lines and enforce the
   seven deterministic identities. A value is retained only when both checks
   agree. The exact PDF SHA-256 binds the key to the audited bytes.

## FY2021 — complete 27-row key

- File SHA-256: `33beb4a185b095d15dcd3259d57bfb46f05953cb0241804bd17417da39000da9`
- Face statement: PDF page 55 (printed page 47).
- Supplemental balance-sheet table: PDF page 77 (printed page 69).
- Face evidence: cash 4,564; receivables 4,660; marketable securities 201;
  inventories 4,985; prepaids 654; other current assets 339; current assets
  15,403; net PP&E 9,429; operating-lease ROU assets 858; goodwill 13,486;
  intangibles 5,288; other assets 2,608; total assets 47,072.
- Note evidence: land 312; buildings 8,086; machinery 17,305; construction in
  progress 1,510; accumulated depreciation (17,784); prepaid pension 943;
  insurance receivables 51; cash-surrender value 261; equity-method investments
  129; equity/other investments 133; deferred taxes 581; other 510.
- Recalculation: Quick 4,564 + 4,660 = 9,224. Other current 201 + (654 + 339)
  = 1,194. Tangible 9,429 + 858 = 10,287. Intangible 13,486 + 5,288 = 18,774.
  Investments 129 + 133 = 262. Other financial 943 + 51 + 261 = 1,255;
  Financial 262 + 1,255 = 1,517. Other fixed 581 + 510 = 1,091. Fixed
  10,287 + 18,774 + 1,517 + 1,091 = 31,669. Total 15,403 + 31,669 = 47,072.

## FY2023 — complete 27-row key

- File SHA-256: `2304e28144e0cc53fb23889a5504aa4661facddbc241bb8c5079cbe990500569`
- Face statement: PDF page 54 (printed page 46).
- Supplemental balance-sheet table: PDF page 67 (printed page 59).
- Face evidence: cash 5,933; receivables 4,750; marketable securities 53;
  inventories 4,822; prepaids 485; other current assets 336; current assets
  16,379; net PP&E 9,159; ROU assets 759; goodwill 12,927; intangibles 4,226;
  other assets 7,130; total assets 50,580.
- Note evidence: land 255; buildings 7,908; machinery 16,855; construction in
  progress 1,852; accumulated depreciation (17,711); prepaid pension 1,253;
  insurance receivables 33; cash-surrender value 270; equity-method investments
  74; equity/other investments 170; deferred taxes 4,918; other 412.
- Recalculation: Quick 5,933 + 4,750 = 10,683. Other current 53 + (485 + 336)
  = 874. Tangible 9,159 + 759 = 9,918. Intangible 12,927 + 4,226 = 17,153.
  Investments 74 + 170 = 244. Other financial 1,253 + 33 + 270 = 1,556;
  Financial 244 + 1,556 = 1,800. Other fixed 4,918 + 412 = 5,330. Fixed
  9,918 + 17,153 + 1,800 + 5,330 = 34,201. Total 16,379 + 34,201 = 50,580.

## FY2024 — complete 27-row key

- File SHA-256: `886ee296081a9bdd17671011eb75336ddedd4afaefe0e1803aacc7640feee760`
- Face statement: PDF page 55 (printed page 47).
- Supplemental balance-sheet table: PDF page 69 (printed page 61).
- Face evidence: cash 5,600; receivables 3,194; marketable securities 2,128;
  inventories 3,698; prepaids 436; other current assets 828; current assets
  15,884; net PP&E 7,388; ROU assets 565; goodwill 6,281; intangibles 1,210;
  other assets 8,540; total assets 39,868.
- Note evidence: land 200; buildings 7,432; machinery 14,780; construction in
  progress 994; accumulated depreciation (16,018); prepaid pension 1,243;
  insurance receivables 31; cash-surrender value 257; equity-method investments
  75; equity/other investments 2,430; deferred taxes 4,146; other 358.
- Recalculation: Quick 5,600 + 3,194 = 8,794. Other current 2,128 + (436 + 828)
  = 3,392. Tangible 7,388 + 565 = 7,953. Intangible 6,281 + 1,210 = 7,491.
  Investments 75 + 2,430 = 2,505. Other financial 1,243 + 31 + 257 = 1,531;
  Financial 2,505 + 1,531 = 4,036. Other fixed 4,146 + 358 = 4,504. Fixed
  7,953 + 7,491 + 4,036 + 4,504 = 23,984. Total 15,884 + 23,984 = 39,868.

## FY2025 — verified 22-row partial key

- File SHA-256: `7c831a3861a34f8cfcc1fec2a105595280eca61db4324bcfb252a3215ee8c267`
- Face statement: PDF page 50 (printed page 42).
- PP&E note: PDF page 54 (printed page 46).
- Leases note: PDF page 104 (printed page 96).
- Face evidence: cash 5,235; receivables 3,533; marketable securities 698;
  inventories 3,661; prepaids 391; assets held for sale 46; other current assets
  2,823; current assets 16,387; net PP&E 7,101; goodwill 6,419; intangibles
  1,103; other assets 6,723; total assets 37,733.
- PP&E/lease evidence: land 202; buildings 7,729; machinery 15,328;
  construction in progress 663; accumulated depreciation (16,821); operating
  lease ROU assets 516.
- Recalculation: Quick 5,235 + 3,533 = 8,768. Other current 698 + (391 + 46 +
  2,823) = 3,958. Tangible 7,101 + 516 = 7,617. Intangible 6,419 + 1,103 =
  7,522. Fixed 37,733 - 16,387 = 21,346.
- Deliberately unscored: Financial Assets, Investments, Long-term Loan, Other
  Financial Assets and Other Fixed Assets. The FY2025 PDF does not disclose the
  supplemental Other-assets component table needed to split its remaining
  6,207 (6,723 less ROU 516). Assigning those five rows would be conjecture.

## Result

FY2021, FY2023 and FY2024 are complete, reconciled 27-row keys. FY2025 is an
honest 22-row partial key. Benchmark accuracy for FY2025 must therefore be
reported as exact matches out of 22, never out of 27 and never against invented
values.
