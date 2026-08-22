"""Acquire the five exact FY2022 audit sources into the durable corpus.

The source registry was assembled from official issuer/FSA archives after the
Firecrawl discovery pass. Downloads still use the normal signature, hash,
annual-report screen, canonical naming, and atomic manifest replacement path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from corpus.fetch import fetch_report  # noqa: E402


REGISTRY = ROOT / "research" / "benchmark" / "fy2022_expansion_sources.json"


def acquire() -> list[dict]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    acquired: list[dict] = []
    for source in payload["sources"]:
        host = urlparse(source["url"]).netloc.lower().removeprefix("www.")
        document = fetch_report({
            "company": source["company"],
            "year": int(payload["fiscal_year"]),
            "url": source["url"],
            "title": f"FY{payload['fiscal_year']} annual/securities report",
            "official_domain": host,
            "source_verified": True,
            "discovery": "Firecrawl discovery followed by exact official-archive pin",
            "expected_sha256": source["sha256"],
        })
        acquired.append(document)
        print(
            f"PINNED {document['company']} FY{document['fiscal_year']} "
            f"{document['sha256']} ({document['pages']} pages, {document['currency']})"
        )
    return acquired


if __name__ == "__main__":
    acquire()
