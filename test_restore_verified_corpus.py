from __future__ import annotations

import io
import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import deploy.aws.restore_verified_corpus as restore_module
from schema import ASSIGNMENT_GOLDEN_SOURCE_SHA256


class RestoreVerifiedCorpusTests(unittest.TestCase):
    def test_rejects_an_archived_pdf_whose_bytes_do_not_match_gold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "backup.tar.gz"
            registry = root / "customers.csv"
            registry.write_text("company_name\n3M\n", encoding="utf-8")
            pdf_bytes = b"not-the-real-assignment-pdf"
            document = {
                "company": "3M",
                "company_slug": "3M",
                "fiscal_year": 2022,
                "currency": "USD",
                "filename": "3M_annual_report_2022.pdf",
                "local_path": "corpus_dataset/3M/2022/3M_annual_report_2022.pdf",
                "sha256": ASSIGNMENT_GOLDEN_SOURCE_SHA256,
                "screened": "ok",
            }
            invalid = {**document, "company": "Random Control", "company_slug": "Random", "fiscal_year": 2023}
            manifest = json.dumps({"version": 1, "documents": [document, invalid]}).encode()
            with tarfile.open(archive_path, "w:gz") as archive:
                manifest_info = tarfile.TarInfo("corpus_dataset/corpus_manifest.json")
                manifest_info.size = len(manifest)
                archive.addfile(manifest_info, io.BytesIO(manifest))
                pdf_info = tarfile.TarInfo(document["local_path"])
                pdf_info.size = len(pdf_bytes)
                archive.addfile(pdf_info, io.BytesIO(pdf_bytes))

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                restore_module.restore_verified_corpus(
                    archive_path=archive_path,
                    corpus_root=root / "corpus",
                    registry_path=registry,
                )

    def test_restores_only_registry_company_gold_and_puts_3m_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "backup.tar.gz"
            registry = root / "customers.csv"
            registry.write_text("company_name\nBakuraku Client\n", encoding="utf-8")
            corpus_root = root / "corpus"
            corpus_root.mkdir()
            (corpus_root / "corpus_manifest.json").write_text(json.dumps({
                "version": 1,
                "documents": [{
                    "company": "3M",
                    "company_slug": "3M",
                    "fiscal_year": 2022,
                    "sha256": ASSIGNMENT_GOLDEN_SOURCE_SHA256,
                    "currency": "USD",
                }],
            }), encoding="utf-8")
            client_bytes = b"%PDF-client"
            client_hash = hashlib.sha256(client_bytes).hexdigest()
            control_bytes = b"%PDF-control"
            control_hash = hashlib.sha256(control_bytes).hexdigest()
            client = {
                "company": "Bakuraku Client",
                "company_slug": "Bakuraku_Client",
                "fiscal_year": 2022,
                "currency": "JPY",
                "filename": "client.pdf",
                "local_path": "corpus_dataset/Bakuraku_Client/2022/client.pdf",
                "sha256": client_hash,
                "screened": "ok",
            }
            control = {
                **client,
                "company": "Random Control",
                "company_slug": "Random_Control",
                "filename": "control.pdf",
                "local_path": "corpus_dataset/Random_Control/2022/control.pdf",
                "sha256": control_hash,
            }
            manifest = json.dumps({"version": 1, "documents": [control, client]}).encode()
            with tarfile.open(archive_path, "w:gz") as archive:
                manifest_info = tarfile.TarInfo("corpus_dataset/corpus_manifest.json")
                manifest_info.size = len(manifest)
                archive.addfile(manifest_info, io.BytesIO(manifest))
                for document, payload in ((control, control_bytes), (client, client_bytes)):
                    pdf_info = tarfile.TarInfo(document["local_path"])
                    pdf_info.size = len(payload)
                    archive.addfile(pdf_info, io.BytesIO(payload))

            audit = {
                client_hash: {
                    "company": "Bakuraku Client",
                    "fiscal_year": "2022",
                    "currency": "JPY",
                    "answers": {},
                },
                control_hash: {
                    "company": "Random Control",
                    "fiscal_year": "2022",
                    "currency": "JPY",
                    "answers": {},
                },
            }
            with patch.object(restore_module, "SOURCE_BOUND_GOLDEN_ANSWERS", audit):
                result = restore_module.restore_verified_corpus(
                    archive_path=archive_path,
                    corpus_root=corpus_root,
                    registry_path=registry,
                )

            self.assertEqual(1, result["restored_documents"])
            self.assertEqual("3M", result["manifest"]["documents"][0]["company"])
            self.assertEqual("Bakuraku Client", result["manifest"]["documents"][1]["company"])
            self.assertTrue((root / "corpus/Bakuraku_Client/2022/client.pdf").is_file())
            self.assertFalse((root / "corpus/Random_Control/2022/control.pdf").exists())


if __name__ == "__main__":
    unittest.main()
