"""Restore only exact, audited corpus PDFs from a recoverable backup.

The backup may contain failed discovery candidates, provisional review files,
or benchmark controls.  This utility admits only the assignment-supplied 3M
FY2022 source and SHA-bound gold for companies in the Bakuraku registry.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tarfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schema import ASSIGNMENT_GOLDEN_SOURCE_SHA256, SOURCE_BOUND_GOLDEN_ANSWERS


def normalized_identity(value: object) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", str(value or "")).casefold()
        if character.isalnum()
    )


def bakuraku_identities(registry_path: Path) -> set[str]:
    with registry_path.open(encoding="utf-8", newline="") as handle:
        return {
            normalized_identity(row.get("company_name"))
            for row in csv.DictReader(handle)
            if normalized_identity(row.get("company_name"))
        }


def _manifest_member(archive: tarfile.TarFile) -> tarfile.TarInfo:
    matches = [
        member
        for member in archive.getmembers()
        if member.isfile() and PurePosixPath(member.name).as_posix().endswith(
            "corpus_dataset/corpus_manifest.json"
        )
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one corpus manifest in backup, found {len(matches)}.")
    return matches[0]


def _pdf_member(archive: tarfile.TarFile, document: dict[str, Any]) -> tarfile.TarInfo:
    local_path = PurePosixPath(str(document.get("local_path") or "")).as_posix().lstrip("/")
    filename = str(document.get("filename") or "").strip()
    matches = []
    for member in archive.getmembers():
        if not member.isfile() or not member.name.lower().endswith(".pdf"):
            continue
        member_path = PurePosixPath(member.name).as_posix().lstrip("/")
        if member_path == local_path or member_path.endswith(f"/{local_path}"):
            matches.append(member)
        elif filename and PurePosixPath(member_path).name == filename:
            expected_suffix = PurePosixPath(local_path).parent.as_posix()
            if member_path.endswith(f"{expected_suffix}/{filename}"):
                matches.append(member)
    unique = {member.name: member for member in matches}
    if len(unique) != 1:
        raise ValueError(
            f"Expected one archived PDF for {document.get('company')} FY{document.get('fiscal_year')}, "
            f"found {len(unique)}."
        )
    return next(iter(unique.values()))


def _audited_document(
    document: dict[str, Any], allowed_companies: set[str]
) -> bool:
    source_hash = str(document.get("sha256") or "")
    company = normalized_identity(document.get("company"))
    year = str(document.get("fiscal_year") or "")
    currency = str(document.get("currency") or "USD").upper()
    if source_hash == ASSIGNMENT_GOLDEN_SOURCE_SHA256:
        return company == "3m" and year == "2022" and currency == "USD"
    if company not in allowed_companies:
        return False
    audited = SOURCE_BOUND_GOLDEN_ANSWERS.get(source_hash)
    return bool(
        audited
        and company == normalized_identity(audited.get("company"))
        and year == str(audited.get("fiscal_year") or "")
        and currency == str(audited.get("currency") or "USD").upper()
    )


def restore_verified_corpus(
    *, archive_path: Path, corpus_root: Path, registry_path: Path, dry_run: bool = False
) -> dict[str, Any]:
    allowed_companies = bakuraku_identities(registry_path)
    manifest_path = corpus_root / "corpus_manifest.json"
    existing = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {"version": 1, "documents": []}
    )
    restored: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    with tarfile.open(archive_path, "r:gz") as archive:
        manifest_stream = archive.extractfile(_manifest_member(archive))
        if manifest_stream is None:
            raise ValueError("Could not read the archived corpus manifest.")
        archived = json.load(manifest_stream)
        for document in archived.get("documents", []):
            if not isinstance(document, dict) or not _audited_document(document, allowed_companies):
                skipped.append({
                    "company": document.get("company") if isinstance(document, dict) else None,
                    "fiscal_year": document.get("fiscal_year") if isinstance(document, dict) else None,
                    "reason": "not an exact Bakuraku-client or assignment gold source",
                })
                continue
            member = _pdf_member(archive, document)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read {member.name} from backup.")
            payload = source.read()
            actual_hash = hashlib.sha256(payload).hexdigest()
            if actual_hash != str(document.get("sha256") or ""):
                raise ValueError(f"SHA-256 mismatch for archived {member.name}.")

            company_folder = str(document.get("company_slug") or document.get("company") or "").strip()
            year = int(document.get("fiscal_year") or 0)
            filename = str(document.get("filename") or PurePosixPath(member.name).name)
            if not company_folder or year <= 0 or Path(filename).name != filename:
                raise ValueError(f"Unsafe corpus identity in archived {member.name}.")
            target = corpus_root / company_folder / str(year) / filename
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + ".tmp")
                temporary.write_bytes(payload)
                os.chmod(temporary, 0o640)
                temporary.replace(target)
            restored.append({
                **document,
                "local_path": str(target),
                "size_bytes": len(payload),
                "verification": None,
            })

    merged = {
        (
            normalized_identity(document.get("company")),
            int(document.get("fiscal_year") or 0),
        ): document
        for document in existing.get("documents", [])
        if isinstance(document, dict)
    }
    for document in restored:
        merged[(normalized_identity(document.get("company")), int(document["fiscal_year"]))] = document
    documents = sorted(
        merged.values(),
        key=lambda document: (
            0 if normalized_identity(document.get("company")) == "3m" else 1,
            normalized_identity(document.get("company")),
            int(document.get("fiscal_year") or 0),
        ),
    )
    output = {
        "version": max(1, int(existing.get("version") or 1)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
    }
    if not dry_run:
        corpus_root.mkdir(parents=True, exist_ok=True)
        temporary_manifest = manifest_path.with_suffix(".json.tmp")
        temporary_manifest.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.chmod(temporary_manifest, 0o640)
        temporary_manifest.replace(manifest_path)
    return {
        "restored_documents": len(restored),
        "restored_companies": len({normalized_identity(item.get("company")) for item in restored}),
        "skipped_documents": len(skipped),
        "documents": restored,
        "manifest": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = restore_verified_corpus(
        archive_path=args.archive,
        corpus_root=args.corpus_root,
        registry_path=args.registry,
        dry_run=args.dry_run,
    )
    print(json.dumps({key: value for key, value in result.items() if key not in {"documents", "manifest"}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
