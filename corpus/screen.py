"""Screen downloaded PDFs before they enter a paid benchmark."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from extraction import extract_with_pypdf


PAGE_MARKER = re.compile(r"^--- PAGE (\d+) ---$", re.M)
BALANCE_SHEET = re.compile(r"(?:consolidated\s+)?balance\s+sheets?|statement\s+of\s+financial\s+position", re.I)
YEAR_PATTERNS = (
    re.compile(r"(?:at|as\s+of)\s+(?:december|january|september|june|march)[^\n]{0,45}\b((?:19|20)\d{2})\b", re.I),
    re.compile(r"for\s+the\s+year\s+ended[^\n]{0,45}\b((?:19|20)\d{2})\b", re.I),
    re.compile(r"fiscal\s+year\s+((?:19|20)\d{2})", re.I),
)


def _year_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for pattern in YEAR_PATTERNS:
        mentions.extend(pattern.findall(text))
    return mentions


def _balance_sheet_page(text: str) -> int | None:
    markers = list(PAGE_MARKER.finditer(text))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        page = text[marker.end():end]
        financial_terms = sum(
            bool(re.search(term, page, re.I))
            for term in (r"current\s+assets", r"cash\s+and\s+cash", r"inventor", r"total\s+assets", r"liabilit")
        )
        if BALANCE_SHEET.search(page) and financial_terms >= 3:
            return int(marker.group(1))
    return None


def screen_pdf(path: Path, expected_year: int) -> dict[str, Any]:
    extracted = extract_with_pypdf(path)
    mentions = _year_mentions(extracted.text)
    year_confirmed = str(expected_year) in mentions
    balance_page = _balance_sheet_page(extracted.text)
    currency = "USD" if re.search(r"(?:U\.S\.\s*)?dollars|\$\s*in\s+millions|millions\s+of\s+dollars", extracted.text, re.I) else "unknown"

    reasons: list[str] = []
    if not year_confirmed:
        reasons.append(f"Fiscal year {expected_year} was not confirmed inside the PDF.")
    if extracted.readable_pages == 0:
        reasons.append("No readable text layer.")
    if balance_page is None:
        reasons.append("No consolidated balance sheet heading found.")

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
        "internal_year_mentions": sorted(set(mentions)),
        "warnings": extracted.warnings,
    }
