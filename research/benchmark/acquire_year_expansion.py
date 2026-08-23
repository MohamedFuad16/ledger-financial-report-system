"""Acquire additional fiscal years for the exact-source Bakuraku clients.

Sources were located manually (no Firecrawl credits): IR BANK's per-ticker
EDINET indexes provided annual securities-report docIDs, which download
anonymously from disclosure2dl.edinet-fsa.go.jp. Every candidate still passes
Ledger's local admission screener — content-level company identity, annual
document type, expected fiscal year, and a readable balance sheet — before it
can replace or create a canonical corpus entry. Entries marked unavailable are
retained honestly and skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from corpus.fetch import fetch_report  # noqa: E402
from corpus.manifest import load_manifest  # noqa: E402

SOURCES_PATH = Path(__file__).with_name("year_expansion_sources.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing-only", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    existing = {
        (str(document.get("company")), int(document.get("fiscal_year") or 0))
        for document in load_manifest().get("documents", [])
    }
    attempted = failed = admitted = 0
    for source in sources:
        if source.get("unavailable") or source.get("error"):
            continue
        identity = (str(source["company"]), int(source["year"]))
        if args.missing_only and identity in existing:
            print(f"SKIP {identity[0]} FY{identity[1]} (already pinned)")
            continue
        if args.limit and attempted >= args.limit:
            break
        attempted += 1
        try:
            document = fetch_report(source)
        except Exception as exc:  # screening rejection is a result, not a crash
            failed += 1
            print(f"FAIL {identity[0]} FY{identity[1]}: {exc}")
            continue
        admitted += 1
        print(
            f"OK {identity[0]} FY{identity[1]} "
            f"pages={document['pages']} balance_page={document['balance_sheet_page']} "
            f"currency={document['currency']} sha256={document['sha256'][:12]}"
        )
    print(f"attempted={attempted} admitted={admitted} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
