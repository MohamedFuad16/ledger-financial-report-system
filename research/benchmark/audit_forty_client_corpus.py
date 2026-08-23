"""Prove the maintained corpus contains forty twice-audited Bakuraku clients.

This verifier is deliberately stricter than a manifest count.  It requires each
client to exist in the evidence-backed Bakuraku registry, have one exact
SHA-bound gold fixture with two named audit passes, account for all 27 canonical
rows as either scorable or explicitly unscorable, and have the exact source
bytes pinned by the local corpus manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from schema import ASSET_SCHEMA  # noqa: E402


REGISTRY = ROOT / "research" / "bakuraku" / "customers.csv"
MANIFEST = ROOT / "corpus_dataset" / "corpus_manifest.json"
OUTPUT = ROOT / "research" / "benchmark" / "forty_client_corpus_audit.json"
FIXTURES = (
    ROOT / "benchmark_data" / "bakuraku_fy2022_gold.json",
    ROOT / "benchmark_data" / "fy2022_expansion_gold.json",
    ROOT / "benchmark_data" / "bakuraku_statutory_gold.json",
)
TARGET_COUNT = 40


def normalized_company(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    with REGISTRY.open(encoding="utf-8", newline="") as handle:
        registry = {
            normalized_company(row["company_name"]): row
            for row in csv.DictReader(handle)
        }

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_by_hash = {
        str(document.get("sha256") or ""): document
        for document in manifest.get("documents", [])
    }
    canonical_rows = {str(row["item"]) for row in ASSET_SCHEMA}
    audited_by_company: dict[str, dict] = {}
    failures: list[str] = []

    for fixture_path in FIXTURES:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        documents = payload.get("documents") or {}
        if not isinstance(documents, dict):
            failures.append(f"{fixture_path.name}: documents must be an object keyed by SHA-256")
            continue
        for source_hash, gold in documents.items():
            company = str(gold.get("company") or "")
            company_key = normalized_company(company)
            if company_key not in registry:
                # The expansion fixture intentionally retains two non-client
                # controls.  They are excluded rather than counted as clients.
                continue
            if company_key in audited_by_company:
                failures.append(f"{company}: duplicate client gold fixture")
                continue

            answers = set((gold.get("answers") or {}).keys())
            unscorable = set(gold.get("unscorable_rows") or [])
            passes = list(gold.get("audit_passes") or [])
            if len(source_hash) != 64:
                failures.append(f"{company}: invalid source SHA-256")
            if not str(gold.get("status") or "").startswith("independently_verified"):
                failures.append(f"{company}: gold status is not independently verified")
            if len(passes) != 2 or len(set(passes)) != 2:
                failures.append(f"{company}: expected exactly two distinct audit passes")
            if answers & unscorable or answers | unscorable != canonical_rows:
                failures.append(f"{company}: scorable/unscorable rows do not partition the 27-row schema")

            pinned = manifest_by_hash.get(source_hash)
            if not pinned:
                failures.append(f"{company}: exact source SHA is absent from the corpus manifest")
                continue
            if normalized_company(pinned.get("company")) != company_key:
                failures.append(f"{company}: fixture and manifest entity identities disagree")
            if str(pinned.get("fiscal_year")) != str(gold.get("fiscal_year")):
                failures.append(f"{company}: fixture and manifest fiscal years disagree")

            source_path = Path(str(pinned.get("local_path") or ""))
            if not source_path.is_absolute():
                source_path = ROOT / source_path
            if not source_path.is_file():
                failures.append(f"{company}: pinned source file is missing")
                continue
            observed_hash = sha256(source_path)
            if observed_hash != source_hash:
                failures.append(f"{company}: pinned source bytes do not match the fixture SHA")
                continue

            audited_by_company[company_key] = {
                "company": company,
                "bakuraku_evidence_url": registry[company_key]["evidence_url"],
                "bakuraku_evidence_type": registry[company_key]["evidence_type"],
                "fiscal_year": int(gold["fiscal_year"]),
                "source_sha256": source_hash,
                "source_path": str(source_path.relative_to(ROOT)),
                "status": gold["status"],
                "audit_passes": passes,
                "scorable_rows": len(answers),
                "unscorable_rows": len(unscorable),
                "all_27_rows_accounted_for": True,
                "exact_source_bytes_verified": True,
            }

    if len(audited_by_company) != TARGET_COUNT:
        failures.append(
            f"expected {TARGET_COUNT} unique Bakuraku clients, found {len(audited_by_company)}"
        )

    result = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failures else "failed",
        "target_client_count": TARGET_COUNT,
        "verified_client_count": len(audited_by_company),
        "assignment_control": "3M FY2022 (not counted as a Bakuraku client)",
        "requirements": {
            "bakuraku_registry_membership": not any("registry" in item for item in failures),
            "two_distinct_audit_passes": not any("audit passes" in item for item in failures),
            "all_schema_rows_accounted_for": not any("27-row schema" in item for item in failures),
            "exact_source_sha_and_bytes": not any(
                phrase in item
                for item in failures
                for phrase in ("SHA", "source file", "source bytes")
            ),
        },
        "failures": failures,
        "clients": sorted(
            audited_by_company.values(),
            key=lambda item: normalized_company(item["company"]),
        ),
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['status'].upper()}: {result['verified_client_count']}/"
        f"{result['target_client_count']} twice-audited Bakuraku clients"
    )
    for failure in failures:
        print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
