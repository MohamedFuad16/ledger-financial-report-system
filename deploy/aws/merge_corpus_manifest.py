"""Merge live EC2 corpus state with a newly deployed seed manifest."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def document_identity(document: dict[str, Any]) -> tuple[str, int]:
    company = str(document.get("company_slug") or document.get("company") or "").strip().casefold()
    return company, int(document.get("fiscal_year") or 0)


def merge_manifests(live: dict[str, Any], deployed: dict[str, Any]) -> dict[str, Any]:
    """Return the union, preferring live runtime state on identity conflicts."""
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for document in deployed.get("documents", []):
        if isinstance(document, dict):
            merged[document_identity(document)] = document
    for document in live.get("documents", []):
        if isinstance(document, dict):
            merged[document_identity(document)] = document
    documents = sorted(
        merged.values(),
        key=lambda item: (
            str(item.get("company") or "").casefold(),
            int(item.get("fiscal_year") or 0),
        ),
    )
    return {
        "version": max(int(live.get("version") or 1), int(deployed.get("version") or 1)),
        "updated_at": datetime.now(UTC).isoformat(),
        "documents": documents,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", required=True, type=Path)
    parser.add_argument("--deployed", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    live = json.loads(args.live.read_text(encoding="utf-8"))
    deployed = json.loads(args.deployed.read_text(encoding="utf-8"))
    payload = merge_manifests(live, deployed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"Merged {len(payload['documents'])} corpus documents into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
