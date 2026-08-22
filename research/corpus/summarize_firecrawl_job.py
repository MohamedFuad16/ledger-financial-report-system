#!/usr/bin/env python3
"""Build an auditable Bakuraku/Firecrawl annual-report availability ledger."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CUSTOMERS = ROOT / "research" / "bakuraku" / "customers.csv"
DEFAULT_OUTPUT = ROOT / "research" / "corpus" / "firecrawl_availability"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Corpus job payload must be a JSON object.")
    return payload


def customer_names(path: Path = CUSTOMERS) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            str(row.get("company_name") or row.get("company") or "").strip()
            for row in csv.DictReader(handle)
        ]


def build_rows(job: dict[str, Any], customers: list[str]) -> list[dict[str, Any]]:
    years = [int(year) for year in job.get("years") or range(2020, 2026)]
    events = job.get("events") or []
    discovered = {
        str(event.get("company") or ""): int(event.get("reports") or 0)
        for event in events
        if event.get("type") == "discovered"
    }
    result = job.get("result") or {}
    downloaded: dict[tuple[str, int], dict[str, Any]] = {}
    for document in result.get("downloaded") or []:
        key = (str(document.get("company") or ""), int(document.get("fiscal_year") or 0))
        downloaded[key] = document
    failures: dict[tuple[str, int], list[str]] = defaultdict(list)
    for failure in result.get("failed") or []:
        key = (str(failure.get("company") or ""), int(failure.get("year") or 0))
        failures[key].append(str(failure.get("reason") or "Unknown failure"))

    rows: list[dict[str, Any]] = []
    for company in customers:
        company_done = company in discovered
        for year in years:
            document = downloaded.get((company, year))
            reasons = failures.get((company, year), [])
            if document:
                status = "downloaded"
            elif reasons:
                status = "not_downloaded"
            elif company_done:
                status = "candidate_found" if discovered[company] else "not_found"
            else:
                status = "pending"
            rows.append({
                "company": company,
                "fiscal_year": year,
                "status": status,
                "company_candidates_found": discovered.get(company, ""),
                "screened": document.get("screened", "") if document else "",
                "sha256": document.get("sha256", "") if document else "",
                "source_url": document.get("source_url", "") if document else "",
                "reason": " | ".join(reasons),
            })
    return rows


def write_outputs(job: dict[str, Any], rows: list[dict[str, Any]], prefix: Path) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with prefix.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "job_id": job.get("id"),
        "job_status": job.get("status"),
        "updated_at": job.get("updated_at"),
        "companies": len({row["company"] for row in rows}),
        "requested_company_years": len(rows),
        "status_counts": {
            status: sum(row["status"] == status for row in rows)
            for status in sorted({str(row["status"]) for row in rows})
        },
        "rows": rows,
    }
    prefix.with_suffix(".json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    counts = summary["status_counts"]
    lines = [
        "# Firecrawl annual-report availability",
        "",
        f"- Job: `{summary['job_id']}` ({summary['job_status']})",
        f"- Updated: {summary['updated_at']}",
        f"- Bakuraku clients: {summary['companies']}",
        f"- Company/year requests: {summary['requested_company_years']}",
        "- Status counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()),
        "",
        "`candidate_found` is company-level discovery progress, not a claim that every year has a usable PDF. "
        "Only `downloaded` rows identify screened, pinned files; benchmark gold still requires two independent reviews.",
        "",
    ]
    prefix.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_json", type=Path)
    parser.add_argument("--customers", type=Path, default=CUSTOMERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    job = load_json(args.job_json)
    rows = build_rows(job, customer_names(args.customers))
    if not rows:
        raise SystemExit("No customer/year rows were produced.")
    write_outputs(job, rows, args.output)
    print(f"Wrote {args.output.with_suffix('.csv')}, .json and .md")


if __name__ == "__main__":
    main()
