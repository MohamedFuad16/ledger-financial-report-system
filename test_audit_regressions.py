"""Regression tests for the 2026-08-24 backend audit fixes."""
import json
import math
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
            blocked = client.delete("/api/runs/all")
            self.assertEqual(blocked.status_code, 403)
            allowed = client.get("/api/benchmark-runs")
            self.assertEqual(allowed.status_code, 200)
        finally:
            os.environ.pop("LEDGER_PUBLIC_READONLY", None)
            importlib.reload(server_module)


if __name__ == "__main__":
    unittest.main()
