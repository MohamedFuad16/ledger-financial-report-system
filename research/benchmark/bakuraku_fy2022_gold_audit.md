# Bakuraku FY2022 gold audit

Audit date: 2026-08-22. Unit: M JPY. Scope: the asset-side 27-row schema.

## Method

1. Pin the exact official filing by SHA-256 and confirm company, fiscal period,
   currency, page count, and consolidated balance-sheet page.
2. Inspect cited pages using `pdftotext -layout` and independently using
   PyMuPDF embedded-text extraction.
3. Reconcile the seven schema identities without consulting model confidence.
4. Preserve the filing's disclosed quantum after conversion to millions.
5. Omit a row only when the source cannot support the requested gross value.

Candidate Strategy 3 runs were used only to navigate source pages. Their values
were not accepted as gold without both source checks.

## Semantic audit decisions

- `長期前払費用` is a long-term prepaid asset in Other Fixed Assets, not the
  separate Deferred Charges row (`繰延資産`). This corrects Dainichi and Raksul.
- `出資金` is an investment. Resol's financial-instruments note supports moving
  that disclosed component from residual Other Fixed Assets into Investments.
- A disclosed one-year loan-receivable maturity belongs in Short-term Loan and
  is removed from residual Other Current Assets. This corrects Plaid.
- A current unallocated doubtful-debt allowance nets trade/current receivables;
  a long-term allowance within `投資その他の資産` nets the financial bucket.
  This corrects Imperial Hotel and Striders.
- When a residual other-assets line contains one disclosed financial component,
  only that component moves; the undisclosed remainder stays in Other Fixed
  Assets. This prevents Resol's entire residual from being misclassified.

## Completeness

Nine filings support all 27 rows. Resol supports 24. Its filing prints net PPE
categories and aggregate depreciation but does not disclose the three requested
gross categories Buildings, Plant & Machinery, and Other Equipment. Those rows
are listed as unscorable; no algebraic allocation or model guess was used.

The machine-readable fixture, including exact citations and audit-pass metadata,
is `benchmark_data/bakuraku_fy2022_gold.json`. The materializer is
`research/benchmark/materialize_bakuraku_gold.py`.
