"""Thread-safe, atomic corpus manifest persistence."""

from __future__ import annotations

import json
import fcntl
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schema import (
    ASSET_SCHEMA,
    ASSIGNMENT_GOLDEN_SOURCE_SHA256,
    GOLDEN_ANSWERS_STORE,
    SOURCE_BOUND_GOLDEN_ANSWERS,
)


CORPUS_ROOT = Path("corpus_dataset")
MANIFEST_PATH = CORPUS_ROOT / "corpus_manifest.json"
_LOCK = threading.Lock()
@contextmanager
def _manifest_guard():
    """Serialize manifest mutations across threads and Gunicorn workers."""
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        lock_path = CORPUS_ROOT / ".corpus_manifest.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _write_manifest(manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(MANIFEST_PATH)


def _manifest_owned_path(raw_path: str) -> Path | None:
    """Resolve a stored path only when it is owned by the corpus root."""
    if not str(raw_path or "").strip():
        return None
    path = Path(raw_path).resolve()
    return path if path.is_relative_to(CORPUS_ROOT.resolve()) else None


def _prune_empty_parents(path: Path) -> None:
    corpus_root = CORPUS_ROOT.resolve()
    parent = path.parent
    while parent != corpus_root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _document_owned_paths(document: dict[str, Any]) -> list[Path]:
    """Return every corpus-owned file pinned by one manifest document."""
    raw_paths = [str(document.get("local_path") or "")]
    verification = document.get("verification")
    if isinstance(verification, dict):
        raw_paths.extend([
            str(verification.get("candidate_path") or ""),
            str(verification.get("approved_path") or ""),
        ])
        pass_paths = verification.get("candidate_pass_paths")
        if isinstance(pass_paths, list):
            raw_paths.extend(str(path or "") for path in pass_paths)
    paths: list[Path] = []
    for raw_path in raw_paths:
        owned = _manifest_owned_path(raw_path)
        if owned and owned not in paths:
            paths.append(owned)
    return paths


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


def migrate_corpus_layout() -> int:
    """Move legacy timestamped PDFs into the canonical company/year path.

    This migration is idempotent and only operates on paths already pinned by
    the manifest and contained by ``CORPUS_ROOT``.
    """
    if not MANIFEST_PATH.exists():
        return 0
    moved = 0
    with _manifest_guard():
        manifest = load_manifest()
        for document in manifest["documents"]:
            old_path = _manifest_owned_path(str(document.get("local_path") or ""))
            company_slug = str(document.get("company_slug") or "").strip()
            fiscal_year = int(document.get("fiscal_year") or 0)
            filename = str(document.get("filename") or "").strip()
            if not old_path or not company_slug or not fiscal_year or not filename:
                continue
            target = (CORPUS_ROOT / company_slug / str(fiscal_year) / filename).resolve()
            if target == old_path:
                continue
            if not target.is_relative_to(CORPUS_ROOT.resolve()):
                continue
            if old_path.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                old_path.replace(target)
                _prune_empty_parents(old_path)
            elif not target.is_file():
                continue
            document["local_path"] = str(target.relative_to(Path.cwd().resolve())) if target.is_relative_to(Path.cwd().resolve()) else str(target)
            moved += 1
        if moved:
            _write_manifest(manifest)
    return moved


def upsert_document(document: dict[str, Any]) -> dict[str, Any]:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    with _manifest_guard():
        manifest = load_manifest()
        documents = manifest["documents"]
        superseded = [
            item for item in documents
            if item.get("sha256") == document.get("sha256")
            or (item.get("company_slug"), item.get("fiscal_year"))
            == (document.get("company_slug"), document.get("fiscal_year"))
        ]
        # A repeated crawl of the same bytes must not erase a human decision.
        # A changed SHA is a changed benchmark source and requires new review.
        same_source = next(
            (item for item in superseded if item.get("sha256") == document.get("sha256")),
            None,
        )
        if same_source and "verification" not in document and isinstance(same_source.get("verification"), dict):
            document["verification"] = same_source["verification"]
        documents[:] = [
            item for item in documents
            if item.get("sha256") != document.get("sha256")
            and (item.get("company_slug"), item.get("fiscal_year"))
            != (document.get("company_slug"), document.get("fiscal_year"))
        ]
        documents.append(document)
        documents.sort(key=lambda item: (str(item.get("company", "")).lower(), int(item.get("fiscal_year") or 0)))
        _write_manifest(manifest)

        # Commit the new manifest first, then remove only a superseded source
        # path owned by corpus storage. Historical extraction runs live outside
        # this tree and are never touched.
        new_paths = set(_document_owned_paths(document))
        for item in superseded:
            for old_path in _document_owned_paths(item):
                if old_path not in new_paths and old_path.is_file():
                    old_path.unlink()
                    _prune_empty_parents(old_path)
        return document


def find_document(document_id: str) -> dict[str, Any] | None:
    identifier = str(document_id or "").strip()
    return next(
        (item for item in load_manifest().get("documents", []) if str(item.get("sha256") or "") == identifier),
        None,
    )


def _read_json_owned(path_value: str) -> dict[str, Any] | None:
    path = _manifest_owned_path(path_value)
    if not path or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def verification_payload(document: dict[str, Any]) -> dict[str, Any]:
    """Return the review sheet tied to the document's current source hash."""
    is_assignment = (
        str(document.get("company_slug") or "").upper() == "3M"
        and int(document.get("fiscal_year") or 0) == 2022
        and str(document.get("sha256") or "") == ASSIGNMENT_GOLDEN_SOURCE_SHA256
    )
    if is_assignment:
        answers = GOLDEN_ANSWERS_STORE["2022"]
        return {
            "document_id": document.get("sha256"),
            "company": document.get("company"),
            "fiscal_year": document.get("fiscal_year"),
            "filename": document.get("filename"),
            "currency": str(document.get("currency") or "USD").upper(),
            "value_scale": "millions",
            "answer_unit": f"M {str(document.get('currency') or 'USD').upper()}",
            "status": "assignment_supplied",
            "authoritative_golden_set": True,
            "candidate_extracted": True,
            "extracted_row_count": len(ASSET_SCHEMA),
            "source_sha256": document.get("sha256"),
            "rows": [
                {**row, "answer_m_usd": answers.get(str(row["item"])), "confidence": 1.0, "source_page": None, "evidence": None}
                for row in ASSET_SCHEMA
            ],
        }

    audited = SOURCE_BOUND_GOLDEN_ANSWERS.get(str(document.get("sha256") or ""))
    if audited:
        document_identity = "".join(
            character for character in str(document.get("company") or "").casefold()
            if character.isalnum()
        )
        audited_identity = "".join(
            character for character in str(audited.get("company") or "").casefold()
            if character.isalnum()
        )
        same_source_identity = (
            document_identity == audited_identity
            and str(document.get("fiscal_year") or "") == str(audited.get("fiscal_year") or "")
            and str(document.get("currency") or "USD").upper()
            == str(audited.get("currency") or "USD").upper()
        )
        if same_source_identity:
            answers = dict(audited.get("answers") or {})
            citations = dict(audited.get("citations") or {})
            return {
                "document_id": document.get("sha256"),
                "company": document.get("company"),
                "fiscal_year": document.get("fiscal_year"),
                "filename": document.get("filename"),
                "currency": str(document.get("currency") or "USD").upper(),
                "value_scale": "millions",
                "answer_unit": f"M {str(document.get('currency') or 'USD').upper()}",
                "source_value_quantum": audited.get("source_value_quantum"),
                "status": "independently_verified",
                "authoritative_golden_set": True,
                "immutable": True,
                "candidate_extracted": True,
                "extracted_row_count": len(answers),
                "source_sha256": document.get("sha256"),
                "audit_passes": audited.get("audit_passes"),
                "unscorable_rows": audited.get("unscorable_rows") or [],
                "rows": [
                    {
                        **row,
                        "answer_m_usd": answers.get(str(row["item"])),
                        "confidence": 1.0 if str(row["item"]) in answers else None,
                        "source_page": (citations.get(str(row["item"])) or {}).get("page"),
                        "evidence": (citations.get(str(row["item"])) or {}).get("evidence"),
                    }
                    for row in ASSET_SCHEMA
                ],
            }

    verification = document.get("verification") if isinstance(document.get("verification"), dict) else {}
    status = str(verification.get("status") or "human_review_required")
    artifact = None
    if status == "human_verified":
        artifact = _read_json_owned(str(verification.get("approved_path") or ""))
    if artifact is None:
        artifact = _read_json_owned(str(verification.get("candidate_path") or ""))
        status = "human_review_required"
    artifact_rows = (artifact or {}).get("rows") or []
    candidate_extracted = isinstance(artifact_rows, list) and len(artifact_rows) == len(ASSET_SCHEMA)
    rows_by_item = {
        str(row.get("item") or ""): row
        for row in artifact_rows
        if isinstance(row, dict)
    }
    rows = []
    for schema_row in ASSET_SCHEMA:
        candidate = rows_by_item.get(str(schema_row["item"]), {})
        rows.append({
            **schema_row,
            "answer_m_usd": candidate.get("answer_m_usd"),
            "confidence": candidate.get("confidence"),
            "source_page": candidate.get("source_page"),
            "evidence": candidate.get("evidence"),
            "pass_values": candidate.get("pass_values"),
            "agreement_count": candidate.get("agreement_count"),
            "successful_passes": candidate.get("successful_passes"),
            "agreement_ratio": candidate.get("agreement_ratio"),
            "stability": candidate.get("stability"),
        })
    return {
        "document_id": document.get("sha256"),
        "company": document.get("company"),
        "fiscal_year": document.get("fiscal_year"),
        "filename": document.get("filename"),
        "currency": str(document.get("currency") or "USD").upper(),
        "value_scale": "millions",
        "answer_unit": f"M {str(document.get('currency') or 'USD').upper()}",
        "source_value_quantum": (artifact or {}).get("source_value_quantum"),
        "status": status,
        "authoritative_golden_set": status == "human_verified",
        "candidate_extracted": candidate_extracted,
        "extracted_row_count": len(artifact_rows) if isinstance(artifact_rows, list) else 0,
        "source_sha256": document.get("sha256"),
        "generated_at": verification.get("generated_at"),
        "approved_at": verification.get("approved_at"),
        "candidate_method": verification.get("candidate_method"),
        "consensus_summary": verification.get("consensus_summary"),
        "rows": rows,
    }


def approve_document_answers(document_id: str, rows: list[dict[str, Any]], *, reviewer: str = "human") -> dict[str, Any]:
    """Save an exact 27-row human-approved key bound to the current PDF SHA."""
    expected_items = [str(row["item"]) for row in ASSET_SCHEMA]
    if len(rows) != len(expected_items) or [str(row.get("item") or "") for row in rows] != expected_items:
        raise ValueError("Approval must contain the 27 schema rows in canonical order.")
    normalized_rows = []
    for schema_row, row in zip(ASSET_SCHEMA, rows):
        answer = row.get("answer_m_usd")
        if answer is None or answer == "":
            normalized_answer = None
        elif isinstance(answer, bool):
            raise ValueError(f"{schema_row['item']} must be numeric or blank.")
        else:
            try:
                normalized_answer = float(answer)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{schema_row['item']} must be numeric or blank.") from exc
        normalized_rows.append({
            **schema_row,
            "answer_m_usd": normalized_answer,
            "confidence": row.get("confidence"),
            "source_page": row.get("source_page"),
            "evidence": row.get("evidence"),
        })

    with _manifest_guard():
        manifest = load_manifest()
        document = next(
            (item for item in manifest["documents"] if str(item.get("sha256") or "") == str(document_id)),
            None,
        )
        if document is None:
            raise KeyError("Corpus document not found.")
        pdf_path = _manifest_owned_path(str(document.get("local_path") or ""))
        if not pdf_path or not pdf_path.is_file():
            raise ValueError("The source PDF is missing from corpus storage.")
        approved_at = datetime.now(timezone.utc).isoformat()
        verification_dir = pdf_path.parent / "verification"
        verification_dir.mkdir(parents=True, exist_ok=True)
        approved_path = verification_dir / "approved_answers.json"
        artifact = {
            "status": "human_verified",
            "authoritative_golden_set": True,
            "pdf_sha256": document.get("sha256"),
            "approved_at": approved_at,
            "reviewer": str(reviewer or "human"),
            "currency": str(document.get("currency") or "USD").upper(),
            "value_scale": "millions",
            "rows": normalized_rows,
        }
        temporary = approved_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(approved_path)
        current = document.get("verification") if isinstance(document.get("verification"), dict) else {}
        document["verification"] = {
            **current,
            "status": "human_verified",
            "source_sha256": document.get("sha256"),
            "approved_path": str(approved_path),
            "approved_at": approved_at,
        }
        _write_manifest(manifest)
        return verification_payload(document)


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

    with _manifest_guard():
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

        owned_paths = _document_owned_paths(document)
        file_removed = pdf_path.is_file()
        for owned_path in reversed(owned_paths):
            if owned_path.is_file():
                owned_path.unlink()
                _prune_empty_parents(owned_path)

        documents[:] = [item for item in documents if str(item.get("sha256") or "") != identifier]
        _write_manifest(manifest)
        return {**document, "file_removed": file_removed}
