"""Corpus builder orchestration used by the Flask background job."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable

from .client import FirecrawlClient
from .discover import discover_company_reports
from .fetch import fetch_report, pin_candidate_answers


Progress = Callable[[dict[str, Any]], None]


def extract_document_candidates(
    document: dict[str, Any],
    *,
    api_key: str = "",
    firecrawl_pdf_mode: str = "auto",
    candidate_passes: int = 3,
    on_event: Progress | None = None,
    client: FirecrawlClient | None = None,
) -> dict[str, Any]:
    """Extract and persist a review-ready answer sheet for one pinned PDF.

    The result is intentionally provisional. It pre-fills the human review UI,
    but it does not become benchmark gold until the reviewer approves it.
    """
    emit = on_event or (lambda _event: None)
    source_url = str(document.get("source_url") or "").strip()
    if not source_url:
        raise ValueError("The pinned report has no source PDF URL to extract.")
    if client is None:
        client = FirecrawlClient(
            api_key or os.getenv("FIRECRAWL_API_KEY", ""),
            on_retry=lambda attempt, delay, error: emit({
                "type": "retry", "attempt": attempt, "delay": round(delay, 1), "message": error,
            }),
        )

    requested_passes = max(1, min(int(candidate_passes), 3))
    parsed_passes: list[dict[str, Any]] = []
    for pass_number in range(1, requested_passes + 1):
        emit({
            "type": "candidate_pass_started",
            "company": document.get("company"),
            "year": document.get("fiscal_year"),
            "pass": pass_number,
            "passes": requested_passes,
        })
        try:
            parsed_passes.append(client.extract_candidate_answers(source_url, mode=firecrawl_pdf_mode))
        except Exception as exc:
            emit({
                "type": "candidate_pass_failed",
                "company": document.get("company"),
                "year": document.get("fiscal_year"),
                "pass": pass_number,
                "passes": requested_passes,
                "message": str(exc),
            })
            continue
        emit({
            "type": "candidate_pass_ready",
            "company": document.get("company"),
            "year": document.get("fiscal_year"),
            "pass": pass_number,
            "passes": requested_passes,
        })

    if not parsed_passes:
        raise RuntimeError("The PDF answer extraction failed on every attempt.")
    return pin_candidate_answers(document, parsed_passes, requested_passes=requested_passes)


def build_corpus(
    companies: list[dict[str, str]],
    years: Iterable[int] = range(2020, 2026),
    *,
    api_key: str = "",
    max_downloads: int = 3,
    firecrawl_pdf_mode: str = "auto",
    candidate_passes: int = 3,
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
                emit({"type": "downloaded", "company": document["company"], "year": document["fiscal_year"], "screened": document["screened"], "path": document["local_path"]})
                emit({
                    "type": "extracting_candidates",
                    "company": document["company"],
                    "year": document["fiscal_year"],
                    "provider": "firecrawl",
                    "mode": firecrawl_pdf_mode,
                })
                try:
                    document = extract_document_candidates(
                        document,
                        firecrawl_pdf_mode=firecrawl_pdf_mode,
                        candidate_passes=candidate_passes,
                        on_event=emit,
                        client=client,
                    )
                except Exception as exc:
                    emit({
                        "type": "candidate_extraction_failed",
                        "company": document["company"],
                        "year": document["fiscal_year"],
                        "provider": "firecrawl",
                        "mode": firecrawl_pdf_mode,
                        "message": str(exc),
                    })
                else:
                    emit({
                        "type": "candidates_ready",
                        "company": document["company"],
                        "year": document["fiscal_year"],
                        "provider": "firecrawl",
                        "mode": firecrawl_pdf_mode,
                        "rows": len(document.get("verification", {})) and 27,
                        "consensus": document.get("verification", {}).get("consensus_summary"),
                    })
                downloaded.append(document)

    return {
        "requested": len(companies) * len(years),
        "downloaded": downloaded,
        "failed": failed,
        "years": years,
    }
