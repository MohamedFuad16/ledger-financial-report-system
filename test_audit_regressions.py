"""Regression tests for the 2026-08-24 backend audit fixes."""
import json
import math
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


class FakePage:
    def __init__(self, page_number=None, page=None, markdown="body", needs_ocr=False):
        if page_number is not None:
            self.page_number = page_number
        if page is not None:
            self.page = page
        self.markdown = markdown
        self.needs_ocr = needs_ocr


class FakeDocument:
    def __init__(self, page_count):
        self.page_count = page_count


class CanonicalInventoryTest(unittest.TestCase):
    def test_missing_duplicate_and_out_of_range_pages_are_quarantined(self):
        from extraction import _canonical_inspector_pages
        raw = [FakePage(page_number=1), FakePage(page_number=1), FakePage(page_number=3), FakePage(page_number=9)]
        inventory, anomalies = _canonical_inspector_pages(raw, FakeDocument(4))
        self.assertEqual([number for number, _ in inventory], [1, 2, 3, 4])
        self.assertIsNone(dict(inventory)[2], "an omitted page must appear with no inspector object")
        self.assertIsNone(dict(inventory)[4])
        self.assertEqual(anomalies["duplicate_pages"], [1])
        self.assertEqual(anomalies["out_of_range_pages"], [9])
        self.assertEqual(anomalies["missing_pages"], [2, 4])


class FiscalYearAuthorityTest(unittest.TestCase):
    def test_pinned_corpus_year_beats_model_year(self):
        source = Path("pipeline.py").read_text(encoding="utf-8")
        self.assertIn('fiscal_year = pinned_year or result.detected_fiscal_year', source)
        self.assertIn('kept the screened corpus year', source)


class NonFiniteRejectionTest(unittest.TestCase):
    def test_asset_row_rejects_non_finite_answers(self):
        from models import AssetRow
        from pydantic import ValidationError
        base = {"item": "Total Assets", "confidence": 0.9}
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValidationError):
                AssetRow(answer_m_usd=bad, **base)
        AssetRow(answer_m_usd=1.5, **base)
        AssetRow(answer_m_usd=None, **base)

    def test_approval_normalization_rejects_non_finite(self):
        from corpus import manifest as corpus_manifest
        source = Path("corpus/manifest.py").read_text(encoding="utf-8")
        self.assertIn("math.isfinite(normalized_answer)", source)
        self.assertTrue(hasattr(corpus_manifest, "math"))


class CorruptArtifactIsolationTest(unittest.TestCase):
    def test_one_corrupt_prediction_does_not_break_list_runs(self):
        import pipeline
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            good = runs / "CompanyA" / "FY2024" / "S1_20260101T000000Z_001"
            good.mkdir(parents=True)
            (good / "prediction.json").write_text(json.dumps({
                "run_id": good.name, "strategy": "s1", "experiment": "no_ocr",
                "rows": [], "company": "CompanyA", "fiscal_year": "2024",
            }), encoding="utf-8")
            bad = runs / "CompanyB" / "FY2024" / "S1_20260101T000000Z_002"
            bad.mkdir(parents=True)
            (bad / "prediction.json").write_text(json.dumps({
                "run_id": bad.name, "strategy": "s1", "experiment": "no_ocr",
                "rows": [{"item": "Total Assets", "answer_m_usd": 1, "confidence": "not-a-number"}],
            }), encoding="utf-8")
            with mock.patch.object(pipeline, "RUNS_DIR", runs):
                pipeline._SUMMARY_CACHE.clear()
                summaries = pipeline.list_runs(None)
        self.assertEqual([entry["run_id"] for entry in summaries], [good.name])


class CacheEvictionTest(unittest.TestCase):
    def test_deleting_a_run_evicts_its_cached_summary(self):
        import pipeline
        pipeline._SUMMARY_CACHE["/tmp/fake_run/prediction.json"] = (0.0, 0, "legacy-public", {})
        pipeline.invalidate_run_summaries(Path("/tmp/fake_run"))
        self.assertNotIn("/tmp/fake_run/prediction.json", pipeline._SUMMARY_CACHE)


class ReadOnlyGateTest(unittest.TestCase):
    def test_mutating_control_plane_is_blocked_when_readonly(self):
        import importlib, os
        os.environ["LEDGER_PUBLIC_READONLY"] = "1"
        try:
            import server as server_module
            importlib.reload(server_module)
            client = server_module.app.test_client()
            blocked = client.post("/api/prompt", json={"prompt": "x"})
            self.assertEqual(blocked.status_code, 403)
            # Run deletion is workspace-scoped server-side, so it stays open
            # to visitors even in read-only mode (they delete only their own).
            allowed_delete = client.delete("/api/runs/all")
            self.assertNotEqual(allowed_delete.status_code, 403)
            allowed = client.get("/api/benchmark-runs")
            self.assertEqual(allowed.status_code, 200)
        finally:
            os.environ.pop("LEDGER_PUBLIC_READONLY", None)
            importlib.reload(server_module)


class QuotaClassificationTest(unittest.TestCase):
    """A transient 429 must never be read as an exhausted allowance.

    _quota_message used to match its markers against the whole serialized error
    dict, so a request id containing "1308", a key named "quota_reset_at", or
    the word "credits" in prose all raised QuotaExhaustedError. The callers in
    server.py then stop scheduling every remaining file, abandoning a paid batch.
    """

    def test_transient_429_is_not_mistaken_for_exhausted_quota(self):
        from api_client import _quota_message
        for label, body in {
            "request id containing the quota code": {
                "error": {"message": "Too Many Requests", "request_id": "req_a1308bf2"}
            },
            "a key name containing 'quota'": {
                "error": {"message": "Too Many Requests", "metadata": {"quota_reset_at": "later"}}
            },
            "'credits' used in marketing prose": {
                "error": {"message": "Rate limit; upgrade for more credits"}
            },
            "a bare rate limit": {"error": {"message": "Too Many Requests"}},
        }.items():
            with self.subTest(label):
                self.assertIsNone(_quota_message(body))

    def test_genuine_exhaustion_is_still_detected(self):
        from api_client import _quota_message
        self.assertEqual(_quota_message({"error": {"message": "usage limit reached"}}), "usage limit reached")
        self.assertEqual(_quota_message({"error": {"message": "Insufficient balance"}}), "Insufficient balance")
        # The numeric code is matched on the code field, not as a substring.
        self.assertEqual(_quota_message({"error": {"code": "1308", "message": "Spent"}}), "Spent")


class CodeFenceTest(unittest.TestCase):
    """A fence sharing a line with the payload must not delete the payload.

    Dropping the first line wholesale returned "" for ```json {...} on one line,
    so a valid 27-row reply was reported as "Model output was not valid JSON"
    and burned a contract-repair call.
    """

    def test_fence_variants_all_yield_the_payload(self):
        from api_client import _strip_code_fence
        for label, raw in {
            "payload on the opening fence line": '```json {"a": 1}\n```',
            "conventional multi-line fence": '```json\n{"a": 1}\n```',
            "fence with no language tag": '```\n{"a": 1}\n```',
            "no fence at all": '{"a": 1}',
        }.items():
            with self.subTest(label):
                self.assertEqual(_strip_code_fence(raw), '{"a": 1}')

    def test_closing_fence_glued_to_the_payload(self):
        from api_client import _strip_code_fence
        self.assertEqual(_strip_code_fence('```json {"a":1}```'), '{"a":1}')


class OversizedNumberTest(unittest.TestCase):
    """An integer too large for a double must fail the contract, not the run.

    json.loads keeps an oversized literal as an arbitrary-precision int, and
    float() on it raises OverflowError — not a ValidationError — so it escaped
    validate_extraction uncaught and bypassed the bounded repair path.
    """

    def test_oversized_integer_raises_a_contract_error(self):
        import models
        rows = [
            {"item": item, "answer_m_usd": 1.0, "confidence": 0.9}
            for item in models.CANONICAL_ITEMS
        ]
        rows[0]["answer_m_usd"] = json.loads("1" + "0" * 400)
        with self.assertRaises(models.SchemaValidationError):
            models.validate_extraction({"detected_fiscal_year": "2022", "rows": rows})


class ReasoningPrecedenceTest(unittest.TestCase):
    """LLM_* must win over the legacy GLM_* name, as it does for every other setting."""

    def test_current_generation_name_wins_over_legacy(self):
        import settings
        with mock.patch.dict(
            os.environ,
            {"GLM_ENABLE_REASONING": "true", "LLM_ENABLE_REASONING": "false"},
            clear=False,
        ):
            os.environ.pop("LLM_REASONING_EFFORT", None)
            self.assertEqual(settings._reasoning_effort_from_env(), "none")


class CacheAccountingTest(unittest.TestCase):
    """An accounting helper must not discard an already-paid-for extraction."""

    def test_zero_cached_tokens_is_reported_rather_than_omitted(self):
        from providers import cache_usage
        usage = {"prompt_tokens": 100, "prompt_tokens_details": {"cached_tokens": 0}}
        self.assertEqual(cache_usage(usage)["cache_hit_rate"], 0.0)

    def test_string_token_counts_do_not_raise(self):
        from providers import cache_usage
        usage = {"prompt_tokens": "100", "prompt_tokens_details": {"cached_tokens": "40"}}
        self.assertEqual(cache_usage(usage)["cache_hit_rate"], 40.0)


if __name__ == "__main__":
    unittest.main()
