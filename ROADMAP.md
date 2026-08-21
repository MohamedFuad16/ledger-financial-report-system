# Ledger roadmap

## Active baseline

- Strategy 1: the four-parser OCR-enabled comparison.
- Strategy 2: the same four parsers with OCR disabled.
- Both convert one Annual Report to a page-marked representation, make one configured-model semantic-mapping call, validate the fixed 27-row result, and use the same verification and scoring contract.

## Strategy 3: finalized intelligent scanning gate

Strategy 3 is implemented. It does not use RAG, embeddings, arbitrary chunks or an agentic loop.

### Locked pipeline

1. pdf-inspector classifies the document and extracts complete per-page Markdown.
2. Ledger reads the parser's document type, confidence, encoding flag, OCR-needed pages, OCR reasons, table pages, column pages and complexity metadata.
3. Only pages routed by pdf-inspector are rendered at exactly 200 DPI and sent to GLM-OCR.
4. Each OCR result replaces that page's empty or unreliable native Markdown at the same original page number; native and OCR pages become one unified Markdown sequence.
5. `intelligent_scan.py` scores every complete page using BM25-style terms derived from the fixed 27-field schema and accounting synonyms, financial-heading matches, table presence, column/layout signals, numeric density and bounded boilerplate penalties.
6. The top three to five complete pages are restored to source order and passed to the configured LLM for semantic mapping.
7. The existing JSON parser, recorded normalization, exact 27-row Pydantic contract, confidence gate, deterministic reconciliation and human-verification flow run unchanged.

PDF-Inspector owns extraction and OCR routing. The intelligent scanning gate owns page relevance. The LLM owns semantic mapping only.

The integration contract was validated against pdf-inspector's official [Python API guide](https://github.com/firecrawl/pdf-inspector/blob/main/docs/python.md), [type stubs](https://github.com/firecrawl/pdf-inspector/blob/main/pdf_inspector.pyi), and the installed 1.15.0 package. Per-page `PageMarkdown.page` values are normalized from 0-based indexes, while aggregate OCR/table/column lists are treated as documented 1-based PDF page numbers.

### Evaluation contract

Strategy 3 must be evaluated against the whole-document control on the same reports and model settings. Record:

- evidence-page recall;
- selected-page ratio;
- input tokens and cost;
- extraction latency;
- 27-field coverage;
- exact accuracy on human-verified reports;
- PDF classification, OCR-routed pages/reasons and per-page provenance;
- all page scores and selected score components.

The gate currently enforces the finalized three-to-five-page packet. Benchmark acceptance is still strict: token savings are useful only if evidence-page recall, field coverage and exact accuracy remain acceptable on held-out company-years. OCR cost must be reported separately because a broken text layer can cause many pages to be OCR-routed before the gate reduces LLM input.
