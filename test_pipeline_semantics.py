"""Behavioral tests for bounded repair and post-model deterministic gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pipeline
from extraction import ExtractedText
from normalize import apply_schema_mapping_conventions
from prompts import SYSTEM_PROMPT, build_evidence_retry_prompt
from reconcile import detect_ppe_measurement_basis_issue, detect_source_fidelity_issues, reconcile
from schema import ASSET_SCHEMA, ASSIGNMENT_GOLDEN_SOURCE_SHA256, SOURCE_BOUND_GOLDEN_ANSWERS


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


class _FakePPEMeasurementS3Strategy(_FakeS3Strategy):
    def __call__(self, _path: Path, **_kwargs) -> ExtractedText:
        result = super().__call__(_path, **_kwargs)
        result.text = "[page 2]\n有形固定資産（純額） 100"
        result.retained_pages[2] = (
            3,
            "有形固定資産等明細表 取得価額 建物 50 機械 30 その他 30 減価償却累計額 40 帳簿価額 100",
        )
        return result


def _payload_with_nulls(null_items: set[str], confidence: float = 0.95) -> dict:
    payload = _payload(confidence)
    for row in payload["rows"]:
        if row["item"] in null_items:
            row["answer_m_usd"] = None
            row["confidence"] = 0.0
    return payload


class PipelineSemanticsTests(unittest.TestCase):
    def test_system_prompt_pins_lease_receivable_and_gross_ppe_conventions(self):
        self.assertIn("リース投資資産 (lease investment assets) is a lease receivable", SYSTEM_PROMPT)
        self.assertIn("return the\n  PPE component rows on that gross-cost basis", SYSTEM_PROMPT)
        self.assertIn("Land and Construction in Progress are normally non-depreciable", SYSTEM_PROMPT)
        self.assertIn("4,676,003千円 = 4,676.003 M JPY", SYSTEM_PROMPT)
        self.assertIn("directly printed balance-sheet amount is\n  authoritative", SYSTEM_PROMPT)
        self.assertIn("預け金 is not Cash & Cash Equivalents", SYSTEM_PROMPT)

    def test_source_fidelity_validator_detects_citation_contradictions(self):
        rows = [
            {
                "item": "Total Assets",
                "answer_m_usd": 4.676003,
                "evidence": "Reported as 4,676,003 thousand yen = 4.676003 M JPY.",
            },
            {
                "item": "Fixed Assets",
                "answer_m_usd": 36.084,
                "evidence": "Component sum 36.084; printed total on Page 68 is 36,085 thousand yen.",
            },
            {
                "item": "Tangible Assets",
                "answer_m_usd": 18.337,
                "evidence": "取得原価 less depreciation = 18,337千円 (貸借対照表純額は18,336千円)",
            },
            {
                "item": "Other Fixed Assets",
                "answer_m_usd": 1514.0,
                "evidence": "Residual is 1,514 (comprising prepaid expenses 5, tax 369, and other 1,138).",
            },
            {
                "item": "Cash & Cash Equivalents",
                "answer_m_usd": 48409.0,
                "source_label": "現金預金 + 預け金",
                "evidence": "現金預金 46,909 + 預け金 1,500",
            },
        ]

        issues = detect_source_fidelity_issues(rows)
        codes = {issue["code"] for issue in issues}

        self.assertEqual(
            codes,
            {
                "contradictory_thousands_to_millions_conversion",
                "direct_reported_value_overwritten_by_arithmetic",
                "residual_disagrees_with_direct_components",
                "custody_deposit_included_in_cash",
            },
        )
        cash_issue = next(issue for issue in issues if issue["code"] == "custody_deposit_included_in_cash")
        self.assertEqual(cash_issue["retry_items"], ["Cash & Cash Equivalents", "Other Quick Assets"])

    def test_source_fidelity_validator_accepts_consistent_citations(self):
        rows = [
            {
                "item": "Total Assets",
                "answer_m_usd": 4676.003,
                "evidence": "Reported as 4,676,003 thousand yen = 4,676.003 M JPY.",
            },
            {
                "item": "Fixed Assets",
                "answer_m_usd": 36.085,
                "evidence": "Printed total on Page 68 is 36,085 thousand yen.",
            },
            {
                "item": "Other Fixed Assets",
                "answer_m_usd": 1512.0,
                "evidence": "Comprising prepaid expenses 5, tax 369, and other 1,138.",
            },
            {
                "item": "Accumulated Depreciation",
                "answer_m_usd": -20145.764,
                "evidence": "20,145,764 thousand yen = -20,145.764 M JPY as a deduction.",
            },
        ]

        self.assertEqual(detect_source_fidelity_issues(rows), [])

    def test_source_fidelity_validator_allows_exact_source_rounding_bound(self):
        rows = [
            {
                "item": "Intangible Assets",
                "answer_m_usd": 4047.0,
                "evidence": (
                    "Reported subtotal 4,047 million yen "
                    "(comprising goodwill 1,253 and other intangibles 2,793)."
                ),
            }
        ]

        self.assertEqual(detect_source_fidelity_issues(rows, value_quantum=1.0), [])

    def test_evidence_retry_prompt_contains_only_permitted_baseline_and_exact_failure(self):
        prompt = build_evidence_retry_prompt(
            additional_pages_text="[page 9]\nInventory note",
            missing_items=["Inventories, Net"],
            first_pass_rows=[
                {
                    "item": "Inventories, Net",
                    "answer_m_usd": 120.125,
                    "confidence": 0.72,
                    "source_page": 4,
                    "source_label": "棚卸資産",
                    "evidence": "Printed inventory line.",
                },
                {
                    "item": "Cash & Cash Equivalents",
                    "answer_m_usd": 999,
                    "confidence": 0.99,
                    "source_page": 2,
                    "source_label": "現金及び預金",
                    "evidence": "Must not enter the compact baseline.",
                },
            ],
            failed_identity_checks=[
                {
                    "identity": "Current Assets = Quick Assets + Inventories, Net + Other Current Assets",
                    "status": "failed",
                    "stated": 500.5,
                    "computed": 501.625,
                    "delta": 1.13,
                    "tolerance": 0.002,
                }
            ],
            output_currency="JPY",
            original_packet_text="[page 2]\nBalance sheet",
        )

        baseline_section = prompt.split("FIRST-PASS BASELINE — PERMITTED ROWS ONLY", 1)[1].split(
            "FAILED ARITHMETIC IDENTITIES", 1
        )[0]
        self.assertIn('"item":"Inventories, Net"', baseline_section)
        self.assertIn('"first_pass_value":120.125', baseline_section)
        self.assertIn('"unit_currency":"M JPY"', baseline_section)
        self.assertIn('"source_page":4', baseline_section)
        self.assertIn('"source_label":"棚卸資産"', baseline_section)
        self.assertIn('"evidence":"Printed inventory line."', baseline_section)
        self.assertNotIn("Cash & Cash Equivalents", baseline_section)
        self.assertNotIn("Must not enter", baseline_section)
        self.assertIn('"discrepancy_parts_minus_total":1.125', prompt)
        self.assertIn("Preserve every\nnon-permitted row", prompt)
        self.assertIn("answer_m_usd null and confidence 0.0", prompt)
        self.assertIn("ground every\nproposed non-null value", prompt)

    def test_assignment_gold_scores_only_the_supplied_pdf_hash(self):
        from schema import GOLDEN_ANSWERS_STORE

        rows = [
            {"item": item, "answer_m_usd": value, "confidence": 0.95, "accepted": True}
            for item, value in GOLDEN_ANSWERS_STORE["2022"].items()
        ]

        scored = pipeline.compute_metrics(rows, "2022", "3M", ASSIGNMENT_GOLDEN_SOURCE_SHA256, "USD")
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

    def test_toenec_fy2020_fixture_uses_the_source_printed_investments_value(self):
        source_hash = "55c088629bc87b5e880c389249f32b9d22be072412ca23295a52acf6a7ac0185"
        audited = SOURCE_BOUND_GOLDEN_ANSWERS[source_hash]
        self.assertEqual(audited["answers"]["Investments"], 21729.0)
        rows = [
            {
                "item": "Investments",
                "answer_m_usd": 21729.0,
                "confidence": 0.95,
                "accepted": True,
            }
        ]
        scored = pipeline.compute_metrics(rows, "2020", "株式会社トーエネック", source_hash, "JPY")
        self.assertEqual(scored["exact_matches"], 1)
        self.assertEqual(scored["total_compared"], 1)

    def test_lease_investment_assets_move_to_trade_receivables_when_label_is_exact(self):
        rows = [
            {
                "item": "Accounts Receivable - Trade",
                "answer_m_usd": 40915.0,
                "confidence": 0.95,
                "source_page": 47,
                "source_label": "受取手形及び売掛金 − 貸倒引当金",
                "evidence": "41,628 − 713",
            },
            {
                "item": "Other Quick Assets",
                "answer_m_usd": 24.0,
                "confidence": 0.9,
                "source_page": 47,
                "source_label": "リース投資資産",
                "evidence": "リース投資資産 24",
            },
        ]

        mapped, repairs = apply_schema_mapping_conventions(rows)
        by_item = {row["item"]: row for row in mapped}
        self.assertEqual(by_item["Accounts Receivable - Trade"]["answer_m_usd"], 40939.0)
        self.assertEqual(by_item["Other Quick Assets"]["answer_m_usd"], 0.0)
        self.assertEqual(len(repairs), 1)
        self.assertIn("lease investment assets", repairs[0])

    def test_composite_other_quick_label_is_not_semantically_rewritten(self):
        rows = [
            {"item": "Accounts Receivable - Trade", "answer_m_usd": 100.0},
            {
                "item": "Other Quick Assets",
                "answer_m_usd": 25.0,
                "source_label": "リース投資資産 + その他",
            },
        ]
        mapped, repairs = apply_schema_mapping_conventions(rows)
        self.assertEqual(mapped, rows)
        self.assertEqual(repairs, [])

    def test_measurement_validator_flags_reconciled_net_ppe_with_disclosed_depreciation(self):
        values = {
            "Tangible Assets": 100.0,
            "Land": 20.0,
            "Buildings": 30.0,
            "Plant & Machinery": 20.0,
            "Construction in Progress": 10.0,
            "Other Equipment": 20.0,
            "Accumulated Depreciation": 0.0,
        }
        rows = [{"item": item, "answer_m_usd": value} for item, value in values.items()]
        evidence = "有形固定資産（純額）100。減価償却累計額 40。"

        issue = detect_ppe_measurement_basis_issue(rows, evidence, value_quantum=1.0)
        self.assertIsNotNone(issue)
        assert issue is not None
        self.assertEqual(issue["code"], "net_ppe_with_zero_accumulated_depreciation")
        self.assertEqual(issue["retry_items"][-1], "Accumulated Depreciation")

        gross_rows = [dict(row) for row in rows]
        gross_values = {
            "Buildings": 50.0,
            "Plant & Machinery": 30.0,
            "Other Equipment": 30.0,
            "Accumulated Depreciation": -40.0,
        }
        for row in gross_rows:
            if row["item"] in gross_values:
                row["answer_m_usd"] = gross_values[row["item"]]
        self.assertEqual(reconcile(gross_rows, value_quantum=1.0)["failed"], 0)
        self.assertIsNone(detect_ppe_measurement_basis_issue(gross_rows, evidence, value_quantum=1.0))

    def test_unicode_report_identities_do_not_collapse(self):
        dainichi = pipeline.report_identity("ダイニチ工業株式会社_annual_report_2022.pdf", "2022")[0]
        resol = pipeline.report_identity("リソルホールディングス株式会社_annual_report_2022.pdf", "2022")[0]

        self.assertEqual(dainichi, "ダイニチ工業株式会社")
        self.assertEqual(resol, "リソルホールディングス株式会社")
        self.assertNotEqual(
            pipeline.normalize_company_key(dainichi),
            pipeline.normalize_company_key(resol),
        )

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

    def _run(
        self,
        model_side_effect,
        confidence=0.95,
        strategy=None,
        arithmetic_side_effect=None,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            run_dir = runs_root / "run"
            run_dir.mkdir(parents=True)
            pdf_path = Path(temp_dir) / "3M_annual_report_2022.pdf"
            pdf_path.write_bytes(b"%PDF-test")
            model_call = Mock(side_effect=model_side_effect)
            failing_report = {
                "checks": [],
                "total_identities": 1,
                "evaluated": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "consistency": 0.0,
                "failed_identities": ["Current Assets"],
            }
            arithmetic = (
                Mock(side_effect=arithmetic_side_effect)
                if arithmetic_side_effect is not None
                else Mock(return_value=failing_report)
            )
            with (
                patch.object(pipeline, "RUNS_DIR", runs_root),
                patch.object(pipeline, "get_strategy", return_value=strategy or _FakeStrategy()),
                patch.object(pipeline, "create_run_dir", return_value=run_dir),
                patch.object(pipeline, "file_run", return_value=run_dir),
                patch.object(pipeline, "run_extraction", model_call),
                patch.object(pipeline, "reconcile", arithmetic),
            ):
                result = pipeline.run_pipeline(
                    pdf_path=pdf_path,
                    settings={
                        "api_key": "test",
                        "model": "test",
                        "base_url": "https://example.invalid",
                        "provider": "openai",
                        "reasoning_effort": "none",
                    },
                    strategy_key="s1",
                    system_prompt="system",
                    enable_reasoning=False,
                    display_name="3M_annual_report_2022.pdf",
                )
            return result, model_call, arithmetic

    def test_low_confidence_and_failed_arithmetic_do_not_call_model_again(self):
        response = {
            "choices": [{"message": {"content": json.dumps(_payload(0.7))}}],
            "usage": {},
        }
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
        first = {
            "choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}],
            "usage": {},
        }
        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA if row["item"] not in nulls})
        for row in retry_payload["rows"]:
            if row["item"] == "Cash & Cash Equivalents":
                row["answer_m_usd"] = 111
            if row["item"] == "Accounts Receivable - Trade":
                row["answer_m_usd"] = 222
            if row["item"] == "Inventories, Net":
                # A retry reply must never overwrite an answered first-pass row.
                row["answer_m_usd"] = 999_999
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }

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
        self.assertIn("PREVIOUSLY SUPPLIED PAGES", retry_prompt)
        self.assertIn("[page 2]\nBalance sheet assets", retry_prompt)

    def test_strategy1_null_rows_never_trigger_the_evidence_retry(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {
            "choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}],
            "usage": {},
        }

        result, model_call, _ = self._run([(first, 0.1)])

        self.assertEqual(model_call.call_count, 1)
        self.assertFalse(result["evidence_retry"]["attempted"])

    def test_strategy3_identity_replacement_is_accepted_only_when_reconciliation_improves(
        self,
    ):
        first = {
            "choices": [{"message": {"content": json.dumps(_payload())}}],
            "usage": {},
        }
        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        for row in retry_payload["rows"]:
            if row["item"] == "Inventories, Net":
                row["answer_m_usd"] = 555
                row["confidence"] = 0.95
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }
        failing = {
            "checks": [
                {
                    "identity": "Current Assets = Quick Assets + Inventories, Net + Other Current Assets",
                    "total_item": "Current Assets",
                    "status": "failed",
                    "stated": 10.0,
                    "computed": 20.25,
                    "delta": 10.25,
                    "tolerance": 0.5,
                }
            ],
            "total_identities": 1,
            "evaluated": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "consistency": 0.0,
            "failed_identities": ["Current Assets"],
        }
        passing = {
            **failing,
            "passed": 1,
            "failed": 0,
            "consistency": 100.0,
            "failed_identities": [],
        }

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
        retry_prompt = model_call.call_args_list[1].kwargs["user_prompt"]
        self.assertIn('"item":"Inventories, Net"', retry_prompt)
        self.assertIn('"item":"Inventories, Net","first_pass_value":6.0', retry_prompt)
        self.assertIn('"discrepancy_parts_minus_total":10.25', retry_prompt)
        self.assertIn("PREVIOUSLY SUPPLIED PAGES", retry_prompt)
        self.assertIn("[page 2]\nBalance sheet assets", retry_prompt)

    def test_strategy3_identity_replacement_is_rejected_without_strict_improvement(self):
        first = {
            "choices": [{"message": {"content": json.dumps(_payload())}}],
            "usage": {},
        }
        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        for row in retry_payload["rows"]:
            if row["item"] == "Inventories, Net":
                row["answer_m_usd"] = 555
                row["confidence"] = 0.95
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }
        still_failing = {
            "checks": [
                {
                    "identity": "Current Assets = Quick Assets + Inventories, Net + Other Current Assets",
                    "total_item": "Current Assets",
                    "status": "failed",
                    "stated": 10.0,
                    "computed": 20.25,
                    "delta": 10.25,
                    "tolerance": 0.5,
                }
            ],
            "total_identities": 1,
            "evaluated": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "consistency": 0.0,
            "failed_identities": ["Current Assets"],
        }

        result, model_call, arithmetic = self._run(
            [(first, 0.1), (retry, 0.2)],
            strategy=_FakeS3Strategy(),
            arithmetic_side_effect=[still_failing, still_failing, still_failing],
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertEqual(arithmetic.call_count, 3)
        self.assertEqual(result["evidence_retry"]["replaced_rows"], [])
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertEqual(by_item["Inventories, Net"]["answer_m_usd"], 6)
        self.assertEqual(by_item["Inventories, Net"]["evidence"], "test")

    def test_strategy3_accepts_gross_ppe_retry_when_measurement_basis_improves(self):
        first_payload = _payload()
        first_values = {
            "Tangible Assets": 100.0,
            "Land": 20.0,
            "Buildings": 30.0,
            "Plant & Machinery": 20.0,
            "Construction in Progress": 10.0,
            "Other Equipment": 20.0,
            "Accumulated Depreciation": 0.0,
        }
        for row in first_payload["rows"]:
            if row["item"] in first_values:
                row["answer_m_usd"] = first_values[row["item"]]
                row["source_label"] = f"{row['item']}（純額）"
        first = {
            "choices": [{"message": {"content": json.dumps(first_payload)}}],
            "usage": {},
        }

        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        gross_values = {
            "Land": 20.0,
            "Buildings": 50.0,
            "Plant & Machinery": 30.0,
            "Construction in Progress": 10.0,
            "Other Equipment": 30.0,
            "Accumulated Depreciation": -40.0,
        }
        for row in retry_payload["rows"]:
            if row["item"] in gross_values:
                row["answer_m_usd"] = gross_values[row["item"]]
                row["confidence"] = 0.95
                row["source_page"] = 3
                row["source_label"] = "有形固定資産等明細表"
                row["evidence"] = "Gross cost and accumulated depreciation note."
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }
        passing = {
            "checks": [],
            "total_identities": 1,
            "evaluated": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "consistency": 100.0,
            "failed_identities": [],
        }

        result, model_call, arithmetic = self._run(
            [(first, 0.1), (retry, 0.2)],
            strategy=_FakePPEMeasurementS3Strategy(),
            arithmetic_side_effect=[passing, passing, passing],
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertEqual(arithmetic.call_count, 3)
        self.assertTrue(result["evidence_retry"]["measurement_basis_resolved"])
        self.assertEqual(result["measurement_basis_validation"]["status"], "ok")
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertEqual(by_item["Buildings"]["answer_m_usd"], 50.0)
        self.assertEqual(by_item["Accumulated Depreciation"]["answer_m_usd"], -40.0)
        self.assertEqual(
            sorted(result["evidence_retry"]["replaced_rows"]),
            sorted(
                [
                    "Buildings",
                    "Plant & Machinery",
                    "Other Equipment",
                    "Accumulated Depreciation",
                ]
            ),
        )
        retry_prompt = model_call.call_args_list[1].kwargs["user_prompt"]
        self.assertIn("PPE MEASUREMENT-BASIS VALIDATION FAILURE", retry_prompt)
        self.assertIn("gross component", retry_prompt)

    def test_strategy3_accepts_retry_when_own_citation_becomes_source_consistent(self):
        first_payload = _payload()
        for row in first_payload["rows"]:
            if row["item"] == "Total Assets":
                row["answer_m_usd"] = 4.676003
                row["source_label"] = "資産合計"
                row["evidence"] = "Reported on the balance sheet as 4,676,003 thousand yen = 4.676003 M JPY."
        first = {
            "choices": [{"message": {"content": json.dumps(first_payload)}}],
            "usage": {},
        }

        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        for row in retry_payload["rows"]:
            if row["item"] == "Total Assets":
                row["answer_m_usd"] = 4676.003
                row["confidence"] = 0.95
                row["source_page"] = 69
                row["source_label"] = "資産合計"
                row["evidence"] = "4,676,003 thousand yen = 4,676.003 M JPY."
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }
        passing = {
            "checks": [],
            "total_identities": 7,
            "evaluated": 7,
            "passed": 7,
            "failed": 0,
            "skipped": 0,
            "consistency": 100.0,
            "failed_identities": [],
        }

        result, model_call, arithmetic = self._run(
            [(first, 0.1), (retry, 0.2)],
            strategy=_FakeS3Strategy(),
            arithmetic_side_effect=[passing, passing, passing],
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertEqual(arithmetic.call_count, 3)
        self.assertEqual(result["evidence_retry"]["replaced_rows"], ["Total Assets"])
        self.assertTrue(result["evidence_retry"]["source_fidelity_resolved"])
        self.assertEqual(result["source_fidelity_validation"]["status"], "ok")
        total = next(row for row in result["rows"] if row["item"] == "Total Assets")
        self.assertEqual(total["answer_m_usd"], 4676.003)
        retry_prompt = model_call.call_args_list[1].kwargs["user_prompt"]
        self.assertIn("SOURCE-FIDELITY VALIDATION FAILURES", retry_prompt)
        self.assertIn("not an answer key", retry_prompt)

    def test_audited_strategy3_mismatches_respect_the_historical_retry_scope(self):
        # Frozen replay of the seven imperfect runs from the benchmark audit.
        # Four RESOL rows were in the permitted retry scope. The other six
        # mismatches never entered that scope, so this targeted change must not
        # mutate them or pretend to solve their separate taxonomy/gold issues.
        cases = [
            ("S3_20260824T043151Z_034", "Accumulated Depreciation", 0.0, -20145.764, "replace"),
            ("S3_20260824T043258Z_036", "Land", None, 18605.316, "missing"),
            ("S3_20260824T043335Z_037", "Land", None, 18315.0, "missing"),
            ("S3_20260824T043335Z_037", "Construction in Progress", None, 169.0, "missing"),
            ("S3_20260824T043905Z_061", "Other Fixed Assets", 71.844, 71.842, "outside"),
            ("S3_20260824T044039Z_068", "Investments", 21729.0, 3421729.0, "outside"),
            ("S3_20260824T044818Z_098", "Accounts Receivable - Trade", 40915.0, 40939.0, "outside"),
            ("S3_20260824T044818Z_098", "Other Quick Assets", 24.0, 0.0, "outside"),
            ("S3_20260824T045021Z_101", "Quick Assets", 95396.0, 95404.0, "outside"),
            ("S3_20260824T045021Z_101", "Accounts Receivable - Trade", 45574.0, 45582.0, "outside"),
        ]

        for run_id, item, first_value, proposal, scope in cases:
            with self.subTest(run_id=run_id, item=item):
                first_rows = [
                    {
                        "item": item,
                        "answer_m_usd": first_value,
                        "confidence": 0.9,
                        "source_page": 1,
                        "source_label": "first pass",
                        "evidence": "first-pass evidence",
                    }
                ]
                retry_rows = [
                    {
                        "item": item,
                        "answer_m_usd": proposal,
                        "confidence": 0.95,
                        "source_page": 2,
                        "source_label": "retry",
                        "evidence": "stronger supplied evidence",
                    }
                ]
                merged, recovered, replaced = pipeline.merge_retry_rows(
                    first_rows,
                    retry_rows,
                    [item] if scope == "missing" else [],
                    [item] if scope == "replace" else [],
                )

                if scope == "outside":
                    self.assertEqual(merged[0]["answer_m_usd"], first_value)
                    self.assertEqual(recovered, [])
                    self.assertEqual(replaced, [])
                else:
                    self.assertEqual(merged[0]["answer_m_usd"], proposal)
                    self.assertEqual(recovered, [item] if scope == "missing" else [])
                    self.assertEqual(replaced, [item] if scope == "replace" else [])

    def test_complete_packet_nulls_are_decided_absences_and_never_retried(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {
            "choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}],
            "usage": {},
        }
        passing = {
            "checks": [],
            "total_identities": 1,
            "evaluated": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "consistency": 100.0,
            "failed_identities": [],
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
        first = {
            "choices": [{"message": {"content": json.dumps(_payload_with_nulls(only_total))}}],
            "usage": {},
        }
        retry_payload = _payload_with_nulls(only_total)
        for row in retry_payload["rows"]:
            if row["item"] == "Total Assets":
                row["answer_m_usd"] = 9219
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }
        passing = {
            "checks": [],
            "total_identities": 1,
            "evaluated": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 1,
            "consistency": None,
            "failed_identities": [],
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
        first = {
            "choices": [{"message": {"content": json.dumps(_payload())}}],
            "usage": {},
        }
        retry_payload = _payload_with_nulls({row["item"] for row in ASSET_SCHEMA})
        retry = {
            "choices": [{"message": {"content": json.dumps(retry_payload)}}],
            "usage": {},
        }

        result, model_call, _ = self._run(
            [(first, 0.1), (retry, 0.2)], strategy=_FakeCompletePacketS3Strategy()
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertTrue(result["evidence_retry"]["attempted"])
        self.assertEqual(result["evidence_retry"]["missing_rows"], [])
        self.assertTrue(result["evidence_retry"]["failed_identity_rows"])

    def test_strategy3_failed_evidence_retry_keeps_first_pass_values(self):
        nulls = {"Cash & Cash Equivalents", "Accounts Receivable - Trade"}
        first = {
            "choices": [{"message": {"content": json.dumps(_payload_with_nulls(nulls))}}],
            "usage": {},
        }

        result, model_call, _ = self._run(
            [(first, 0.1), RuntimeError("provider unavailable")],
            strategy=_FakeS3Strategy(),
        )

        self.assertEqual(model_call.call_count, 2)
        self.assertTrue(result["evidence_retry"]["attempted"])
        self.assertIn("provider unavailable", result["evidence_retry"]["error"])
        by_item = {row["item"]: row for row in result["rows"]}
        self.assertIsNone(by_item["Cash & Cash Equivalents"]["answer_m_usd"])

    def test_contract_failure_gets_at_most_one_contextual_repair_call(self):
        invalid = {"choices": [{"message": {"content": "{}"}}], "usage": {}}
        valid = {
            "choices": [{"message": {"content": json.dumps(_payload())}}],
            "usage": {},
        }
        result, model_call, _ = self._run([(invalid, 0.1), (valid, 0.2)])

        self.assertEqual(model_call.call_count, 2)
        self.assertEqual(result["contract_repair_attempts"], 1)
        repair_messages = model_call.call_args_list[1].kwargs["messages"]
        self.assertEqual(
            [message["role"] for message in repair_messages],
            ["system", "user", "assistant", "user"],
        )
        self.assertIn("contract errors", repair_messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
