# Fifty-company annual-report rebuild

The acquisition cohort must be selected exclusively from the evidence-backed
112-company Bakuraku customer-story registry. A target is admitted only when
the same legal entity has public annual filings; a parent-company filing must
not be substituted for a private subsidiary.

Every one of the 112 targets is sent through Firecrawl; no target is skipped
because of an assumption about whether it is public or private. The registry
includes companies, municipalities, hospitals, associations and subsidiaries,
so customer evidence alone is not proof that an independent six-year public
filing series exists. The cohort audit records the observed Firecrawl result
explicitly instead of inventing reports or silently changing the legal entity.

Acquisition uses Firecrawl only to discover candidate report URLs from the
official entry point. A candidate is downloaded locally, screened as an annual
report, checked for company/year identity, and pinned by SHA-256. Firecrawl
output never becomes benchmark gold.

Gold requires two independent passes over the exact pinned PDF. Each pass must
record the statement page, reporting currency, scale, fiscal-year column,
directly disclosed rows, derived arithmetic and rows that the filing does not
separately disclose. Only exact agreement between both passes may be marked
`independently_verified`; unsupported schema splits stay explicitly
unscorable.

## Availability status

Run `python research/corpus/summarize_firecrawl_job.py JOB_JSON` after saving a
corpus-job response. The script writes a CSV, JSON and Markdown ledger with one
row per Bakuraku client and year. `found` means Firecrawl discovered at least
one candidate for the company; `downloaded` means a candidate passed download
and PDF screening; neither status means the document is benchmark gold.
