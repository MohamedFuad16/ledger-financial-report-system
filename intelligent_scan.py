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
from collections.abc import Iterable
from typing import Any

from schema import ASSET_SCHEMA

TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9&-]{1,}|\d+(?:[.,]\d+)*", re.I)

# Accounting language varies substantially across US and international annual
# reports.  These are navigation terms, never answer aliases or golden values.
ACCOUNTING_SYNONYMS = (
    "balance sheet",
    "statement of financial position",
    "financial statements",
    "current assets",
    "total assets",
    "cash and cash equivalents",
    "accounts receivable",
    "trade receivables",
    "inventories",
    "marketable securities",
    "prepaid expenses",
    "other current assets",
    "property plant and equipment",
    "property, plant and equipment",
    "pp&e",
    "land",
    "buildings",
    "machinery",
    "construction in progress",
    "equipment",
    "accumulated depreciation",
    "goodwill",
    "intangible assets",
    "investments",
    "financial assets",
    "other assets",
    "operating lease",
    "right of use assets",
    "right-of-use assets",
    "rou assets",
    "notes to consolidated financial statements",
)

# EDINET filings use Japanese statement labels. These fixed navigation terms
# are schema concepts, not company/year/page-specific answers. Japanese text
# is scored by substring because whitespace tokenization is not reliable.
JAPANESE_ACCOUNTING_TERMS = (
    "貸借対照表",
    "財務諸表",
    "資産の部",
    "流動資産",
    "固定資産",
    "資産合計",
    "現金及び預金",
    "売掛金",
    "受取手形",
    "棚卸資産",
    "商品及び製品",
    "原材料及び貯蔵品",
    "有形固定資産",
    "建物及び構築物",
    "機械装置",
    "土地",
    "建設仮勘定",
    "減価償却累計額",
    "無形固定資産",
    "のれん",
    "投資その他の資産",
    "投資有価証券",
    "敷金及び保証金",
    "繰延税金資産",
)

FINANCIAL_HEADING_PATTERNS = tuple(
    re.compile(pattern, re.I | re.M)
    for pattern in (
        r"^#{1,4}\s+.*(?:balance sheets?|financial position)",
        r"^#{1,4}\s+.*(?:property,? plant|equipment|intangible|goodwill|inventor|receiv)",
        r"(?:consolidated\s+)?balance sheets?",
        r"statements? of financial position",
        r"notes? to (?:the )?(?:consolidated )?financial statements",
        r"(?:連結)?貸借対照表",
        r"(?:連結)?財務諸表",
        r"資産の部",
    )
)

REJECT_PATTERNS = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"proxy statement",
        r"board of directors",
        r"executive compensation",
        r"shareholder proposal",
        r"corporate governance",
        r"table of contents",
        r"取締役|役員の状況|コーポレート.?ガバナンス|株主総会|目次",
    )
)

# Evidence that is easy to lose when issuers move a schema component off the
# face statement. This is a source-language concept, not an answer or company-
# specific page number. A bounded bonus keeps a lease note competitive with
# dense generic financial pages when Other Equipment may include ROU assets.
CRITICAL_EVIDENCE_PATTERNS = (
    (
        "right_of_use_assets",
        re.compile(r"(?:operating\s+lease\s+)?right[-\s]+of[-\s]+use\s+assets?", re.I),
    ),
    ("japanese_investment_breakdown", re.compile(r"市場価格のない株式等")),
    ("japanese_accumulated_depreciation", re.compile(r"減価償却累計額")),
    ("japanese_loan_maturity", re.compile(r"金銭債権の連結決算日後の償還予定額")),
)


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
    has_consolidated_balance_sheet = any("連結貸借対照表" in text for _, text in usable)
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
        standalone_statement = bool(
            has_consolidated_balance_sheet and "貸借対照表" in text and "連結貸借対照表" not in text
        )
        critical_evidence = [name for name, pattern in CRITICAL_EVIDENCE_PATTERNS if pattern.search(text)]
        japanese_term_hits = [term for term in JAPANESE_ACCOUNTING_TERMS if term in text]
        # The lexical score does the ranking work; the remaining bounded terms
        # incorporate PDF layout facts and strong financial-navigation cues.
        score = (
            bm25
            + min(10.0, len(matched_terms) * 0.28)
            + heading_hits * 4.0
            + (4.0 if table_signal else 0.0)
            + (0.75 if column_signal else 0.0)
            + min(2.0, numeric_density * 8.0)
            + min(16.0, len(critical_evidence) * 16.0)
            + min(18.0, len(japanese_term_hits) * 0.9)
            - reject_hits * (3.0 if not heading_hits else 1.0)
            - (12.0 if standalone_statement else 0.0)
        )
        results.append(
            {
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
                "standalone_statement_penalty": standalone_statement,
                "critical_evidence": critical_evidence,
                "japanese_accounting_hits": japanese_term_hits[:24],
                "characters": len(text),
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), int(item["page"])))


# Japanese navigation vocabulary per schema row, used only to rank retry pages.
# These are fixed accounting concepts (like JAPANESE_ACCOUNTING_TERMS above),
# never company-, year- or answer-specific values.
JAPANESE_ITEM_TERMS: dict[str, tuple[str, ...]] = {
    "Cash & Cash Equivalents": ("現金及び預金", "現金預金"),
    "Accounts Receivable - Trade": (
        "売掛金",
        "受取手形",
        "電子記録債権",
        "契約資産",
        "完成工事未収入金",
    ),
    "Other Quick Assets": ("未収入金", "未収収益"),
    "Inventories, Net": (
        "棚卸資産",
        "商品及び製品",
        "仕掛品",
        "原材料及び貯蔵品",
        "未成工事支出金",
    ),
    "Marketable Securities": ("有価証券",),
    "Short-term Loan": ("短期貸付金", "貸付金", "償還予定"),
    "Advance Payments": ("前渡金", "前払金"),
    "Other Current Assets": ("前払費用",),
    "Tangible Assets": ("有形固定資産", "有形固定資産等明細表"),
    "Land": ("土地",),
    "Buildings": ("建物", "構築物", "有形固定資産等明細表", "取得価額"),
    "Plant & Machinery": (
        "機械及び装置",
        "機械装置",
        "有形固定資産等明細表",
        "取得価額",
    ),
    "Construction in Progress": ("建設仮勘定",),
    "Other Equipment": (
        "工具、器具及び備品",
        "車両運搬具",
        "リース資産",
        "使用権資産",
        "有形固定資産等明細表",
    ),
    "Accumulated Depreciation": ("減価償却累計額", "有形固定資産等明細表", "取得価額"),
    "Intangible Assets": ("無形固定資産", "のれん", "ソフトウエア"),
    "Financial Assets": (
        "投資その他の資産",
        "敷金及び保証金",
        "前払年金費用",
        "退職給付に係る資産",
    ),
    "Investments": ("投資有価証券", "関係会社株式", "出資金"),
    "Long-term Loan": ("長期貸付金", "貸付金", "償還予定"),
    "Other Financial Assets": (
        "敷金及び保証金",
        "破産更生債権",
        "保険積立金",
        "貸倒引当金",
    ),
    "Other Fixed Assets": ("長期前払費用", "繰延税金資産"),
    "Deferred Charges": ("繰延資産", "株式交付費", "社債発行費", "開発費"),
}


def select_retry_pages(
    pages: list[tuple[int, str]],
    *,
    missing_items: list[str],
    exclude_pages: Iterable[int],
    maximum_pages: int = 3,
    pages_with_tables: Iterable[Any] | None = None,
    pages_with_columns: Iterable[Any] | None = None,
) -> tuple[list[tuple[int, str]], dict[str, Any]]:
    """Pick the next-best unsent pages for one bounded evidence-retry pass.

    Ranking combines the gate's global score with a bonus for schema terms of
    the specific rows that came back null. The inputs are the public schema and
    parser output only — no golden values participate.
    """
    excluded = {int(page) for page in exclude_pages}
    remaining = [(page, text) for page, text in pages if int(page) not in excluded]
    if not remaining or maximum_pages < 1:
        return [], {"retry_pages": [], "reason": "no_remaining_pages"}

    missing_terms: set[str] = set()
    wanted = {str(item) for item in missing_items}
    japanese_targets: set[str] = set()
    for row in ASSET_SCHEMA:
        if str(row.get("item")) not in wanted:
            continue
        for key in ("classification", "subclassification", "item", "description"):
            missing_terms.update(_tokens(str(row.get(key) or "")))
    for item in wanted:
        japanese_targets.update(JAPANESE_ITEM_TERMS.get(item, ()))

    ranked = score_pages(
        remaining,
        pages_with_tables=pages_with_tables,
        pages_with_columns=pages_with_columns,
    )
    rescored = []
    text_by_page = {int(page): text for page, text in remaining}
    for entry in ranked:
        page_no = int(entry["page"])
        page_text = text_by_page.get(page_no, "")
        page_tokens = set(_tokens(page_text))
        targeted_hits = len(page_tokens & missing_terms)
        # Japanese note pages never match English schema tokens, so the label
        # vocabulary of the specific missing rows must dominate the ranking —
        # otherwise generically dense financial pages always win.
        japanese_hits = sum(1 for term in japanese_targets if term in page_text)
        rescored.append(
            {
                **entry,
                "targeted_term_hits": targeted_hits,
                "targeted_japanese_hits": japanese_hits,
                "retry_score": round(
                    float(entry["score"]) + min(8.0, targeted_hits * 0.6) + min(36.0, japanese_hits * 12.0),
                    4,
                ),
            }
        )
    rescored.sort(key=lambda item: (-float(item["retry_score"]), int(item["page"])))
    chosen = rescored[:maximum_pages]
    chosen_numbers = {int(item["page"]) for item in chosen}
    selected = sorted(
        ((page, text) for page, text in remaining if int(page) in chosen_numbers),
        key=lambda item: item[0],
    )
    return selected, {
        "retry_pages": [int(item["page"]) for item in chosen],
        "retry_scores": [
            {
                key: item[key]
                for key in (
                    "page",
                    "score",
                    "retry_score",
                    "targeted_term_hits",
                    "targeted_japanese_hits",
                )
            }
            for item in chosen
        ],
        "reason": None,
    }


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
        return [], {
            "selected_pages": [],
            "ranked_pages": [],
            "fallback": "no_readable_pages",
        }

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
        "selector": "intelligent_scanning_gate_v2",
        "selection_method": "BM25-style schema terms + critical schema evidence + financial headings + pdf-inspector layout metadata",
        "selected_pages": [page for page, _ in selected],
        "selected_page_count": len(selected),
        "candidate_page_count": len(ranked),
        "ranked_pages": selected_ranked,
        "all_page_scores": ranked,
        "full_markdown_characters": total_chars,
        "selected_markdown_characters": selected_chars,
        "character_reduction_percent": round((1 - selected_chars / total_chars) * 100, 2)
        if total_chars
        else 0.0,
        "fallback": None,
    }
    return selected, diagnostics
