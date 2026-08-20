"""Thread-safe, atomic corpus manifest persistence."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CORPUS_ROOT = Path("corpus_dataset")
MANIFEST_PATH = CORPUS_ROOT / "corpus_manifest.json"
_LOCK = threading.Lock()


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"version": 1, "updated_at": None, "documents": []}
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "updated_at": None, "documents": []}
    payload.setdefault("version", 1)
    payload.setdefault("documents", [])
    return payload


def upsert_document(document: dict[str, Any]) -> dict[str, Any]:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        manifest = load_manifest()
        documents = manifest["documents"]
        documents[:] = [
            item for item in documents
            if item.get("sha256") != document.get("sha256")
            and (item.get("company_slug"), item.get("fiscal_year"))
            != (document.get("company_slug"), document.get("fiscal_year"))
        ]
        documents.append(document)
        documents.sort(key=lambda item: (str(item.get("company", "")).lower(), int(item.get("fiscal_year") or 0)))
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        temporary = MANIFEST_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(MANIFEST_PATH)
        return document
