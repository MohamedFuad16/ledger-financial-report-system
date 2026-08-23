"""Rename corpus folders/files to uniform English slugs and update the manifest.

Idempotent: documents already stored under their English slug are skipped.
Content bytes never change, so every SHA-256 binding survives; after moving,
each file is re-hashed and must still match its manifest hash or the script
aborts before writing the manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from corpus.company_names import english_slug  # noqa: E402

MANIFEST = PROJECT_ROOT / "corpus_dataset" / "corpus_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    moved = skipped = 0
    for document in manifest.get("documents", []):
        slug = english_slug(document.get("company"))
        if not slug:
            print(f"SKIP unmapped company: {document.get('company')}")
            skipped += 1
            continue
        old_path = PROJECT_ROOT / str(document["local_path"])
        old_name = str(document["filename"])
        kind = "statutory_report" if "statutory_report" in old_name else "annual_report"
        new_name = f"{slug}_{kind}_{document['fiscal_year']}.pdf"
        new_rel = f"corpus_dataset/{slug}/{document['fiscal_year']}/{new_name}"
        new_path = PROJECT_ROOT / new_rel
        if str(document["local_path"]) == new_rel and new_path.is_file():
            skipped += 1
            continue
        if not old_path.is_file():
            # A host that pulled the migrated manifest still holds its file
            # under the legacy Unicode slug; reconstruct that location.
            legacy_slug = re.sub(r"[^\w-]+", "_", str(document["company"]), flags=re.UNICODE).strip("_")
            legacy_path = (
                PROJECT_ROOT / "corpus_dataset" / legacy_slug / str(document["fiscal_year"])
                / f"{legacy_slug}_{kind}_{document['fiscal_year']}.pdf"
            )
            if legacy_path.is_file():
                old_path = legacy_path
            elif new_path.is_file() and sha256(new_path) == document["sha256"]:
                # File was moved in an earlier run; only the manifest lagged.
                old_path = new_path
            else:
                raise SystemExit(f"Missing source file for {document['company']} FY{document['fiscal_year']}: {old_path}")
        if old_path != new_path:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.replace(new_path)
        if sha256(new_path) != document["sha256"]:
            raise SystemExit(f"SHA changed while moving {new_rel}; aborting before manifest write.")
        # Update every path-bearing field, including any review artifacts.
        old_rel = str(document["local_path"])
        for key, value in list(document.items()):
            if isinstance(value, str) and old_rel in value:
                document[key] = value.replace(old_rel, new_rel)
            elif isinstance(value, dict):
                for inner_key, inner_value in list(value.items()):
                    if isinstance(inner_value, str) and old_rel.rsplit("/", 1)[0] in inner_value:
                        value[inner_key] = inner_value.replace(old_rel.rsplit("/", 1)[0], new_rel.rsplit("/", 1)[0])
        document["company_slug"] = slug
        document["local_path"] = new_rel
        document["filename"] = new_name
        # Drain the now-empty old directories.
        try:
            old_year_dir = old_path.parent
            if old_year_dir.is_dir() and not any(old_year_dir.iterdir()):
                old_year_dir.rmdir()
            old_company_dir = old_year_dir.parent
            if old_company_dir.is_dir() and not any(old_company_dir.iterdir()):
                old_company_dir.rmdir()
        except OSError:
            pass
        moved += 1
        print(f"MOVED {document['company']} FY{document['fiscal_year']} -> {new_rel}")

    temporary = MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(MANIFEST)
    print(f"moved={moved} already-uniform={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
