"""Durability checks for browser-rehydratable extraction jobs."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import server


class ExtractionJobPersistenceTests(unittest.TestCase):
    def test_corpus_page_preview_renders_one_exact_pdf_page(self):
        import fitz

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "report.pdf"
            with fitz.open() as pdf:
                page = pdf.new_page(width=595, height=842)
                page.insert_text((72, 72), "Consolidated Balance Sheet")
                pdf.save(pdf_path)
            document = {
                "sha256": "a" * 64,
                "filename": "report.pdf",
                "local_path": str(pdf_path),
            }
            with patch.object(server, "CORPUS_ROOT", root), patch.object(
                server, "find_document", return_value=document
            ):
                response = server.app.test_client().get(
                    f"/api/corpus/{document['sha256']}/pages/1.png"
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "image/png")
            self.assertTrue(response.data.startswith(b"\x89PNG"))

    def test_start_route_runs_backend_owned_job_and_persists_replay(self):
        prediction = {
            "run_id": "S1_test", "fiscal_year": "2022", "page_count": 10,
            "approx_input_tokens": 1000, "api_elapsed_seconds": 0.2,
            "extract_seconds": 0.1, "total_seconds": 0.3,
            "metrics": {"accuracy": 1.0, "coverage": 1.0, "consistency": 1.0},
            "warnings": [], "contract_repairs": [],
        }
        staged = {
            "id": "upload-1", "name": "3M_annual_report_2022.pdf",
            "path": "/tmp/test.pdf", "pages": 10, "approx_tokens": 1000,
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "EXTRACTION_JOBS_ROOT", Path(temp_dir)
        ), patch.object(server, "current_settings", return_value={
            "api_key": "test", "max_concurrency": 1, "auto_concurrency": False,
            "temperature": 0.1, "enable_reasoning": False,
        }), patch.dict(server.STAGED, {"upload-1": staged}, clear=True), patch.object(
            server, "run_pipeline", return_value=prediction
        ):
            response = server.app.test_client().post("/api/extraction/jobs", json={
                "upload_ids": ["upload-1"], "strategies": ["s1"],
            })
            self.assertEqual(response.status_code, 202)
            job_id = response.get_json()["job_id"]
            persisted = None
            for _ in range(50):
                persisted = server.app.test_client().get(f"/api/extraction/jobs/{job_id}").get_json()
                if persisted["status"] in {"complete", "failed"}:
                    break
                time.sleep(0.01)

            self.assertIsNotNone(persisted)
            self.assertEqual(persisted["status"], "complete")
            self.assertEqual(persisted["succeeded"], 1)
            self.assertEqual(persisted["failed"], 0)
            self.assertEqual(
                [event["event"] for event in persisted["events"]],
                ["batch_start", "pass_start", "file_done", "file_complete", "batch_done"],
            )

    def test_state_and_event_offsets_survive_independent_requests(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "EXTRACTION_JOBS_ROOT", Path(temp_dir)
        ):
            job_id = "a" * 16
            server._write_extraction_job_state(job_id, {
                "id": job_id,
                "status": "running",
                "scope": "s2",
                "strategies": ["s1", "s2"],
                "files_total": 6,
                "passes_total": 12,
                "succeeded": 1,
                "failed": 0,
            })
            server._append_extraction_event(job_id, "batch_start", {"files_total": 6})
            server._append_extraction_event(job_id, "file_done", {"run_id": "run-1"})

            first, first_offset = server._read_extraction_events(job_id, 0)
            second, second_offset = server._read_extraction_events(job_id, 1)

            self.assertEqual([item["event"] for item in first], ["batch_start", "file_done"])
            self.assertEqual([item["event"] for item in second], ["file_done"])
            self.assertEqual(first_offset, 2)
            self.assertEqual(second_offset, 2)
            self.assertEqual(server._read_extraction_job_state(job_id)["status"], "running")

    def test_corpus_job_passes_source_company_year_and_currency_to_pipeline(self):
        prediction = {
            "run_id": "S2_test", "fiscal_year": "2022", "page_count": 10,
            "approx_input_tokens": 1000, "api_elapsed_seconds": 0.2,
            "extract_seconds": 0.1, "total_seconds": 0.3,
            "metrics": {"accuracy": None, "coverage": 100.0, "consistency": 100.0},
            "warnings": [], "contract_repairs": [],
        }
        staged = {
            "id": "corpus-1", "name": "note_annual_report_2022.pdf",
            "path": "/tmp/note.pdf", "pages": 10, "approx_tokens": 1000,
            "source": "corpus", "company": "note株式会社", "fiscal_year": 2022,
            "currency": "JPY",
        }
        pipeline_mock = Mock(return_value=prediction)
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "EXTRACTION_JOBS_ROOT", Path(temp_dir)
        ), patch.object(server, "current_settings", return_value={
            "api_key": "test", "max_concurrency": 1, "auto_concurrency": False,
            "temperature": 0.0, "enable_reasoning": False,
        }), patch.dict(server.STAGED, {"corpus-1": staged}, clear=True), patch.object(
            server, "run_pipeline", pipeline_mock
        ):
            response = server.app.test_client().post("/api/extraction/jobs", json={
                "upload_ids": ["corpus-1"], "strategies": ["s2"],
            })
            self.assertEqual(response.status_code, 202)
            job_id = response.get_json()["job_id"]
            for _ in range(50):
                state = server.app.test_client().get(f"/api/extraction/jobs/{job_id}").get_json()
                if state["status"] in {"complete", "failed"}:
                    break
                time.sleep(0.01)

            call = pipeline_mock.call_args.kwargs
            self.assertEqual(call["company_hint"], "note株式会社")
            self.assertEqual(call["fiscal_year_hint"], "2022")
            self.assertEqual(call["output_currency"], "JPY")

    def test_job_route_replays_only_unseen_events(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "EXTRACTION_JOBS_ROOT", Path(temp_dir)
        ):
            job_id = "b" * 16
            server._write_extraction_job_state(job_id, {
                "id": job_id,
                "status": "complete",
                "scope": "s1",
                "strategies": ["s1"],
                "files_total": 1,
                "passes_total": 1,
                "succeeded": 1,
                "failed": 0,
            })
            server._append_extraction_event(job_id, "batch_start", {})
            server._append_extraction_event(job_id, "batch_done", {"succeeded": 1})

            response = server.app.test_client().get(f"/api/extraction/jobs/{job_id}?after=1")
            payload = response.get_json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(payload["next_offset"], 2)
            self.assertEqual([item["event"] for item in payload["events"]], ["batch_done"])


if __name__ == "__main__":
    unittest.main()
