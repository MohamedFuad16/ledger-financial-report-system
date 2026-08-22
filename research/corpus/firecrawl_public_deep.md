# Firecrawl annual-report availability

- Job: `7d066af8e8c1` (complete)
- Updated: 2026-08-22T16:43:41.438626+00:00
- Bakuraku clients: 16
- Company/year requests: 96
- Status counts: downloaded=1, not_downloaded=95

`candidate_found` is company-level discovery progress, not a claim that every year has a usable PDF. Only `downloaded` rows identify screened, pinned files; benchmark gold still requires two independent reviews.

Post-run audit: the one admitted file was titled `四 半 期 報 告 書`; it was a
quarterly report whose display spacing bypassed the initial literal exclusion.
It was deleted from the live corpus and the classifier now normalizes Unicode
and whitespace before checking document type. Therefore this job produced zero
valid annual-report sets and zero new gold keys.
