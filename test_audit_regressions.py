"""Regression tests for the 2026-08-24 backend audit fixes."""

import io
import json
import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from werkzeug.datastructures import FileStorage


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

        raw = [
            FakePage(page_number=1),
            FakePage(page_number=1),
            FakePage(page_number=3),
            FakePage(page_number=9),
        ]
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
        self.assertIn("fiscal_year = pinned_year or result.detected_fiscal_year", source)
        self.assertIn("kept the screened corpus year", source)


class NonFiniteRejectionTest(unittest.TestCase):
    def test_asset_row_rejects_non_finite_answers(self):
        from pydantic import ValidationError

        from models import AssetRow

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
            (good / "prediction.json").write_text(
                json.dumps(
                    {
                        "run_id": good.name,
                        "strategy": "s1",
                        "experiment": "no_ocr",
                        "rows": [],
                        "company": "CompanyA",
                        "fiscal_year": "2024",
                    }
                ),
                encoding="utf-8",
            )
            bad = runs / "CompanyB" / "FY2024" / "S1_20260101T000000Z_002"
            bad.mkdir(parents=True)
            (bad / "prediction.json").write_text(
                json.dumps(
                    {
                        "run_id": bad.name,
                        "strategy": "s1",
                        "experiment": "no_ocr",
                        "rows": [
                            {
                                "item": "Total Assets",
                                "answer_m_usd": 1,
                                "confidence": "not-a-number",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(pipeline, "RUNS_DIR", runs):
                pipeline._SUMMARY_CACHE.clear()
                summaries = pipeline.list_runs(None)
        self.assertEqual([entry["run_id"] for entry in summaries], [good.name])


class CacheEvictionTest(unittest.TestCase):
    def test_deleting_a_run_evicts_its_cached_summary(self):
        import pipeline

        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "fake_run"
            cache_key = str(run_dir / "prediction.json")
            pipeline._SUMMARY_CACHE[cache_key] = (0.0, 0, "legacy-public", {})
            pipeline.invalidate_run_summaries(run_dir)
            self.assertNotIn(cache_key, pipeline._SUMMARY_CACHE)


class ReadOnlyGateTest(unittest.TestCase):
    def test_mutating_control_plane_is_blocked_when_readonly(self):
        import importlib
        import os

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


class BenchmarkSummaryTest(unittest.TestCase):
    def test_final_strategy3_summary_is_available_without_row_level_gold(self):
        import server as server_module

        response = server_module.app.test_client().get("/api/benchmark-summary")
        self.assertEqual(response.status_code, 200)
        summary = response.get_json()["summary"]
        # Cohort size is data, not a contract: pinning it here made the suite
        # fail whenever the corpus legitimately changed, and it would not have
        # caught the real defect, which was a summary asserting figures no run
        # supported. Assert the invariants that make the number trustworthy.
        for key in (
            "companies",
            "documents",
            "exact_rows",
            "scored_rows",
            "row_micro_accuracy",
            "document_macro_accuracy",
            "field_coverage",
            "exact_documents",
        ):
            self.assertIn(key, summary)
        self.assertGreater(summary["documents"], 0)
        self.assertGreaterEqual(summary["documents"], summary["companies"])
        self.assertLessEqual(summary["exact_documents"], summary["documents"])
        self.assertLessEqual(summary["exact_rows"], summary["scored_rows"])
        for metric in ("row_micro_accuracy", "document_macro_accuracy", "field_coverage"):
            self.assertGreaterEqual(summary[metric], 0.0)
            self.assertLessEqual(summary[metric], 100.0)
        # The headline must agree with its own row counts.
        self.assertAlmostEqual(
            summary["row_micro_accuracy"],
            summary["exact_rows"] / summary["scored_rows"] * 100,
            places=3,
        )
        # The endpoint publishes aggregates only; row-level gold never leaves it.
        self.assertNotIn("rows", summary)
        self.assertNotIn("answers", summary)


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
                "error": {
                    "message": "Too Many Requests",
                    "metadata": {"quota_reset_at": "later"},
                }
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

        self.assertEqual(
            _quota_message({"error": {"message": "usage limit reached"}}),
            "usage limit reached",
        )
        self.assertEqual(
            _quota_message({"error": {"message": "Insufficient balance"}}),
            "Insufficient balance",
        )
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

        rows = [{"item": item, "answer_m_usd": 1.0, "confidence": 0.9} for item in models.CANONICAL_ITEMS]
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

        usage = {
            "prompt_tokens": "100",
            "prompt_tokens_details": {"cached_tokens": "40"},
        }
        self.assertEqual(cache_usage(usage)["cache_hit_rate"], 40.0)


class UploadTrustBoundaryTest(unittest.TestCase):
    def test_non_pdf_bytes_are_rejected_before_any_file_is_persisted(self):
        import pipeline

        upload = FileStorage(stream=io.BytesIO(b"not a pdf"), filename="report.pdf")
        with TemporaryDirectory() as tmp, mock.patch.object(pipeline, "UPLOAD_DIR", Path(tmp)):
            with self.assertRaisesRegex(ValueError, "not a valid PDF"):
                pipeline.save_upload(upload)
            self.assertEqual([], list(Path(tmp).rglob("*")))

    def test_staged_upload_expiry_removes_only_temporary_uploads(self):
        import server

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            temporary = root / "temporary" / "report.pdf"
            corpus = root / "corpus" / "report.pdf"
            temporary.parent.mkdir()
            corpus.parent.mkdir()
            temporary.write_bytes(b"%PDF-1.7")
            corpus.write_bytes(b"%PDF-1.7")
            expired_at = time.time() - server.STAGED_TTL_SECONDS - 1
            with mock.patch.dict(
                server.STAGED,
                {
                    "temporary": {
                        "path": str(temporary),
                        "staged_at": expired_at,
                        "temporary_upload": True,
                    },
                    "corpus": {
                        "path": str(corpus),
                        "staged_at": expired_at,
                        "temporary_upload": False,
                    },
                },
                clear=True,
            ):
                server._prune_staged()
                self.assertEqual({}, server.STAGED)
            self.assertFalse(temporary.exists())
            self.assertTrue(corpus.exists())


class ApiTrustBoundaryTest(unittest.TestCase):
    def test_health_contract_exposes_no_environment_metadata(self):
        import server

        with mock.patch.dict(os.environ, {"AWS_REGION": "ap-northeast-1"}, clear=False):
            response = server.app.test_client().get("/api/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"ok": True, "service": "ledger-backend"}, response.get_json())

    def test_json_endpoints_reject_non_object_payloads(self):
        import server

        client = server.app.test_client()
        with mock.patch.object(server, "PUBLIC_READONLY", False):
            for endpoint in ("/api/settings", "/api/runtime-settings", "/api/prompt"):
                with self.subTest(endpoint=endpoint):
                    response = client.post(endpoint, json=["not", "an", "object"])
                    self.assertEqual(400, response.status_code)
                    self.assertEqual("A JSON object is required.", response.get_json()["error"])

    def test_responses_include_browser_security_headers(self):
        import server

        response = server.app.test_client().get("/api/health")
        self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])
        self.assertEqual("DENY", response.headers["X-Frame-Options"])
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_masked_credentials_do_not_reveal_key_fragments(self):
        import server

        secret = "prefix-private-value-suffix"
        masked = server.mask_key(secret)
        self.assertEqual("Configured", masked)
        self.assertNotIn("prefix", masked)
        self.assertNotIn("suffix", masked)

    def test_client_errors_redact_credentials_and_local_paths(self):
        import server

        secret = "TEST_PRIVATE_VALUE_123456"
        private_path = "/" + "Users/reviewer/private/report.pdf"
        error = RuntimeError(f"Bearer {secret} failed at {private_path}; api_key={secret}")
        with mock.patch.object(
            server,
            "current_settings",
            return_value={"api_key": secret, "firecrawl_api_key": ""},
        ):
            message = server.safe_client_error(error)
        self.assertNotIn(secret, message)
        self.assertNotIn(private_path, message)
        self.assertIn("[redacted]", message)
        self.assertIn("[local path]", message)


class BenchmarkFeedIsolationTest(unittest.TestCase):
    """A visitor's demo run must never move the published benchmark numbers."""

    def test_feed_serves_only_the_benchmark_workspace(self):
        import pipeline
        from pipeline import BENCHMARK_WORKSPACE_ID

        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            sha = "a" * 64
            rows = [{"item": "Total Assets", "answer_m_usd": 1.0, "confidence": 0.99}]

            def write(run_id, workspace):
                run = runs / "CompanyA" / "FY2024" / run_id
                run.mkdir(parents=True)
                (run / "prediction.json").write_text(
                    json.dumps(
                        {
                            "run_id": run_id,
                            "strategy": "s3",
                            "experiment": "intelligent_scan",
                            "company": "CompanyA",
                            "fiscal_year": "2024",
                            "currency": "JPY",
                            "source_pdf_sha256": sha,
                            "rows": rows,
                            "workspace_id": workspace,
                        }
                    ),
                    encoding="utf-8",
                )

            write("S3_20260101T000000Z_001", BENCHMARK_WORKSPACE_ID)
            write("S3_20260101T000000Z_002", "ws_visitor_browser_workspace")

            with mock.patch.object(pipeline, "RUNS_DIR", runs):
                pipeline._SUMMARY_CACHE.clear()
                official = pipeline.list_runs(BENCHMARK_WORKSPACE_ID)
                everyone = pipeline.list_runs(None)

        self.assertEqual(["S3_20260101T000000Z_001"], [entry["run_id"] for entry in official])
        self.assertEqual(
            2,
            len(everyone),
            "the visitor run still exists; it is only excluded from the feed",
        )

    def test_the_feed_endpoint_asks_for_the_benchmark_workspace(self):
        source = Path("server.py").read_text(encoding="utf-8")
        feed = source.split("def get_benchmark_runs")[1].split("@app.route")[0]
        self.assertIn("list_runs(BENCHMARK_WORKSPACE_ID)", feed)
        self.assertNotIn("list_runs(None)", feed)


if __name__ == "__main__":
    unittest.main()
