"""Discover Annual Report PDF URLs, preferring supplied official IR sites."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import urlparse
import unicodedata

from .client import FirecrawlClient


REPORT_WORDS = re.compile(
    r"annual[-_\s]?report|form[-_\s]?10[-_\s]?k|10-k|"
    r"有価証券報告書|有報|統合報告書|年次報告書",
    re.I,
)

# EDINET is the Japanese Financial Services Agency's filing system.  Search
# results on this host may be accepted without an issuer-domain URL, but only
# when the result itself names the exact requested legal entity.  Generic CDN
# and parent-company results remain untrusted.
PUBLIC_FILING_DOMAINS = {
    "disclosure.edinet-fsa.go.jp",
    "disclosure2.edinet-fsa.go.jp",
    "disclosure2dl.edinet-fsa.go.jp",
}


@dataclass(frozen=True)
class ReportCandidate:
    company: str
    year: int
    url: str
    title: str = ""
    description: str = ""
    discovery: str = "search"
    official_domain: str = ""
    source_verified: bool = False
    score: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _looks_like_report(item: dict, year: int) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("url", "title", "description"))
    # A PDF extension plus a year is not sufficient: investor sites contain
    # thousands of year-stamped releases and presentations. Require explicit
    # annual-report/filing language before a candidate can reach download.
    return str(year) in text and REPORT_WORDS.search(text) is not None


def _score(item: dict, year: int, official_domain: str) -> int:
    url = str(item.get("url") or "")
    text = " ".join(str(item.get(key) or "") for key in ("url", "title", "description"))
    score = 0
    score += 7 if _domain(url) == official_domain or _domain(url).endswith(f".{official_domain}") else 0
    score += 5 if urlparse(url).path.lower().endswith(".pdf") else 0
    score += 4 if str(year) in text else 0
    score += 3 if REPORT_WORDS.search(text) else 0
    score -= 4 if re.search(r"proxy|sustainability|esg|quarter|presentation", text, re.I) else 0
    return score


def _matches_domain(url: str, official_domain: str) -> bool:
    """Return true only for the supplied official host or one of its subdomains."""
    if not official_domain:
        return False
    candidate_domain = _domain(url)
    return candidate_domain == official_domain or candidate_domain.endswith(f".{official_domain}")


def _normalized_identity(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKC", value).casefold()
        if character.isalnum()
    )


def _trusted_public_filing(item: dict, company: str) -> bool:
    domain = _domain(str(item.get("url") or ""))
    if domain not in PUBLIC_FILING_DOMAINS:
        return False
    identity = _normalized_identity(company)
    result_text = _normalized_identity(
        " ".join(str(item.get(key) or "") for key in ("title", "description"))
    )
    return bool(identity and identity in result_text)


def discover_company_reports(
    client: FirecrawlClient,
    *,
    company: str,
    years: Iterable[int],
    official_url: str = "",
    country: str = "US",
    deep_search: bool = False,
) -> dict[int, list[ReportCandidate]]:
    years = sorted({int(year) for year in years})
    official_domain = _domain(official_url)
    pool: list[tuple[dict, str]] = []

    is_japanese = country.strip().upper() == "JP"
    map_search = "有価証券報告書 統合報告書 annual report" if is_japanese else "annual report 10-k"

    if official_url:
        try:
            pool.extend((item, "map") for item in client.map(official_url, search=map_search))
        except Exception:
            # Search below is the supported fallback for thin/blocked maps.
            pass

    found_years = {
        year for year in years if any(_looks_like_report(item, year) for item, _ in pool)
    }
    if official_url and found_years != set(years):
        try:
            pool.extend((item, "page") for item in client.scrape_links(official_url))
        except Exception:
            # Some IR pages block a full scrape while still exposing a sitemap.
            pass

    found_years = {
        year for year in years if any(_looks_like_report(item, year) for item, _ in pool)
    }
    if found_years != set(years):
        # One broad PDF search returns the issuer's filing series and avoids six
        # almost-identical paid requests for a company with no public reports.
        # The year is still required in every accepted result below.
        if is_japanese:
            query = f'"{company}" 有価証券報告書 filetype:pdf'
        else:
            query = f'"{company}" official annual report 10-k filetype:pdf'
        pool.extend((item, "search") for item in client.search(query, limit=50, country=country))

    if deep_search:
        found_years = {
            year for year in years if any(_looks_like_report(item, year) for item, _ in pool)
        }
        for year in years:
            if year in found_years:
                continue
            queries = (
                (
                    f'"{company}" {year} 有価証券報告書 PDF',
                    f'"{company}" FY{year} annual report PDF',
                )
                if is_japanese
                else (
                    f'"{company}" {year} annual report filetype:pdf',
                    f'"{company}" FY{year} 10-k PDF',
                )
            )
            for query in queries:
                pool.extend((item, "deep_search") for item in client.search(query, limit=25, country=country))

    output: dict[int, list[ReportCandidate]] = {year: [] for year in years}
    seen: set[tuple[int, str]] = set()
    for item, discovery in pool:
        url = str(item.get("url") or "").strip()
        if not url.startswith(("https://", "http://")):
            continue
        matches_official = _matches_domain(url, official_domain)
        trusted_public_filing = _trusted_public_filing(item, company)
        # Search results are untrusted.  A high-scoring PDF from another
        # company must never be downloaded merely because its title contains
        # the requested fiscal year.  Map results are different: Firecrawl
        # reached them by following the supplied official site, which commonly
        # delegates filings to a disclosure/CDN host.
        if (
            discovery in {"search", "deep_search"}
            and official_domain
            and not matches_official
            and not trusted_public_filing
        ):
            continue
        for year in years:
            if not _looks_like_report(item, year) or (year, url) in seen:
                continue
            seen.add((year, url))
            output[year].append(ReportCandidate(
                company=company,
                year=year,
                url=url,
                title=str(item.get("title") or ""),
                description=str(item.get("description") or ""),
                discovery=discovery,
                official_domain=official_domain,
                source_verified=bool(
                    trusted_public_filing
                    or (official_domain and (matches_official or discovery in {"map", "page"}))
                ),
                score=_score(item, year, official_domain),
            ))
    for candidates in output.values():
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.url))
    return output
