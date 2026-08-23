"""Inventory exact-entity public gazette balance-sheet announcements.

This is a research-only complement to Firecrawl discovery.  It queries the
public 官報決算データベース index, resolves the newest announcement image, and
records provenance.  It never promotes a record into the corpus or benchmark
gold: the mirrored gazette image still needs identity review, source pinning,
27-row partitioning, and two independent verification passes.
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CUSTOMERS = ROOT / "research" / "bakuraku" / "customers.csv"
OUTPUT = ROOT / "research" / "corpus" / "gazette_statutory_filings.json"
BASE = "https://catr.jp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LedgerCorpusResearch/1.0)",
    "Accept": "text/html,application/json",
}
ALIASES = {
    "STORES株式会社（旧ヘイ株式会社）": "STORES株式会社",
    "SEVENRICH会計事務所・株式会社SEVENRICH Accounting": "株式会社SEVENRICH Accounting",
    "ゴージュ会計事務所／ゴージュ株式会社": "ゴージュ株式会社",
    "東京フットボールクラブ株式会社（FC東京）": "東京フットボールクラブ株式会社",
    "株式会社AZURE（税理士法人札幌中央会計グループ）": "株式会社AZURE",
    "株式会社PIGNUS（ピグナス）": "株式会社PIGNUS",
}


def normalize(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", value).casefold()
        if character.isalnum()
    )


def fetch(url: str) -> bytes:
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=30) as response:
        return response.read()


def first_match(pattern: str, document: str) -> str:
    match = re.search(pattern, document, flags=re.I | re.S)
    return html.unescape(match.group(1).strip()) if match else ""


def exact_company_document(company: str) -> dict | None:
    params = {
        "q": company,
        "query_by": "full_text_search",
        "infix": "always",
        "num_typos": "0",
        "prefix": "false",
        "per_page": "20",
        "page": "1",
    }
    payload = json.loads(fetch(f"{BASE}/search/typesense?{urlencode(params)}"))
    exact = [
        hit["document"]
        for hit in payload.get("hits", [])
        if normalize(str(hit.get("document", {}).get("name", ""))) == normalize(company)
        and int(hit.get("document", {}).get("settlement_count") or 0) > 0
    ]
    active = [item for item in exact if item.get("is_active")]
    selected = active or exact
    return selected[0] if len(selected) == 1 else None


def main() -> int:
    records: list[dict] = []
    with CUSTOMERS.open(encoding="utf-8", newline="") as stream:
        customers = list(csv.DictReader(stream))

    for index, customer in enumerate(customers, start=1):
        registry_name = customer["company_name"].strip()
        query_name = ALIASES.get(registry_name, registry_name).strip()
        try:
            company = exact_company_document(query_name)
            if company is None:
                print(f"MISS {index:03d} {registry_name}", flush=True)
                continue

            company_url = f"{BASE}/companies/{company['key']}/{company['id']}"
            company_html = fetch(company_url).decode("utf-8", errors="replace")
            settlement_paths = list(
                dict.fromkeys(
                    re.findall(
                        rf'href="(/companies/{re.escape(str(company["key"]))}/'
                        rf'{re.escape(str(company["id"]))}/settlements/[^"]+)"',
                        company_html,
                    )
                )
            )
            if not settlement_paths:
                print(f"MISS {index:03d} {registry_name} (no announcement link)", flush=True)
                continue

            settlement_url = urljoin(BASE, settlement_paths[0])
            settlement_html = fetch(settlement_url).decode("utf-8", errors="replace")
            image_url = first_match(
                r'<meta\s+property="og:image"\s+content="([^"]+)"', settlement_html
            )
            page_company = first_match(
                r'<meta\s+property="og:title"\s+content="([^"|]+?)\s+第', settlement_html
            )
            if normalize(page_company) != normalize(query_name) or not image_url:
                print(f"REJECT {index:03d} {registry_name} (identity/image)", flush=True)
                continue

            official_host = urlparse(customer.get("official_website", "")).netloc.lower()
            official_host = official_host.removeprefix("www.")
            page_hosts = {
                host.removeprefix("www.")
                for host in re.findall(r'href="https?://([^/"?#]+)', settlement_html, flags=re.I)
            }
            records.append(
                {
                    "registry_company": registry_name,
                    "filing_company": page_company,
                    "company_index_url": company_url,
                    "announcement_url": settlement_url,
                    "announcement_image_url": image_url,
                    "closed_date": company.get("closed_date", ""),
                    "total_assets_index_value_yen": company.get("total_assets"),
                    "official_website": customer.get("official_website", ""),
                    "official_host_present_on_announcement": bool(
                        official_host
                        and any(
                            host == official_host or host.endswith(f".{official_host}")
                            for host in page_hosts
                        )
                    ),
                    "status": "candidate_only",
                }
            )
            print(f"FOUND {index:03d} {registry_name}", flush=True)
        except Exception as exc:  # Research inventory must continue across individual failures.
            print(f"ERROR {index:03d} {registry_name}: {exc}", flush=True)
        time.sleep(0.12)

    OUTPUT.write_text(
        json.dumps(
            {
                "version": 1,
                "purpose": "candidate discovery only; not benchmark gold",
                "source": "public Japanese gazette announcement mirror",
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {len(records)} exact-entity candidates to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
