"""Behavioral tests for bounded repair and post-model deterministic gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pipeline
from schema import SOURCE_BOUND_GOLDEN_ANSWERS
from extraction import ExtractedText
from schema import ASSET_SCHEMA


class _FakeStrategy:
    key = "s1"
    label = "PyPDF raw text"
    run_prefix = "S1"
    extraction_note = "Raw page-marked text."
    parser = "pypdf"
    experiment = "no_ocr"
    ocr_enabled = False
    ocr_policy = "off"

    def __call__(self, _path: Path) -> ExtractedText:
        return ExtractedText(text="Annual report text", page_count=1, readable_pages=1)


def _payload(confidence: float = 0.95) -> dict:
    return {
        "detected_fiscal_year": "2022",
        "rows": [
            {
                "item": row["item"],
                "answer_m_usd": index + 1,
                "confidence": confidence,
                "source_page": 1,
                "source_label": row["item"],
                "evidence": "test",
            }
            for index, row in enumerate(ASSET_SCHEMA)
        ],
    }


class PipelineSemanticsTests(unittest.TestCase):
    def test_source_bound_audit_scores_only_the_exact_pdf_hash(self):
        source_hash, audited = next(
            (source_hash, audited)
            for source_hash, audited in SOURCE_BOUND_GOLDEN_ANSWERS.items()
            if audited["fiscal_year"] == "2023"
        )
        rows = [
            {"item": item, "answer_m_usd": value, "confidence": 0.95, "accepted": True}
            for item, value in audited["answers"].items()
        ]

        scored = pipeline.compute_metrics(rows, "2023", "3M", source_hash)
        unbound = pipeline.compute_metrics(rows, "2023", "3M", "0" * 64)

        self.assertEqual(scored["accuracy"], 100.0)
        self.assertEqual(scored["gold_status"], "independently_verified")
        self.assertIsNone(unbound["accuracy"])
        self.assertFalse(unbound["has_golden"])

    def _run(self, model_side_effect, confidence=0.95):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            run_dir = runs_root / "run"
            run_dir.mkdir(parents=True)
            pdf_path = Path(temp_dir) / "3M_annual_report_2022.pdf"
            pdf_path.write_bytes(b"%PDF-test")
            model_call = Mock(side_effect=model_side_effect)
            arithmetic = Mock(return_value={
                "checks": [], "total_identities": 1, "evaluated": 1, "passed": 0,
                "failed": 1, "skipped": 0, "consistency": 0.0,
                "failed_identities": ["Current Assets"],
            })
            with patch.object(pipeline, "RUNS_DIR", runs_root), patch.object(
                pipeline, "get_strategy", return_value=_FakeStrategy()
            ), patch.object(
                pipeline, "create_run_dir", return_value=run_dir
            ), patch.object(pipeline, "file_run", return_value=run_dir), patch.object(
                pipeline, "run_extraction", model_call
            ), patch.object(pipeline, "reconcile", arithmetic):
                result = pipeline.run_pipeline(
                    pdf_path=pdf_path,
                    settings={
                        "api_key": "test", "model": "test", "base_url": "https://example.invalid",
                        "provider": "openai", "reasoning_effort": "none",
                    },
                    strategy_key="s1",
                    system_prompt="system",
                    enable_reasoning=False,
                    display_name="3M_annual_report_2022.pdf",
                )
            return result, model_call, arithmetic

    def test_low_confidence_and_failed_arithmetic_do_not_call_model_again(self):
        response = {"choices": [{"message": {"content": json.dumps(_payload(0.7))}}], "usage": {}}
        result, model_call, arithmetic = self._run([(response, 0.1)])

        self.assertEqual(model_call.call_count, 1)
        self.assertEqual(arithmetic.call_count, 1)
        self.assertTrue(all(not row["accepted"] for row in result["rows"]))
        self.assertEqual(result["metrics"]["coverage"], 100.0)
        self.assertEqual(result["metrics"]["confidence_accepted_coverage"], 0.0)
        self.assertEqual(result["reconciliation"]["failed"], 1)
        self.assertEqual(result["contract_repair_attempts"], 0)

    def test_contract_failure_gets_at_most_one_contextual_repair_call(self):
        invalid = {"choices": [{"message": {"content": "{}"}}], "usage": {}}
        valid = {"choices": [{"message": {"content": json.dumps(_payload())}}], "usage": {}}
        result, model_call, _ = self._run([(invalid, 0.1), (valid, 0.2)])

        self.assertEqual(model_call.call_count, 2)
        self.assertEqual(result["contract_repair_attempts"], 1)
        repair_messages = model_call.call_args_list[1].kwargs["messages"]
        self.assertEqual([message["role"] for message in repair_messages], ["system", "user", "assistant", "user"])
        self.assertIn("contract errors", repair_messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
