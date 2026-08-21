"""Safety checks for pinned corpus deletion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import corpus.manifest as manifest_module


class CorpusManifestTests(unittest.TestCase):
    def test_delete_removes_only_the_pinned_pdf_and_manifest_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            pdf_path = root / "3m" / "2022" / "20260821T000000Z" / "3M_annual_report_2022.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-test")
            preserved_run = Path(temp_dir) / "runs" / "3m" / "FY2022" / "run-1" / "prediction.json"
            preserved_run.parent.mkdir(parents=True)
            preserved_run.write_text("{}", encoding="utf-8")
            document = {
                "sha256": "a" * 64,
                "company": "3M",
                "company_slug": "3m",
                "fiscal_year": 2022,
                "filename": pdf_path.name,
                "local_path": str(pdf_path),
            }

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ):
                manifest_module.upsert_document(document)
                deleted = manifest_module.delete_pinned_document(document["sha256"])

                self.assertEqual(deleted["filename"], pdf_path.name)
                self.assertTrue(deleted["file_removed"])
                self.assertFalse(pdf_path.exists())
                self.assertTrue(preserved_run.exists())
                self.assertEqual(manifest_module.load_manifest()["documents"], [])

    def test_delete_refuses_a_manifest_path_outside_corpus_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            outside = Path(temp_dir) / "must-not-delete.pdf"
            outside.write_bytes(b"keep")
            document = {
                "sha256": "b" * 64,
                "company": "Example",
                "company_slug": "example",
                "fiscal_year": 2022,
                "filename": outside.name,
                "local_path": str(outside),
            }

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ):
                manifest_module.upsert_document(document)
                with self.assertRaisesRegex(ValueError, "outside corpus storage"):
                    manifest_module.delete_pinned_document(document["sha256"])

            self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
