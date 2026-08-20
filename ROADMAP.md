# Roadmap

Planned work, in order. Nothing here is built yet. When the owner says *"build
the corpus builder"* or *"scale up the dataset"*, this file is the spec.

---

## Sequencing gates

The large-scale corpus is **step 3**. Do not start it early — a bigger dataset
measured with an unfinished pipeline produces numbers nobody can trust.

| # | Gate | Status |
|---|---|---|
| 1 | Strategies 1–4 implemented and each verified on the 6-document set | **S1 ✅, S2 ✅ (bake-off, pdf-inspector chosen), S3 ✗, S4 ✗** |
| 2 | Re-run all 6 documents through **all four** strategies, back to back, same settings; publish the comparison table | not started |
| 3 | Build the Firecrawl corpus builder and re-measure at scale | not started — this document |

Strategies 3 and 4 are stubs today (see the dashboard cards: "Hybrid Retrieval &
RAG", "Agentic Accounting"). Gate 2 is a repeat of the experiment already run
for S1 vs S2 (see README, *Results*), extended to 4 strategies.

---

## Step 3: large-scale corpus via Firecrawl

### Goal

Move from 6 documents / 1 company to roughly **100 companies × several fiscal
years** of annual reports, so accuracy is measured across filers with different
statement layouts, terminology and PDF toolchains — not against 3M's house
style, which every current number reflects.

This directly answers the assignment's instruction that the system should
generalise: *「他企業のAnnual Reportが入力となることも考慮した汎用的なシステムを構築する
ことを意識してください」*.

### Firecrawl is already wired up

- **MCP server**: `firecrawl` → `https://mcp.firecrawl.dev/v2/mcp`, registered at
  user scope with the API key as an `Authorization: Bearer` header. `claude mcp
  list` shows it Connected. No interactive login needed.
- **Key**: `FIRECRAWL_API_KEY` in `.env` (gitignored). `.env.example` carries an
  empty placeholder. The key is never written to any tracked file.
- **CLI alternative**, if a future session prefers it to MCP:
  `npx -y firecrawl-cli@latest init --all --browser`

### What to build

A `corpus/` package, kept **separate from the extraction pipeline** so the
benchmark code stays free of network dependencies:

```
corpus/
├── discover.py     # company list → annual-report PDF URLs
├── fetch.py        # download + dedupe + fiscal-year detection
├── screen.py       # reject unusable PDFs before they reach the benchmark
└── manifest.py     # write/read corpus_manifest.json
```

**`discover.py`** — for each company, find the annual report PDFs.

Firecrawl call order (cheapest signal first, same discipline as the CLI skills):

1. `search` — `"<company> annual report <year> filetype:pdf"` and
   `"<company> investor relations annual report"` to find the IR page.
2. `map` — enumerate URLs under the IR domain; keep those matching
   `annual|10-k|report` and ending `.pdf`. This is the workhorse: one map call
   per IR site usually yields every year at once.
3. `scrape` — only when the IR page renders its PDF list client-side and `map`
   comes back thin.
4. `interact` — last resort, for IR pages behind a year-selector dropdown or a
   cookie wall.

Do **not** use `crawl` as the default. A full crawl of an IR domain returns
hundreds of irrelevant pages; `map` + a URL filter is far cheaper and is what
this task actually needs. Reserve `crawl` for sites where `map` is blocked.

`monitor` is worth a second pass later: a monitor per IR page with
`--goal "a new annual report PDF was published"` keeps the corpus current
without re-running discovery.

**`fetch.py`** — download each PDF, hash it, and detect the fiscal year from the
document rather than the filename. The 6-document set already proved filenames
lie: `2024_3M_Annual_Report FINAL.pdf` covers FY2024, but publishers are
inconsistent, and `3M_2021_Annual_Report_Web-(3).pdf` had to be confirmed from
`For the Year Ended December 31, 2021` inside the PDF. Reuse that check: find
the consolidated balance sheet page, read the `At December 31, <year>` heading.

**`screen.py`** — reject documents the benchmark cannot fairly score, *before*
spending model tokens:

- `extraction.garble_ratio` over every page — 1 of the 6 current documents
  (FY2021) has an unreadable text layer on 71 of 142 pages. At 100 companies
  expect a meaningful fraction. Screen them into a separate `unreadable/` bucket
  and report the rate; do not silently drop them, it is a finding.
- No consolidated balance sheet page found → reject.
- Non-USD reporting currency → tag it, don't reject; the schema wants M USD and
  the conversion behaviour is worth measuring separately.
- Page count or token estimate wildly outside the 100–200 page norm → tag.

**`manifest.py`** — one `corpus_manifest.json`, the single source of truth:

```json
{
  "company": "3M Company",
  "ticker": "MMM",
  "fiscal_year": "2022",
  "source_url": "https://investors.3m.com/...",
  "local_path": "corpus_dataset/3M/2022/20260820T143852Z/3M_annual_report_2022.pdf",
  "sha256": "708a1e60...",
  "pages": 141,
  "readable_pages": 141,
  "balance_sheet_page": 58,
  "currency": "USD",
  "screened": "ok",
  "golden_answers": null
}
```

Filenames follow the normalized convention requested for corpus work:
`<Company>_annual_report_<FY>.pdf`.

### The hard part: ground truth at scale

**This is the blocking design problem, and it must be decided before any
large-scale accuracy number is published.**

The current 27-row answer keys exist for 3M only, and even those took manual
verification (FY2025 is still a partial 19-row key because 3M reclassified its
right-of-use assets). Hand-labelling 100 companies × 27 rows is ~2,700 judgement
calls. Options, worst to best:

1. **LLM-generated keys** — circular. The thing being measured generates the
   thing measuring it. Not acceptable for a headline accuracy number.
2. **Structural self-consistency only** — no answer key; score whether the
   model's own output reconciles. Now implemented in `reconcile.py`, and
   **measured to be a weak signal**: across 48 scored runs, 47 pass all seven
   identities while averaging only 72.1% accuracy. A misclassification stays
   self-consistent, so this cannot stand alone as the scale metric. Keep it as
   a cheap negative filter (a run that *fails* reconciliation is definitely
   broken) rather than as evidence a run is right.
3. **Anchor rows from the printed statements** — automatically extract the
   handful of rows that appear verbatim on the face of the balance sheet (cash,
   receivables, inventories, gross PP&E components, accumulated depreciation,
   goodwill, total assets) with a deterministic parser, and score only those.
   This is exactly how the FY2025 partial key was built, and it reconciled
   against every printed total. Scales, and is not circular.
4. **A hand-labelled stratified sample** — full 27-row keys for ~10 companies
   chosen to span layouts, used to calibrate how well (3) predicts full accuracy.

**Recommended: (3) as the scale metric, (4) as the calibration set, (2) as a
free additional signal.** Report them as three separate numbers. Never blend a
derived key into the same column as the assignment's official FY2022 key —
`compute_metrics` already scores only the rows a key defines, and `has_golden` /
`total_compared` already carry the distinction through to the UI.

### Measured cost of running it

From the real 12-run experiment (710s wall clock at concurrency 3, mean 123,356
input tokens per run):

| Scope | Runs | @ concurrency 3 | @ concurrency 6 | Input tokens |
|---|---:|---:|---:|---:|
| 20 companies × 3 years × 2 strategies | 120 | 2.0 h | 1.0 h | ~15 M |
| 100 companies × 3 years × 2 strategies | 600 | 9.9 h | 4.9 h | ~74 M |
| 100 companies × 5 years × 4 strategies | 2,000 | 32.9 h | 16.4 h | ~247 M |

**Start with the 20-company slice.** It is a 2-hour run that will expose every
pipeline problem the 100-company run would, at a seventh of the cost. Only scale
to 100 once the 20 comes back clean.

The adaptive limiter in `ratelimit.py` already handles throttling (halve on 429,
back off, recover), and the 12-run experiment recorded zero throttle events at
concurrency 3. Concurrency 6 previously did hit 429s, so treat 3 as the safe
default and let the limiter find the ceiling.

### Acceptance criteria

- `corpus_manifest.json` validates: every entry has a fiscal year confirmed
  *from inside the PDF*, a sha256, and a screening verdict.
- No duplicate `(company, fiscal_year)` pairs; no duplicate sha256.
- Screening rate reported explicitly — how many documents were rejected and why.
  The unreadable-PDF rate across ~100 filers is itself a result worth publishing.
- Accuracy reported as three separate columns (anchor-row, self-consistency,
  hand-labelled sample), never merged.
- The 6-document 3M set stays in `test_dataset/` untouched as the regression
  set, so every future change is still comparable to every number in the README.

### Explicit non-goals

- Do not put Firecrawl on the extraction path. The benchmark must stay runnable
  offline from local PDFs.
- Do not auto-refresh the corpus mid-experiment. A corpus is pinned by manifest
  and sha256 for the life of a result.
- Do not let discovery invent an answer key.
