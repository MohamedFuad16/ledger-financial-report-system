"""API checks for the extracted-answer human-review workflow."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import server


class CorpusReviewRouteTests(unittest.TestCase):
    def setUp(self):
        self.document_id = "a" * 64
        self.document = {
            "sha256": self.document_id,
            "company": "Example",
            "company_slug": "Example",
            "fiscal_year": 2024,
            "source_url": "https://example.com/report.pdf",
            "local_path": "/tmp/example-report.pdf",
            "filename": "example-report.pdf",
        }
        self.blank_review = {
            "document_id": self.document_id,
            "company": "Example",
            "fiscal_year": 2024,
            "status": "human_review_required",
            "candidate_extracted": False,
            "extracted_row_count": 0,
            "rows": [],
        }
        self.extracted_review = {
            **self.blank_review,
            "candidate_extracted": True,
            "candidate_method": "configured_llm_semantic_mapping",
            "extracted_row_count": 27,
            "rows": [{"item": f"Row {index}", "answer_m_usd": index} for index in range(27)],
        }

    def test_missing_prefill_is_extracted_from_the_pdf_before_review(self):
        with patch.object(server, "find_document", return_value=self.document), patch.object(
            server, "verification_payload", side_effect=[self.blank_review, self.extracted_review]
        ), patch.object(server, "current_settings", return_value={
            "api_key": "server-side-key",
            "model": "test-model",
            "base_url": "https://example.com/v1",
            "provider": "test",
            "enable_reasoning": True,
            "reasoning_effort": "medium",
            "temperature": 0.1,
        }), patch.object(
            server, "run_pipeline", return_value={
                "run_id": "S2_test",
                "model": "test-model",
                "provider": "test",
                "fiscal_year": "2024",
                "detected_fiscal_year": "2024",
                "rows": self.extracted_review["rows"],
            }
        ) as extract, patch.object(
            server, "pin_candidate_answers", return_value={**self.document, "verification": {}}
        ) as pin:
            response = server.app.test_client().post(
                f"/api/corpus/{self.document_id}/verification/extract"
            )

        self.assertEqual(201, response.status_code)
        self.assertTrue(response.get_json()["candidate_extracted"])
        self.assertFalse(response.get_json()["reused"])
        self.assertEqual("s2", extract.call_args.kwargs["strategy_key"])
        self.assertEqual("2024", extract.call_args.kwargs["fiscal_year_hint"])
        self.assertEqual("configured_llm", pin.call_args.kwargs["provider"])
        self.assertEqual(27, len(pin.call_args.args[1]["rows"]))

    def test_existing_prefill_is_reused_without_spending_another_extraction(self):
        with patch.object(server, "find_document", return_value=self.document), patch.object(
            server, "verification_payload", return_value=self.extracted_review
        ), patch.object(server, "run_pipeline") as extract:
            response = server.app.test_client().post(
                f"/api/corpus/{self.document_id}/verification/extract"
            )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["reused"])
        extract.assert_not_called()

    def test_legacy_firecrawl_prefill_is_replaced_by_semantic_mapping(self):
        legacy = {**self.extracted_review, "candidate_method": "firecrawl_multi_pass_consensus"}
        with patch.object(server, "find_document", return_value=self.document), patch.object(
            server, "verification_payload", side_effect=[legacy, self.extracted_review]
        ), patch.object(server, "current_settings", return_value={
            "api_key": "server-side-key", "model": "test-model", "base_url": "https://example.com/v1",
            "provider": "test", "enable_reasoning": False, "reasoning_effort": "none", "temperature": 0.1,
        }), patch.object(server, "run_pipeline", return_value={
            "run_id": "S2_test", "model": "test-model", "provider": "test", "fiscal_year": "2024",
            "detected_fiscal_year": "2024", "rows": self.extracted_review["rows"],
        }) as extract, patch.object(
            server, "pin_candidate_answers", return_value={**self.document, "verification": {}}
        ):
            response = server.app.test_client().post(
                f"/api/corpus/{self.document_id}/verification/extract"
            )

        self.assertEqual(201, response.status_code)
        self.assertFalse(response.get_json()["reused"])
        extract.assert_called_once()

    def test_review_does_not_fall_back_to_blank_manual_entry_without_a_connector(self):
        with patch.object(server, "find_document", return_value=self.document), patch.object(
            server, "verification_payload", return_value=self.blank_review
        ), patch.object(server, "current_settings", return_value={"api_key": ""}):
            response = server.app.test_client().post(
                f"/api/corpus/{self.document_id}/verification/extract"
            )

        self.assertEqual(400, response.status_code)
        self.assertIn("extraction is unavailable", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
