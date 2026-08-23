"""Behavioral tests for bounded repair and post-model deterministic gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pipeline
from schema import ASSIGNMENT_GOLDEN_SOURCE_SHA256, SOURCE_BOUND_GOLDEN_ANSWERS
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


class _FakeS3Strategy(_FakeStrategy):
    key = "s3"
    label = "Strategy 3 - intelligent scanning gate"
    run_prefix = "S3"
    parser = "inspector-intelligent"
    experiment = "intelligent_scan"
    complete_packet = False

    def __call__(self, _path: Path, **_kwargs) -> ExtractedText:
        result = ExtractedText(
            text="[page 2]\nBalance sheet assets",
            page_count=4,
            readable_pages=4,
            diagnostics={
                "selected_pages": [2],
                "selected_page_count": 1,
                "complete_document_packet": self.complete_packet,
            },
        )
        result.retained_pages = [
            (1, "Corporate governance boilerplate"),
            (2, "Balance sheet assets"),
            (3, "Notes: cash and cash equivalents and accounts receivable detail"),
            (4, "Officers and directors"),
        ]
        return result


class _FakeCompletePacketS3Strategy(_FakeS3Strategy):
    complete_packet = True


def _payload_with_nulls(null_items: set[str], confidence: float = 0.95) -> dict:
    payload = _payload(confidence)
    for row in payload["rows"]:
        if row["item"] in null_items:
            row["answer_m_usd"] = None
            row["confidence"] = 0.0
    return payload


class PipelineSemanticsTests(unittest.TestCase):
    def test_assignment_gold_scores_only_the_supplied_pdf_hash(self):
        from schema import GOLDEN_ANSWERS_STORE

        rows = [
            {"item": item, "answer_m_usd": value, "confidence": 0.95, "accepted": True}
            for item, value in GOLDEN_ANSWERS_STORE["2022"].items()
        ]

        scored = pipeline.compute_metrics(
            rows, "2022", "3M", ASSIGNMENT_GOLDEN_SOURCE_SHA256, "USD"
        )
        mislabeled = pipeline.compute_metrics(rows, "2022", "3M", "0" * 64, "USD")

        self.assertEqual(100.0, scored["accuracy"])
        self.assertEqual("assignment_supplied", scored["gold_status"])
        self.assertFalse(mislabeled["has_golden"])

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
        wrong_currency = pipeline.compute_metrics(rows, "2023", "3M", source_hash, "JPY")

        self.assertEqual(scored["accuracy"], 100.0)
        self.assertEqual(scored["gold_status"], "independently_verified")
        self.assertIsNone(unbound["accuracy"])
        self.assertFalse(unbound["has_golden"])
        self.assertFalse(wrong_currency["has_golden"])

    def test_unicode_report_identities_do_not_collapse(self):
        dainichi = pipeline.report_identity("ダイニチ工業株式会社_annual_report_2022.pdf", "2022")[0]
        resol = pipeline.report_identity("リソルホールディングス株式会社_annual_report_2022.pdf", "2022")[0]

        self.assertEqual(dainichi, "ダイニチ工業株式会社")
        self.assertEqual(resol, "リソルホールディングス株式会社")
        self.assertNotEqual(pipeline.normalize_company_key(dainichi), pipeline.normalize_company_key(resol))

    def test_source_precision_is_detected_in_million_units(self):
        self.assertEqual(pipeline.detect_source_value_quantum("（単位：百万円）"), 1.0)
        self.assertEqual(pipeline.detect_source_value_quantum("(単位：千円)"), 0.001)

    def test_jpy_thousand_gold_does_not_accept_tenth_million_rounding(self):
        source_hash, audited = next(
            (source_hash, audited)
            for source_hash, audited in SOURCE_BOUND_GOLDEN_ANSWERS.items()
            if audited.get("currency") == "JPY" and audited.get("source_value_quantum") == 0.001
        )
        rows = [
            {"item": item, "answer_m_usd": value, "confidence": 0.95, "accepted": True}
            for item, value in audited["answers"].items()
        ]
        rows[0]["answer_m_usd"] = round(float(rows[0]["answer_m_usd"]), 1)

        scored = pipeline.compute_metrics(
            rows, audited["fiscal_year"], audited["company"], source_hash, "JPY"
        )

        self.assertLess(scored["accuracy"], 100.0)
        self.assertEqual(scored["gold_value_quantum"], 0.001)

    def _run(self, model_side_effect, confidence=0.95, strategy=None, arithmetic_side_effect=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            run_dir = runs_root / "run"
            run_dir.mkdir(parents=True)
            pdf_path = Path(temp_dir) / "3M_annual_report_2022.pdf"
            pdf_path.write_bytes(b"%PDF-test")
            model_call = Mock(side_effect=model_side_effect)
            failing_report = {
                "checks": [], "total_identities": 1, "evaluated": 1, "passed": 0,
                "failed": 1, "skipped": 0, "consistency": 0.0,
                "failed_identities": ["Current Assets"],
            }
            arithmetic = (
                Mock(side_effect=arithmetic_side_effect)
                if arithmetic_side_effect is not None
                else Mock(return_value=failing_report)
            )
            with patch.object(pipeline, "RUNS_DIR", runs_root), patch.object(
                pipeline, "get_strategy", return_value=strategy or _FakeStrategy()
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

    def test_strategy3_null_rows_trigger_one_bounded_evidence_retry(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {"choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}], "usage": {}}
        retry_payload = _payload_with_nulls(
            {row["item"] for row in ASSET_SCHEMA if row["item"] not in nulls}
        )
        for row in retry_payload["rows"]:
            if row["item"] == "Cash & Cash Equivalents":
                row["answer_m_usd"] = 111
            if row["item"] == "Accounts Receivable - Trade":
                row["answer_m_usd"] = 222
            if row["item"] == "Inventories, Net":
                # A retry reply must never overwrite an answered first-pass row.
                row["answer_m_usd"] = 999_999
        retry = {"choices": [{"message": {"content": json.dumps(retry_payload)}}], "usage": {}}

        result, model_call, _ = self._run([(first, 0.1), (retry, 0.2)], strategy=_FakeS3Strategy())

        self.assertEqual(model_call.call_count, 2)
        self.assertTrue(result["evidence_retry"]["attempted"])
        self.assertEqual(sorted(result["evidence_retry"]["recovered_rows"]), sorted(nulls))
        self.assertNotIn(2, result["evidence_retry"]["pages_added"])
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertEqual(by_item["Cash & Cash Equivalents"]["answer_m_usd"], 111)
        self.assertTrue(by_item["Cash & Cash Equivalents"]["evidence"].startswith("[evidence retry]"))
        self.assertEqual(by_item["Accounts Receivable - Trade"]["answer_m_usd"], 222)
        inventories_index = next(i for i, row in enumerate(ASSET_SCHEMA) if row["item"] == "Inventories, Net")
        self.assertEqual(by_item["Inventories, Net"]["answer_m_usd"], inventories_index + 1)
        retry_prompt = model_call.call_args_list[1].kwargs["user_prompt"]
        self.assertIn("EVIDENCE RETRY", retry_prompt)
        self.assertIn("Cash & Cash Equivalents", retry_prompt)

    def test_strategy1_null_rows_never_trigger_the_evidence_retry(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {"choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}], "usage": {}}

        result, model_call, _ = self._run([(first, 0.1)])

        self.assertEqual(model_call.call_count, 1)
        self.assertFalse(result["evidence_retry"]["attempted"])

    def test_strategy3_identity_replacement_is_accepted_only_when_reconciliation_improves(self):
        first = {"choices": [{"message": {"content": json.dumps(_payload())}}], "usage": {}}
        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        for row in retry_payload["rows"]:
            if row["item"] == "Inventories, Net":
                row["answer_m_usd"] = 555
                row["confidence"] = 0.95
        retry = {"choices": [{"message": {"content": json.dumps(retry_payload)}}], "usage": {}}
        failing = {
            "checks": [], "total_identities": 1, "evaluated": 1, "passed": 0,
            "failed": 1, "skipped": 0, "consistency": 0.0,
            "failed_identities": ["Current Assets"],
        }
        passing = {**failing, "passed": 1, "failed": 0, "consistency": 100.0, "failed_identities": []}

        result, model_call, arithmetic = self._run(
            [(first, 0.1), (retry, 0.2)],
            strategy=_FakeS3Strategy(),
            # pre-retry: failing → trial with replacement: passing → final: passing
            arithmetic_side_effect=[failing, passing, passing],
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertEqual(arithmetic.call_count, 3)
        self.assertEqual(result["evidence_retry"]["replaced_rows"], ["Inventories, Net"])
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertEqual(by_item["Inventories, Net"]["answer_m_usd"], 555)
        self.assertTrue(by_item["Inventories, Net"]["evidence"].startswith("[evidence retry]"))

    def test_complete_packet_nulls_are_decided_absences_and_never_retried(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {"choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}], "usage": {}}
        passing = {
            "checks": [], "total_identities": 1, "evaluated": 1, "passed": 1,
            "failed": 0, "skipped": 0, "consistency": 100.0, "failed_identities": [],
        }

        result, model_call, _ = self._run(
            [(first, 0.1)],
            strategy=_FakeCompletePacketS3Strategy(),
            arithmetic_side_effect=[passing, passing],
        )

        self.assertEqual(model_call.call_count, 1)
        self.assertFalse(result["evidence_retry"]["attempted"])
        self.assertIn("complete readable document", result["evidence_retry"]["reason"])

    def test_sparse_total_only_run_gets_one_both_sides_verification_retry(self):
        # A condensed gazette yields essentially just Total Assets; nothing can
        # cross-check it, so one verification call must re-derive it.
        only_total = {row["item"] for row in ASSET_SCHEMA} - {"Total Assets"}
        first = {"choices": [{"message": {"content": json.dumps(_payload_with_nulls(only_total))}}], "usage": {}}
        retry_payload = _payload_with_nulls(only_total)
        for row in retry_payload["rows"]:
            if row["item"] == "Total Assets":
                row["answer_m_usd"] = 9219
        retry = {"choices": [{"message": {"content": json.dumps(retry_payload)}}], "usage": {}}
        passing = {
            "checks": [], "total_identities": 1, "evaluated": 0, "passed": 0,
            "failed": 0, "skipped": 1, "consistency": None, "failed_identities": [],
        }

        result, model_call, _ = self._run(
            [(first, 0.1), (retry, 0.2)],
            strategy=_FakeCompletePacketS3Strategy(),
            arithmetic_side_effect=[passing, passing, passing],
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertTrue(result["evidence_retry"]["verification_mode"])
        self.assertEqual(result["evidence_retry"]["replaced_rows"], ["Total Assets"])
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertEqual(by_item["Total Assets"]["answer_m_usd"], 9219)
        retry_prompt = model_call.call_args_list[1].kwargs["user_prompt"]
        self.assertIn("BOTH sides", retry_prompt)

    def test_complete_packet_failed_identity_still_gets_the_misread_retry(self):
        first = {"choices": [{"message": {"content": json.dumps(_payload())}}], "usage": {}}
        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        retry = {"choices": [{"message": {"content": json.dumps(retry_payload)}}], "usage": {}}

        result, model_call, _ = self._run(
            [(first, 0.1), (retry, 0.2)], strategy=_FakeCompletePacketS3Strategy()
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertTrue(result["evidence_retry"]["attempted"])
        self.assertEqual(result["evidence_retry"]["missing_rows"], [])
        self.assertTrue(result["evidence_retry"]["failed_identity_rows"])

    def test_strategy3_failed_evidence_retry_keeps_first_pass_values(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {"choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}], "usage": {}}

        result, model_call, _ = self._run(
            [(first, 0.1), RuntimeError("provider unavailable")], strategy=_FakeS3Strategy()
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertTrue(result["evidence_retry"]["attempted"])
        self.assertIn("provider unavailable", result["evidence_retry"]["error"])
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertIsNone(by_item["Cash & Cash Equivalents"]["answer_m_usd"])

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
