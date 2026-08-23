# Forty-client golden corpus

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

Firecrawl can parse public PDFs, follow JavaScript-driven pages and reuse
caller-authorized headers, cookies or persistent browser state. Those features
do not make a private document public and do not authorize bypassing an access
control. If the caller does not have permission and credentials, the source is
out of scope.

Gold requires two independent passes over the exact pinned PDF. Each pass must
record the statement page, reporting currency, scale, fiscal-year column,
directly disclosed rows, derived arithmetic and rows that the filing does not
separately disclose. Only exact agreement between both passes may be marked
`independently_verified`; unsupported schema splits stay explicitly
unscorable.

`discover_statutory_filings.py` checkpoints a broad Firecrawl PDF search for
all 112 clients. `discover_gazette_filings.py` resolves exact-entity public
gazette announcement images as a fallback for clients without a full report.
`materialize_statutory_gold.py` accepts a condensed announcement only when its
structured index total agrees with a local RapidOCR read of both balancing
totals. Those records score only `Total Assets`; all other 26 rows remain
explicitly unscorable. Together with the 13 full-report clients, the maintained
fixture contains 40 unique Bakuraku clients. 3M stays first as the separate
assignment control and is not counted as a Bakuraku client.

## Availability status

Run `python research/corpus/summarize_firecrawl_job.py JOB_JSON` after saving a
corpus-job response. The script writes a CSV, JSON and Markdown ledger with one
row per Bakuraku client and year. `found` means Firecrawl discovered at least
one candidate for the company; `downloaded` means a candidate passed download
and PDF screening; neither status means the document is benchmark gold.
