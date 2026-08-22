"""Deployment safeguards for the EC2 corpus manifest."""

from __future__ import annotations

import unittest

from deploy.aws.merge_corpus_manifest import merge_manifests


class DeploymentManifestTests(unittest.TestCase):
    def test_live_documents_and_verification_win_without_dropping_new_seeds(self):
        deployed = {
            "version": 1,
            "documents": [
                {"company": "3M", "company_slug": "3M", "fiscal_year": 2022, "sha256": "new-seed"},
                {"company": "New", "company_slug": "New", "fiscal_year": 2022, "sha256": "new-report"},
            ],
        }
        live = {
            "version": 1,
            "documents": [
                {"company": "3M", "company_slug": "3M", "fiscal_year": 2021, "sha256": "live-old-year"},
                {
                    "company": "3M",
                    "company_slug": "3M",
                    "fiscal_year": 2022,
                    "sha256": "live-current",
                    "verification": {"status": "human_verified"},
                },
            ],
        }

        merged = merge_manifests(live, deployed)
        by_identity = {
            (item["company_slug"], item["fiscal_year"]): item
            for item in merged["documents"]
        }

        self.assertEqual(3, len(by_identity))
        self.assertEqual("live-old-year", by_identity[("3M", 2021)]["sha256"])
        self.assertEqual("live-current", by_identity[("3M", 2022)]["sha256"])
        self.assertEqual("human_verified", by_identity[("3M", 2022)]["verification"]["status"])
        self.assertEqual("new-report", by_identity[("New", 2022)]["sha256"])


if __name__ == "__main__":
    unittest.main()
