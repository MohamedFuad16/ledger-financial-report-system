"""Deterministic complete-page selection for Strategy 3.

The selector is deliberately not a vector index or a generative agent.  It
scores the complete, page-bounded Markdown produced by pdf-inspector against
the fixed 27-row schema and parser-supplied layout metadata, then keeps only a
small evidence packet for the semantic-mapping model.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Iterable

from schema import ASSET_SCHEMA


TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9&-]{1,}|\d+(?:[.,]\d+)*", re.I)

# Accounting language varies substantially across US and international annual
# reports.  These are navigation terms, never answer aliases or golden values.
ACCOUNTING_SYNONYMS = (
    "balance sheet", "statement of financial position", "financial statements",
    "current assets", "total assets", "cash and cash equivalents",
    "accounts receivable", "trade receivables", "inventories", "marketable securities",
    "prepaid expenses", "other current assets", "property plant and equipment",
    "property, plant and equipment", "pp&e", "land", "buildings", "machinery",
    "construction in progress", "equipment", "accumulated depreciation",
    "goodwill", "intangible assets", "investments", "financial assets",
    "other assets", "notes to consolidated financial statements",
)

FINANCIAL_HEADING_PATTERNS = tuple(re.compile(pattern, re.I | re.M) for pattern in (
    r"^#{1,4}\s+.*(?:balance sheets?|financial position)",
    r"^#{1,4}\s+.*(?:property,? plant|equipment|intangible|goodwill|inventor|receiv)",
    r"(?:consolidated\s+)?balance sheets?",
    r"statements? of financial position",
    r"notes? to (?:the )?(?:consolidated )?financial statements",
))

REJECT_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (
    r"proxy statement",
    r"board of directors",
    r"executive compensation",
    r"shareholder proposal",
    r"corporate governance",
    r"table of contents",
))


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text or "")]


def _query_terms() -> set[str]:
    schema_text = " ".join(
        str(row.get(key) or "")
        for row in ASSET_SCHEMA
        for key in ("classification", "subclassification", "item", "description")
    )
    return set(_tokens(schema_text + " " + " ".join(ACCOUNTING_SYNONYMS)))


QUERY_TERMS = _query_terms()


def _page_number_set(values: Iterable[Any] | None) -> set[int]:
    """Normalize pdf-inspector aggregate layout lists, which are 1-indexed."""
    output: set[int] = set()
    for value in values or []:
        if isinstance(value, bool):
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number >= 1:
            output.add(number)
    return output


def score_pages(
    pages: list[tuple[int, str]],
    *,
    pages_with_tables: Iterable[Any] | None = None,
    pages_with_columns: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    """Return an explainable BM25-style score for each complete Markdown page."""
    usable = [(int(page), text or "") for page, text in pages if str(text or "").strip()]
    if not usable:
        return []

    tokenized = {page: _tokens(text) for page, text in usable}
    counts = {page: Counter(tokens) for page, tokens in tokenized.items()}
    document_frequency = Counter(
        term for tokens in tokenized.values() for term in (set(tokens) & QUERY_TERMS)
    )
    page_total = len(usable)
    average_length = sum(len(tokens) for tokens in tokenized.values()) / page_total or 1.0
    table_pages = _page_number_set(pages_with_tables)
    column_pages = _page_number_set(pages_with_columns)
    k1, b = 1.5, 0.75
    results: list[dict[str, Any]] = []

    for page_no, text in usable:
        page_counts = counts[page_no]
        length = max(1, len(tokenized[page_no]))
        bm25 = 0.0
        matched_terms: list[str] = []
        for term in QUERY_TERMS:
            frequency = page_counts.get(term, 0)
            if not frequency:
                continue
            matched_terms.append(term)
            df = document_frequency[term]
            inverse_document_frequency = math.log(1 + (page_total - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * length / average_length)
            bm25 += inverse_document_frequency * (frequency * (k1 + 1) / denominator)

        heading_hits = sum(bool(pattern.search(text)) for pattern in FINANCIAL_HEADING_PATTERNS)
        has_markdown_table = bool(re.search(r"^\s*\|.+\|\s*$", text, re.M))
        table_signal = page_no in table_pages or has_markdown_table
        column_signal = page_no in column_pages
        numeric_tokens = sum(bool(re.search(r"\d", token)) for token in tokenized[page_no])
        numeric_density = numeric_tokens / length
        reject_hits = sum(bool(pattern.search(text)) for pattern in REJECT_PATTERNS)
        # The lexical score does the ranking work; the remaining bounded terms
        # incorporate PDF layout facts and strong financial-navigation cues.
        score = (
            bm25
            + min(10.0, len(matched_terms) * 0.28)
            + heading_hits * 4.0
            + (4.0 if table_signal else 0.0)
            + (0.75 if column_signal else 0.0)
            + min(2.0, numeric_density * 8.0)
            - reject_hits * (3.0 if not heading_hits else 1.0)
        )
        results.append({
            "page": page_no,
            "score": round(score, 4),
            "bm25": round(bm25, 4),
            "schema_term_hits": len(matched_terms),
            "matched_terms": sorted(matched_terms)[:24],
            "financial_heading_hits": heading_hits,
            "table_signal": table_signal,
            "column_signal": column_signal,
            "numeric_density": round(numeric_density, 4),
            "reject_hits": reject_hits,
            "characters": len(text),
        })
    return sorted(results, key=lambda item: (-float(item["score"]), int(item["page"])))


def select_evidence_pages(
    pages: list[tuple[int, str]],
    *,
    pages_with_tables: Iterable[Any] | None = None,
    pages_with_columns: Iterable[Any] | None = None,
    minimum_pages: int = 3,
    maximum_pages: int = 5,
) -> tuple[list[tuple[int, str]], dict[str, Any]]:
    """Select three to five whole pages and return full scoring diagnostics."""
    ranked = score_pages(
        pages,
        pages_with_tables=pages_with_tables,
        pages_with_columns=pages_with_columns,
    )
    if not ranked:
        return [], {"selected_pages": [], "ranked_pages": [], "fallback": "no_readable_pages"}

    upper = min(maximum_pages, len(ranked))
    lower = min(minimum_pages, upper)
    selected_count = lower
    # Pages four and five are retained when they still carry a meaningful
    # fraction of the third page's signal.  This keeps packets compact without
    # making every annual report an unconditional five-page prompt.
    reference_score = max(1.0, float(ranked[lower - 1]["score"]))
    while selected_count < upper and float(ranked[selected_count]["score"]) >= reference_score * 0.45:
        selected_count += 1

    selected_ranked = ranked[:selected_count]
    selected_numbers = {int(item["page"]) for item in selected_ranked}
    selected = [(page, text) for page, text in pages if page in selected_numbers and str(text).strip()]
    selected.sort(key=lambda item: item[0])
    total_chars = sum(len(text) for _, text in pages)
    selected_chars = sum(len(text) for _, text in selected)
    diagnostics = {
        "selector": "intelligent_scanning_gate_v1",
        "selection_method": "BM25-style schema terms + financial headings + pdf-inspector layout metadata",
        "selected_pages": [page for page, _ in selected],
        "selected_page_count": len(selected),
        "candidate_page_count": len(ranked),
        "ranked_pages": selected_ranked,
        "all_page_scores": ranked,
        "full_markdown_characters": total_chars,
        "selected_markdown_characters": selected_chars,
        "character_reduction_percent": round((1 - selected_chars / total_chars) * 100, 2) if total_chars else 0.0,
        "fallback": None,
    }
    return selected, diagnostics
