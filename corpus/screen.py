"""Screen downloaded PDFs before they enter a paid benchmark."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from extraction import extract_with_pypdf


PAGE_MARKER = re.compile(r"^--- PAGE (\d+) ---$", re.M)
BALANCE_SHEET = re.compile(
    r"(?:consolidated\s+)?balance\s+sheets?"
    r"|statement\s+of\s+financial\s+position"
    r"|貸借対照表"
    r"|財政状態計算書",
    re.I,
)
YEAR_PATTERNS = (
    re.compile(r"(?:at|as\s+of)\s+(?:december|january|september|june|march)[^\n]{0,45}\b((?:19|20)\d{2})\b", re.I),
    re.compile(r"for\s+the\s+year\s+ended[^\n]{0,45}\b((?:19|20)\d{2})\b", re.I),
    re.compile(r"fiscal\s+year\s+((?:19|20)\d{2})", re.I),
    # Japanese securities reports identify the filing period on their cover as
    # 【事業年度】... (自 2024年... 至 2024年...). Keep the match close to
    # the label so unrelated comparative years do not satisfy the screen.
    re.compile(r"事業年度[^\n]{0,100}?((?:19|20)\d{2})年"),
    re.compile(r"((?:19|20)\d{2})年\s*\d{1,2}月期"),
)

FINANCIAL_TERM_GROUPS = (
    (r"current\s+assets", r"流動資産"),
    (r"cash\s+and\s+cash", r"現金(?:及び)?(?:預金|現金同等物)|現金預金"),
    (r"inventor", r"(?:棚卸|たな卸)資産|未成工事支出金|材料貯蔵品"),
    (r"total\s+assets", r"資産(?:合計|の部合計)"),
    (r"liabilit", r"負債(?:合計|の部)"),
)


def _year_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for pattern in YEAR_PATTERNS:
        mentions.extend(pattern.findall(text))
    return mentions


def _balance_sheet_page(text: str) -> int | None:
    markers = list(PAGE_MARKER.finditer(text))
    candidates: list[tuple[float, int]] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        page = text[marker.end():end]
        financial_terms = sum(
            any(re.search(term, page, re.I) for term in alternatives)
            for alternatives in FINANCIAL_TERM_GROUPS
        )
        if not BALANCE_SHEET.search(page) or financial_terms < 3:
            continue
        # Management discussion often contains a prose heading named
        # "Balance Sheet" before the audited statement. Rank all candidates
        # and prefer the page that actually carries the asset-side statement.
        # These are document-shape signals only; they contain no answer values.
        score = float(financial_terms)
        score += 8.0 if re.search(r"consolidated\s+balance\s+sheets?", page, re.I) else 0.0
        score += 3.0 if re.search(r"\bassets\s*\n\s*current\s+assets\b", page, re.I) else 0.0
        score += 3.0 if re.search(r"\btotal\s+assets\b", page, re.I) else 0.0
        score += 1.5 if re.search(r"\b(?:goodwill|intangible\s+assets)\b", page, re.I) else 0.0
        score += 1.5 if re.search(r"\baccumulated\s+depreciation\b", page, re.I) else 0.0
        score += min(3.0, len(re.findall(r"(?m)^.*\d[\d,().$ -]*$", page)) / 8.0)
        candidates.append((score, int(marker.group(1))))
    return max(candidates, default=(0.0, None), key=lambda item: (item[0], -item[1]))[1]


def _page_text(text: str, page_number: int | None) -> str:
    if page_number is None:
        return text
    marker = re.search(rf"^--- PAGE {int(page_number)} ---$", text, re.M)
    if not marker:
        return text
    following = PAGE_MARKER.search(text, marker.end())
    return text[marker.end():following.start() if following else len(text)]


def _statement_years(text: str, balance_page: int | None) -> list[int]:
    """Return calendar years printed on the selected balance-sheet page."""
    statement = _page_text(text, balance_page)
    return sorted({
        int(year)
        for year in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", statement)
    })


def _statement_currency(text: str, balance_page: int | None) -> str:
    """Detect the currency of the audited statement, not any translated note."""
    statement = _page_text(text, balance_page)
    if re.search(r"yen\s+in\s+(?:thousands|millions)|Japanese\s+yen|(?:単位\s*[:：]?\s*)?(?:千円|百万円)|日本円", statement, re.I):
        return "JPY"
    if re.search(r"(?:U\.S\.\s*)?dollars|\$\s*in\s+millions|millions\s+of\s+dollars", statement, re.I):
        return "USD"
    return "unknown"


def screen_pdf(path: Path, expected_year: int) -> dict[str, Any]:
    extracted = extract_with_pypdf(path)
    mentions = _year_mentions(extracted.text)
    balance_page = _balance_sheet_page(extracted.text)
    statement_years = _statement_years(extracted.text, balance_page)
    reporting_year = max(statement_years, default=None)
    year_confirmed = (
        reporting_year == expected_year
        if reporting_year is not None
        else str(expected_year) in mentions
    )
    currency = _statement_currency(extracted.text, balance_page)

    reasons: list[str] = []
    if not year_confirmed:
        reasons.append(f"Fiscal year {expected_year} was not confirmed inside the PDF.")
    if extracted.readable_pages == 0:
        reasons.append("No readable text layer.")
    if balance_page is None:
        reasons.append("No balance sheet heading found.")

    verdict = "ok" if not reasons else "review"
    if extracted.readable_pages == 0:
        verdict = "unreadable"
    return {
        "screened": verdict,
        "screen_reasons": reasons,
        "pages": extracted.page_count,
        "readable_pages": extracted.readable_pages,
        "garbled_pages": extracted.garbled_pages,
        "balance_sheet_page": balance_page,
        "currency": currency,
        "fiscal_year_confirmed": year_confirmed,
        "reporting_year": reporting_year,
        "statement_years": statement_years,
        "internal_year_mentions": sorted(set(mentions)),
        "warnings": extracted.warnings,
    }
