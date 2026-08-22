"""Safety checks for pinned corpus deletion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import corpus.manifest as manifest_module
import corpus.fetch as fetch_module
from schema import ASSET_SCHEMA


class CorpusManifestTests(unittest.TestCase):
    def test_source_bound_audit_is_immutable_native_currency_gold(self):
        document_hash, audited = next(
            (source_hash, item)
            for source_hash, item in manifest_module.SOURCE_BOUND_GOLDEN_ANSWERS.items()
            if item.get("currency") == "JPY"
        )
        document = {
            "sha256": document_hash,
            "company": audited["company"],
            "company_slug": audited["company"],
            "fiscal_year": int(audited["fiscal_year"]),
            "filename": "audited_annual_report_2022.pdf",
            "currency": audited["currency"],
        }

        verification = manifest_module.verification_payload(document)

        self.assertEqual("independently_verified", verification["status"])
        self.assertTrue(verification["authoritative_golden_set"])
        self.assertTrue(verification["immutable"])
        self.assertEqual("JPY", verification["currency"])
        self.assertEqual("M JPY", verification["answer_unit"])
        self.assertEqual(27, len(verification["rows"]))
        self.assertEqual(len(audited["answers"]), verification["extracted_row_count"])

    def test_japanese_company_slugs_remain_distinct_and_path_safe(self):
        first = fetch_module.company_slug("ダイニチ工業株式会社")
        second = fetch_module.company_slug("リソルホールディングス株式会社")

        self.assertNotEqual(first, second)
        self.assertNotEqual("Unknown_Company", first)
        self.assertNotIn("/", first)
        self.assertNotIn("..", first)

    def test_fetch_rejects_screening_review_before_replacing_canonical_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            current = root / "Example" / "2022" / "Example_annual_report_2022.pdf"
            current.parent.mkdir(parents=True)
            current.write_bytes(b"%PDF-current")

            def fake_download(_url, target):
                target.write_bytes(b"%PDF-news-release")
                return "f" * 64, target.stat().st_size

            with patch.object(fetch_module, "CORPUS_ROOT", root), patch.object(
                fetch_module, "_download", side_effect=fake_download
            ), patch.object(fetch_module, "screen_pdf", return_value={
                "screened": "review",
                "screen_reasons": ["No balance sheet heading found."],
            }), patch.object(fetch_module, "upsert_document") as upsert:
                with self.assertRaisesRegex(ValueError, "failed Annual Report screening"):
                    fetch_module.fetch_report({
                        "company": "Example",
                        "year": 2022,
                        "url": "https://example.test/release_2022.pdf",
                    })

            self.assertEqual(b"%PDF-current", current.read_bytes())
            self.assertEqual([], list(current.parent.glob(".*.pdf")))
            upsert.assert_not_called()

    def test_fetch_rejects_an_audited_source_hash_mismatch_before_screening(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"

            def fake_download(_url, target):
                target.write_bytes(b"%PDF-changed")
                return "f" * 64, target.stat().st_size

            with patch.object(fetch_module, "CORPUS_ROOT", root), patch.object(
                fetch_module, "_download", side_effect=fake_download
            ), patch.object(fetch_module, "screen_pdf") as screen, patch.object(
                fetch_module, "upsert_document"
            ) as upsert:
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    fetch_module.fetch_report({
                        "company": "Example",
                        "year": 2022,
                        "url": "https://example.test/annual_report_2022.pdf",
                        "expected_sha256": "a" * 64,
                    })

            screen.assert_not_called()
            upsert.assert_not_called()
            self.assertFalse(any(root.rglob("*.pdf")))

    def test_upsert_replaces_same_company_year_and_removes_superseded_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            legacy = root / "3M" / "2022" / "stamp" / "3M_annual_report_2022.pdf"
            current = root / "3M" / "2022" / "3M_annual_report_2022.pdf"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"%PDF-legacy")
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_bytes(b"%PDF-current")

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ):
                manifest_module.upsert_document({
                    "sha256": "a" * 64,
                    "company": "3M",
                    "company_slug": "3M",
                    "fiscal_year": 2022,
                    "filename": legacy.name,
                    "local_path": str(legacy),
                })
                manifest_module.upsert_document({
                    "sha256": "b" * 64,
                    "company": "3M",
                    "company_slug": "3M",
                    "fiscal_year": 2022,
                    "filename": current.name,
                    "local_path": str(current),
                })

                documents = manifest_module.load_manifest()["documents"]
                self.assertEqual([item["sha256"] for item in documents], ["b" * 64])
                self.assertFalse(legacy.exists())
                self.assertTrue(current.exists())

    def test_migration_moves_timestamped_pdf_to_canonical_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            legacy = root / "3M" / "2022" / "stamp" / "3M_annual_report_2022.pdf"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"%PDF-test")

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ):
                manifest_module.upsert_document({
                    "sha256": "c" * 64,
                    "company": "3M",
                    "company_slug": "3M",
                    "fiscal_year": 2022,
                    "filename": legacy.name,
                    "local_path": str(legacy),
                })
                self.assertEqual(manifest_module.migrate_corpus_layout(), 1)
                migrated = root / "3M" / "2022" / legacy.name
                self.assertTrue(migrated.exists())
                self.assertFalse(legacy.exists())
                self.assertEqual(Path(manifest_module.load_manifest()["documents"][0]["local_path"]).resolve(), migrated.resolve())

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

    def test_candidate_answers_are_pinned_as_non_authoritative_and_deleted_with_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            pdf_path = root / "Example" / "2024" / "Example_annual_report_2024.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-test")
            document = {
                "sha256": "d" * 64,
                "company": "Example",
                "company_slug": "Example",
                "fiscal_year": 2024,
                "filename": pdf_path.name,
                "local_path": str(pdf_path),
                "source_url": "https://example.com/report.pdf",
                "currency": "JPY",
            }

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ), patch.object(fetch_module, "CORPUS_ROOT", root), patch.object(
                fetch_module, "upsert_document", side_effect=manifest_module.upsert_document
            ):
                manifest_module.upsert_document(document)
                pinned = fetch_module.pin_candidate_answers(document, {
                    "mode": "auto",
                    "detected_fiscal_year": 2024,
                    "rows": [{
                        "item": "Current Assets",
                        "answer_m_usd": 123.0,
                        "confidence": 0.7,
                        "source_page": 10,
                        "evidence": "Total current assets 123",
                    }],
                    "metadata": {"pages": 1},
                })
                candidate_path = Path(pinned["verification"]["candidate_path"])
                candidate = fetch_module.json.loads(candidate_path.read_text(encoding="utf-8"))

                self.assertTrue(candidate_path.is_file())
                self.assertEqual("human_review_required", pinned["verification"]["status"])
                self.assertFalse(candidate["authoritative_golden_set"])
                self.assertEqual(27, len(candidate["rows"]))
                self.assertEqual(123.0, candidate["rows"][0]["answer_m_usd"])
                review = manifest_module.verification_payload(pinned)
                self.assertTrue(review["candidate_extracted"])
                self.assertEqual(27, review["extracted_row_count"])
                self.assertEqual("JPY", review["currency"])
                self.assertEqual("M JPY", review["answer_unit"])

                manifest_module.delete_pinned_document(document["sha256"])
                self.assertFalse(pdf_path.exists())
                self.assertFalse(candidate_path.exists())

    def test_multi_pass_candidates_prefill_a_non_authoritative_consensus(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            pdf_path = root / "Example" / "2024" / "Example_annual_report_2024.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-test")
            document = {
                "sha256": "9" * 64,
                "company": "Example",
                "company_slug": "Example",
                "fiscal_year": 2024,
                "filename": pdf_path.name,
                "local_path": str(pdf_path),
                "source_url": "https://example.com/report.pdf",
            }
            passes = [{
                "mode": "auto",
                "detected_fiscal_year": 2024,
                "rows": [{
                    "item": row["item"],
                    "answer_m_usd": 100.0 + pass_number if index == 0 else None,
                    "confidence": 0.9,
                    "source_page": 10,
                    "evidence": "Extracted from the PDF",
                } for index, row in enumerate(ASSET_SCHEMA)],
            } for pass_number in (0, 0, 1)]

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ), patch.object(fetch_module, "CORPUS_ROOT", root), patch.object(
                fetch_module, "upsert_document", side_effect=manifest_module.upsert_document
            ):
                manifest_module.upsert_document(document)
                pinned = fetch_module.pin_candidate_answers(document, passes, requested_passes=3)
                review = manifest_module.verification_payload(pinned)

            self.assertEqual("human_review_required", review["status"])
            self.assertTrue(review["candidate_extracted"])
            self.assertFalse(review["authoritative_golden_set"])
            self.assertEqual(100.0, review["rows"][0]["answer_m_usd"])
            self.assertEqual(2, review["rows"][0]["agreement_count"])
            self.assertEqual("stable", review["rows"][0]["stability"])
            self.assertEqual(3, review["consensus_summary"]["requested_passes"])

    def test_human_approval_is_sha_bound_and_does_not_survive_changed_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus_dataset"
            pdf_path = root / "Example" / "2024" / "Example_annual_report_2024.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-first")
            original = {
                "sha256": "e" * 64,
                "company": "Example",
                "company_slug": "Example",
                "fiscal_year": 2024,
                "filename": pdf_path.name,
                "local_path": str(pdf_path),
            }
            rows = [{**row, "answer_m_usd": index} for index, row in enumerate(ASSET_SCHEMA)]

            with patch.object(manifest_module, "CORPUS_ROOT", root), patch.object(
                manifest_module, "MANIFEST_PATH", root / "corpus_manifest.json"
            ):
                manifest_module.upsert_document(original)
                approved = manifest_module.approve_document_answers(original["sha256"], rows)
                self.assertEqual("human_verified", approved["status"])
                approved_path = Path(
                    manifest_module.find_document(original["sha256"])["verification"]["approved_path"]
                )
                self.assertTrue(approved_path.is_file())

                pdf_path.write_bytes(b"%PDF-replacement")
                replacement = {**original, "sha256": "f" * 64}
                manifest_module.upsert_document(replacement)

                current = manifest_module.find_document(replacement["sha256"])
                self.assertNotIn("verification", current)
                self.assertEqual("human_review_required", manifest_module.verification_payload(current)["status"])
                self.assertFalse(approved_path.exists())


if __name__ == "__main__":
    unittest.main()
