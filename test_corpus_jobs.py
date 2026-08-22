"""Durability checks for browser-rehydratable corpus discovery jobs."""

from __future__ import annotations

import tempfile
import time
import unittest
import os
from pathlib import Path
from unittest.mock import patch

import server


class CorpusJobPersistenceTests(unittest.TestCase):
    def test_live_job_owned_by_another_gunicorn_process_stays_visible(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "CORPUS_JOBS_ROOT", Path(temp_dir)
        ):
            job_id = "b" * 12
            server._write_corpus_job_state(job_id, {
                "id": job_id,
                "status": "running",
                "worker_instance_id": "another-gunicorn-process",
                "worker_pid": os.getpid(),
                "events": [],
            })

            state = server._read_corpus_job_state(job_id)

            self.assertEqual("running", state["status"])
            self.assertNotIn("error", state)

    def test_completed_job_survives_loss_of_process_memory(self):
        def build(
            _companies,
            years,
            *,
            api_key,
            max_downloads,
            on_event,
            deep_search=False,
        ):
            self.assertEqual("test-firecrawl", api_key)
            self.assertEqual([2024], years)
            self.assertFalse(deep_search)
            on_event({"type": "discovered", "company": "Example"})
            return {"requested": 1, "downloaded": [], "failed": [], "years": years}

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "CORPUS_JOBS_ROOT", Path(temp_dir)
        ), patch.object(server, "current_settings", return_value={
            "firecrawl_api_key": "test-firecrawl", "max_concurrency": 1,
        }), patch.object(server, "build_corpus", side_effect=build), patch.dict(
            server.CORPUS_JOBS, {}, clear=True
        ):
            response = server.app.test_client().post("/api/corpus/jobs", json={
                "companies": [{"name": "Example", "official_url": "https://example.com"}],
                "years": [2024],
            })
            self.assertEqual(202, response.status_code)
            job_id = response.get_json()["job_id"]
            state = None
            for _ in range(50):
                state = server._read_corpus_job_state(job_id)
                if state and state["status"] == "complete":
                    break
                time.sleep(0.01)

            server.CORPUS_JOBS.clear()
            detail = server.app.test_client().get(f"/api/corpus/jobs/{job_id}")
            listing = server.app.test_client().get("/api/corpus/jobs").get_json()["jobs"]

            self.assertEqual("complete", detail.get_json()["status"])
            self.assertEqual(job_id, listing[0]["id"])
            self.assertEqual("discovered", detail.get_json()["events"][0]["type"])

    def test_stale_active_job_is_preserved_as_interrupted(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            server, "CORPUS_JOBS_ROOT", Path(temp_dir)
        ):
            job_id = "c" * 12
            server._write_corpus_job_state(job_id, {
                "id": job_id,
                "status": "running",
                "worker_instance_id": "an-older-backend-process",
                "events": [],
            })
            state = server._read_corpus_job_state(job_id)
            self.assertEqual("interrupted", state["status"])
            self.assertIn("backend restarted", state["error"])


if __name__ == "__main__":
    unittest.main()
