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


def delete_pinned_document(document_id: str) -> dict[str, Any] | None:
    """Delete one manifest-owned PDF and its manifest entry by SHA-256.

    The caller supplies only the manifest identifier.  The stored path is still
    resolved and constrained to ``CORPUS_ROOT`` before anything is removed, so
    a stale or tampered manifest cannot turn this into arbitrary file deletion.
    Existing extraction runs are intentionally left untouched.
    """
    identifier = str(document_id or "").strip()
    if not identifier:
        return None

    with _LOCK:
        manifest = load_manifest()
        documents = manifest["documents"]
        document = next((item for item in documents if str(item.get("sha256") or "") == identifier), None)
        if document is None:
            return None

        corpus_root = CORPUS_ROOT.resolve()
        raw_path = str(document.get("local_path") or "").strip()
        if not raw_path:
            raise ValueError("The pinned manifest entry has no stored PDF path.")
        pdf_path = Path(raw_path).resolve()
        if not pdf_path.is_relative_to(corpus_root):
            raise ValueError("The pinned PDF path is outside corpus storage.")
        if pdf_path.exists() and not pdf_path.is_file():
            raise ValueError("The pinned PDF path is not a file.")

        file_removed = pdf_path.is_file()
        if file_removed:
            pdf_path.unlink()
            parent = pdf_path.parent
            while parent != corpus_root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent

        documents[:] = [item for item in documents if str(item.get("sha256") or "") != identifier]
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        temporary = MANIFEST_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(MANIFEST_PATH)
        return {**document, "file_removed": file_removed}
