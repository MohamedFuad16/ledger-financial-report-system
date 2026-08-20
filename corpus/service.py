"""Corpus builder orchestration used by the Flask background job."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable

from .client import FirecrawlClient
from .discover import discover_company_reports
from .fetch import fetch_report


Progress = Callable[[dict[str, Any]], None]


def build_corpus(
    companies: list[dict[str, str]],
    years: Iterable[int] = range(2020, 2026),
    *,
    api_key: str = "",
    max_downloads: int = 3,
    on_event: Progress | None = None,
) -> dict[str, Any]:
    years = sorted({int(year) for year in years if 2020 <= int(year) <= 2025})
    if not years:
        raise ValueError("Choose at least one fiscal year from 2020 through 2025.")
    if not companies:
        raise ValueError("Add at least one company.")

    emit = on_event or (lambda _event: None)
    client = FirecrawlClient(
        api_key or os.getenv("FIRECRAWL_API_KEY", ""),
        on_retry=lambda attempt, delay, error: emit({
            "type": "retry", "attempt": attempt, "delay": round(delay, 1), "message": error,
        }),
    )
    candidate_groups: list[list[dict[str, Any]]] = []
    missing: list[dict[str, Any]] = []

    for company in companies:
        name = str(company.get("name") or "").strip()
        if not name:
            continue
        emit({"type": "discovering", "company": name})
        discovered = discover_company_reports(
            client,
            company=name,
            official_url=str(company.get("official_url") or "").strip(),
            country=str(company.get("country") or "US"),
            years=years,
        )
        for year in years:
            choices = discovered.get(year) or []
            if choices:
                candidate_groups.append([choice.as_dict() for choice in choices[:5]])
            else:
                missing.append({"company": name, "year": year, "reason": "No report URL discovered."})
        emit({"type": "discovered", "company": name, "reports": sum(bool(value) for value in discovered.values())})

    downloaded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = list(missing)

    def fetch_first(choices: list[dict[str, Any]]) -> dict[str, Any]:
        errors: list[str] = []
        for candidate in choices:
            try:
                return fetch_report(candidate)
            except Exception as exc:  # try the next ranked official candidate
                errors.append(f"{candidate['url']}: {exc}")
        raise RuntimeError("; ".join(errors))

    with ThreadPoolExecutor(max_workers=max(1, min(int(max_downloads), 8))) as executor:
        futures = {executor.submit(fetch_first, choices): choices[0] for choices in candidate_groups}
        for future in as_completed(futures):
            candidate = futures[future]
            try:
                document = future.result()
            except Exception as exc:
                failed.append({"company": candidate["company"], "year": candidate["year"], "reason": str(exc), "url": candidate["url"]})
                emit({"type": "failed", **failed[-1]})
            else:
                downloaded.append(document)
                emit({"type": "downloaded", "company": document["company"], "year": document["fiscal_year"], "screened": document["screened"], "path": document["local_path"]})

    return {
        "requested": len(companies) * len(years),
        "downloaded": downloaded,
        "failed": failed,
        "years": years,
    }
