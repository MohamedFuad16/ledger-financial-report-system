# Ledger roadmap

## Active baseline

- Strategy 1: the four-parser OCR-enabled comparison.
- Strategy 2: the same four parsers with OCR disabled.
- Both convert one Annual Report to a page-marked representation, make one configured-model semantic-mapping call, validate the fixed 27-row result, and use the same verification and scoring contract.

## Strategy 3: schema-guided page filtering

Strategy 3 is a planned input-reduction experiment. It will not send the entire parser-produced Markdown document to the model. A deterministic selector will operate on existing PDF page markers, score complete pages against the 27-field schema, and create a smaller evidence packet for the same semantic-mapping call.

This is technically page retrieval and page-level segmentation. It is not vector RAG: there is no embedding index, vector database, arbitrary token chunking, recursive retrieval, or agentic loop.

### Selector design

1. Build positive patterns from all 27 field names, accounting synonyms, statement headings, note headings, units, and year cues.
2. Score every complete Markdown page with BM25-style lexical signals plus deterministic boosts for balance-sheet structure and schema coverage.
3. Apply explicit reject patterns to boilerplate such as covers, legal notices, proxy material, governance biographies, and repeated navigation only when low relevance agrees.
4. Always retain the detected balance-sheet page, its neighboring pages, relevant asset-note pages, and page provenance.
5. Preserve original page order and send the retained packet through the existing prompt, model, validation, confidence, reconciliation, and human-review flow.
6. Fall back to the complete document whenever selector confidence or predicted schema coverage is below threshold.

### Evaluation contract

Strategy 3 must be evaluated against the whole-document control on the same reports and model settings. Record:

- evidence-page recall;
- selected-page ratio;
- input tokens and cost;
- extraction latency;
- 27-field coverage;
- exact accuracy on human-verified reports;
- fallbacks and rejected-page reasons.

The go/no-go rule is strict: token savings are useful only if evidence-page recall is effectively complete and field coverage and exact accuracy do not regress. Patterns must be learned from a development set and checked on held-out company-years to avoid a selector that only memorizes 3M report layouts.
