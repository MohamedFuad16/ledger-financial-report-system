"""Tests for the Firecrawl availability ledger."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
import csv
from pathlib import Path


SCRIPT = Path(__file__).parent / "research" / "corpus" / "summarize_firecrawl_job.py"
SPEC = importlib.util.spec_from_file_location("summarize_firecrawl_job", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class FirecrawlAvailabilityTests(unittest.TestCase):
    def test_reads_the_bakuraku_registry_column(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "customers.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["company_name"])
                writer.writeheader()
                writer.writerow({"company_name": "Bakuraku Client"})

            self.assertEqual(["Bakuraku Client"], MODULE.customer_names(path))

    def test_rows_distinguish_pending_found_failed_and_downloaded(self):
        job = {
            "years": [2024, 2025],
            "events": [
                {"type": "discovered", "company": "NoHit", "reports": 0},
                {"type": "discovered", "company": "Hit", "reports": 1},
            ],
            "result": {
                "downloaded": [{
                    "company": "Hit", "fiscal_year": 2024, "screened": True,
                    "sha256": "abc", "source_url": "https://example.com/report.pdf",
                }],
                "failed": [{"company": "Hit", "year": 2025, "reason": "screen failed"}],
            },
        }

        rows = MODULE.build_rows(job, ["NoHit", "Hit", "Waiting"])
        statuses = {(row["company"], row["fiscal_year"]): row["status"] for row in rows}

        self.assertEqual("not_found", statuses[("NoHit", 2024)])
        self.assertEqual("downloaded", statuses[("Hit", 2024)])
        self.assertEqual("not_downloaded", statuses[("Hit", 2025)])
        self.assertEqual("pending", statuses[("Waiting", 2024)])


if __name__ == "__main__":
    unittest.main()
