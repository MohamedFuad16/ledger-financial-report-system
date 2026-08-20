"""Command-line entry point for an Annual Report corpus job.

The Flask UI starts the same service in a daemon thread. This entry point is
useful for a long local batch that should keep running independently of a
browser tab.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from corpus.service import build_corpus
from settings import current_settings, load_local_env


def load_companies(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("companies", payload) if isinstance(payload, dict) else payload
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        return [
            {
                "name": row.get("company_name") or row.get("name") or "",
                "official_url": row.get("official_website") or row.get("official_url") or "",
                "country": row.get("country") or "JP",
            }
            for row in rows
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover and download FY2020–FY2025 Annual Reports.")
    parser.add_argument("companies", type=Path, help="CSV or JSON company seed file")
    parser.add_argument("--years", nargs="+", type=int, default=list(range(2020, 2026)))
    parser.add_argument("--downloads", type=int, default=4, help="Maximum parallel PDF downloads")
    args = parser.parse_args()
    load_local_env()
    settings = current_settings()
    result = build_corpus(
        load_companies(args.companies)[:200],
        args.years,
        api_key=settings.get("firecrawl_api_key", ""),
        max_downloads=args.downloads,
        on_event=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
