"""Durability checks for browser-rehydratable extraction jobs."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class ExtractionJobPersistenceTests(unittest.TestCase):
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
