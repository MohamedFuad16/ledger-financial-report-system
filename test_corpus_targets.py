import unittest
from unittest.mock import patch

import server


class CorpusTargetLibraryTests(unittest.TestCase):
    def test_library_has_100_unique_targets_without_counting_seeds_as_reports(self):
        document = {
            "company": "3M",
            "company_slug": "3M",
            "fiscal_year": 2020,
            "source_url": "https://investors.3m.com/example.pdf",
            "local_path": "corpus_dataset/3M/2020/example.pdf",
            "filename": "example.pdf",
            "sha256": "a" * 64,
            "pages": 100,
            "readable_pages": 100,
            "screened": "ok",
        }
        with patch.object(server, "load_manifest", return_value={"version": 1, "documents": [document]}):
            payload = server.app.test_client().get("/api/corpus").get_json()

        self.assertEqual(len(payload["targets"]), 100)
        self.assertEqual(len({target["company"] for target in payload["targets"]}), 100)
        self.assertEqual(payload["summary"]["companies"], 100)
        self.assertEqual(payload["summary"]["companies_with_reports"], 1)
        self.assertEqual(payload["summary"]["documents"], 1)
        self.assertEqual(payload["targets"][0]["company"], "3M")
        self.assertEqual(payload["targets"][0]["status"], "report_stored")
        self.assertTrue(any(target["status"] == "research_seed" for target in payload["targets"]))


if __name__ == "__main__":
    unittest.main()
