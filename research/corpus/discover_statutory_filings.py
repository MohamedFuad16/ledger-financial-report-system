"""Discover public statutory financial-statement PDFs for Bakuraku clients.

This research command deliberately has a wider vocabulary than the product's
Annual Report discovery flow.  It records candidates only; it never downloads,
screens, or promotes a result to benchmark gold.  Every accepted benchmark
source still requires exact-entity/year screening, SHA pinning, a complete
27-row scored/unscorable partition, and two independent verification passes.

The output is checkpointed after every company so a paid Firecrawl sweep can be
resumed without repeating completed searches.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from corpus.client import FirecrawlClient  # noqa: E402


CUSTOMERS = ROOT / "research" / "bakuraku" / "customers.csv"
DEFAULT_OUTPUT = ROOT / "research" / "corpus" / "firecrawl_statutory_filings.json"
STATEMENT_WORDS = re.compile(
    r"決算公告|貸借対照表|財務諸表|計算書類|決算書|有価証券報告書|"
    r"annual\s+report|financial\s+statements?|balance\s+sheet",
    re.I,
)


def normalized(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", value).casefold()
        if character.isalnum()
    )


def write_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_customers() -> list[dict[str, str]]:
    with CUSTOMERS.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def candidate(item: dict, company: str, official_url: str) -> dict | None:
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or "").strip()
    description = str(item.get("description") or "").strip()
    text = " ".join((url, title, description))
    if not url.startswith(("https://", "http://")) or not STATEMENT_WORDS.search(text):
        return None

    official_host = urlparse(official_url).netloc.lower().removeprefix("www.")
    result_host = urlparse(url).netloc.lower().removeprefix("www.")
    exact_identity = normalized(company) in normalized(f"{title} {description}")
    official_host_match = bool(
        official_host
        and (result_host == official_host or result_host.endswith(f".{official_host}"))
    )
    return {
        "url": url,
        "title": title,
        "description": description,
        "host": result_host,
        "is_pdf_url": urlparse(url).path.lower().endswith(".pdf"),
        "exact_identity_in_result": exact_identity,
        "official_host_match": official_host_match,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="0 searches every remaining client")
    parser.add_argument("--start-after", default="")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    client = FirecrawlClient(os.getenv("FIRECRAWL_API_KEY", ""))
    output = args.output.expanduser().resolve()
    payload = (
        json.loads(output.read_text(encoding="utf-8"))
        if output.exists()
        else {"version": 1, "purpose": "candidate discovery only", "companies": {}}
    )
    completed = payload.setdefault("companies", {})
    started = not bool(args.start_after)
    searched = 0

    for row in load_customers():
        company = str(row["company_name"]).strip()
        if not started:
            started = company == args.start_after
            continue
        if company in completed:
            continue
        if args.limit and searched >= args.limit:
            break

        official_url = str(row.get("official_website") or "").strip()
        query = (
            f'"{company}" 決算公告 貸借対照表 財務諸表 計算書類 '
            "有価証券報告書 filetype:pdf"
        )
        print(f"SEARCH {company}", flush=True)
        try:
            raw_results = client.search(query, limit=20, country="JP")
            candidates = [
                parsed
                for item in raw_results
                if (parsed := candidate(item, company, official_url)) is not None
            ]
            completed[company] = {
                "official_website": official_url,
                "query": query,
                "result_count": len(raw_results),
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
            print(f"FOUND {company}: {len(candidates)}/{len(raw_results)} candidates", flush=True)
        except Exception as exc:
            completed[company] = {
                "official_website": official_url,
                "query": query,
                "error": str(exc),
                "candidate_count": 0,
                "candidates": [],
            }
            print(f"ERROR {company}: {exc}", flush=True)
        write_checkpoint(output, payload)
        searched += 1

    print(f"WROTE {len(completed)} companies to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
