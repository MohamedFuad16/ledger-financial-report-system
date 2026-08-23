"""Screen downloaded PDFs before they enter a paid benchmark."""

from __future__ import annotations

import re
import unicodedata
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

ANNUAL_DOCUMENT = re.compile(
    r"annual\s+report|form\s+10[- ]?k|有価証券報告書|年次報告書|統合報告書",
    re.I,
)

NON_ANNUAL_DOCUMENT = re.compile(
    r"定時株主総会招集ご通知|臨時株主総会|proxy\s+statement|"
    r"quarter(?:ly)?\s+report|interim\s+report|四半期報告書|半期報告書|決算短信",
    re.I,
)


def _normalized_identity(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", str(value or "")).casefold()
        if character.isalnum()
    )


def _company_identity_variants(company: str) -> set[str]:
    """Return exact legal-name variants that may appear on a filing cover."""
    raw = unicodedata.normalize("NFKC", str(company or "")).strip()
    variants = {raw}
    variants.add(re.split(r"[（(]", raw, maxsplit=1)[0])
    variants.update(part for part in re.split(r"[／/・]", raw) if part)
    return {
        normalized
        for variant in variants
        if len(normalized := _normalized_identity(variant)) >= 3
    }


def _company_identity_confirmed(text: str, expected_company: str) -> bool:
    normalized_text = _normalized_identity(text)
    return any(
        identity in normalized_text
        for identity in _company_identity_variants(expected_company)
    )


# Japanese statutory filings identify their own type on the cover with the
# 【提出書類】 label. Whitespace is stripped before matching, so spaced-out
# display titles (e.g. 四 半 期 報 告 書) cannot evade the check.
COVER_DOCUMENT_TYPE = re.compile(r"【提出書類】([^【]{1,60})")


def _is_annual_document(text: str) -> bool:
    compact = re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))
    # Trust the filing's own cover label over incidental cross-references: a
    # genuine annual securities report routinely mentions its quarterly
    # reports (縦覧場所, audit history), which must not reject it.
    cover = COVER_DOCUMENT_TYPE.search(compact)
    if cover:
        stated_type = cover.group(1)
        if NON_ANNUAL_DOCUMENT.search(stated_type):
            return False
        if ANNUAL_DOCUMENT.search(stated_type):
            return True
    head = compact[:4000]
    if NON_ANNUAL_DOCUMENT.search(head):
        return False
    if ANNUAL_DOCUMENT.search(head):
        return True
    if NON_ANNUAL_DOCUMENT.search(text) or NON_ANNUAL_DOCUMENT.search(compact):
        return False
    return ANNUAL_DOCUMENT.search(text) is not None or ANNUAL_DOCUMENT.search(compact) is not None


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


def screen_pdf(
    path: Path,
    expected_year: int,
    *,
    expected_company: str = "",
    require_annual_document: bool = False,
) -> dict[str, Any]:
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
    company_identity_confirmed = (
        _company_identity_confirmed(extracted.text, expected_company)
        if expected_company
        else None
    )
    annual_document_confirmed = (
        _is_annual_document(extracted.text)
        if require_annual_document
        else None
    )

    reasons: list[str] = []
    if not year_confirmed:
        reasons.append(f"Fiscal year {expected_year} was not confirmed inside the PDF.")
    if extracted.readable_pages == 0:
        reasons.append("No readable text layer.")
    if balance_page is None:
        reasons.append("No balance sheet heading found.")
    if company_identity_confirmed is False:
        reasons.append(f"The PDF does not identify the requested company: {expected_company}.")
    if annual_document_confirmed is False:
        reasons.append("The PDF is not an annual or securities report.")

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
        "company_identity_confirmed": company_identity_confirmed,
        "annual_document_confirmed": annual_document_confirmed,
        "reporting_year": reporting_year,
        "statement_years": statement_years,
        "internal_year_mentions": sorted(set(mentions)),
        "warnings": extracted.warnings,
    }
