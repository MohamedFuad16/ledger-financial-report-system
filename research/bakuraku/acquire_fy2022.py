"""Acquire the pinned FY2022 Bakuraku-customer benchmark sources.

Firecrawl establishes the company/archive seed. Exact filing IDs are then
validated against the issuer archive or EDINET before this script downloads and
passes each PDF through Ledger's local admission screener.
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


SOURCES_PATH = Path(__file__).with_name("fy2022_sources.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing-only", action="store_true")
    args = parser.parse_args()

    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    existing = {
        (str(document.get("company")), int(document.get("fiscal_year") or 0))
        for document in load_manifest().get("documents", [])
    }
    failed = 0
    for source in sources:
        identity = (str(source["company"]), int(source["year"]))
        if args.missing_only and identity in existing:
            print(f"SKIP {identity[0]} FY{identity[1]} (already pinned)")
            continue
        try:
            document = fetch_report(source)
        except Exception as exc:
            failed += 1
            print(f"FAIL {identity[0]} FY{identity[1]}: {exc}")
            continue
        print(
            f"OK {identity[0]} FY{identity[1]} "
            f"pages={document['pages']} balance_page={document['balance_sheet_page']} "
            f"currency={document['currency']} sha256={document['sha256']}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
