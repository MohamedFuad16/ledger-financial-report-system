"""Discover Annual Report PDF URLs, preferring supplied official IR sites."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import urlparse

from .client import FirecrawlClient


REPORT_WORDS = re.compile(r"annual[-_\s]?report|form[-_\s]?10[-_\s]?k|10-k", re.I)


@dataclass(frozen=True)
class ReportCandidate:
    company: str
    year: int
    url: str
    title: str = ""
    description: str = ""
    discovery: str = "search"
    official_domain: str = ""
    score: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _looks_like_report(item: dict, year: int) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("url", "title", "description"))
    return str(year) in text and (REPORT_WORDS.search(text) is not None or ".pdf" in text.lower())


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


def discover_company_reports(
    client: FirecrawlClient,
    *,
    company: str,
    years: Iterable[int],
    official_url: str = "",
    country: str = "US",
) -> dict[int, list[ReportCandidate]]:
    years = sorted({int(year) for year in years})
    official_domain = _domain(official_url)
    pool: list[tuple[dict, str]] = []

    if official_url:
        try:
            pool.extend((item, "map") for item in client.map(official_url, search="annual report 10-k"))
        except Exception:
            # Search below is the supported fallback for thin/blocked maps.
            pass

    found_years = {
        year for year in years if any(_looks_like_report(item, year) for item, _ in pool)
    }
    for year in years:
        if year in found_years:
            continue
        query = f'"{company}" official investor relations annual report {year} filetype:pdf'
        pool.extend((item, "search") for item in client.search(query, limit=8, country=country))

    output: dict[int, list[ReportCandidate]] = {year: [] for year in years}
    seen: set[tuple[int, str]] = set()
    for item, discovery in pool:
        url = str(item.get("url") or "").strip()
        if not url.startswith(("https://", "http://")):
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
                score=_score(item, year, official_domain),
            ))
    for candidates in output.values():
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.url))
    return output
