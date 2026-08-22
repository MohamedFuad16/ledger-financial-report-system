"""Focused tests for Strategy 3's deterministic complete-page gate."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import extraction
from intelligent_scan import score_pages, select_evidence_pages


class IntelligentScanningGateTests(unittest.TestCase):
    def test_financial_table_outranks_governance_boilerplate(self):
        pages = [
            (1, "# Corporate Governance\nBoard of directors and executive compensation."),
            (2, "# Consolidated Balance Sheets\n| Assets | 2025 |\n| Cash and cash equivalents | 100 |\n| Total assets | 900 |"),
            (3, "# Property, Plant and Equipment\nLand buildings machinery construction in progress accumulated depreciation."),
        ]
        ranked = score_pages(pages, pages_with_tables=[2], pages_with_columns=[2])
        self.assertEqual(2, ranked[0]["page"])
        self.assertTrue(ranked[0]["table_signal"])
        self.assertGreater(ranked[0]["score"], ranked[-1]["score"])

    def test_selector_keeps_only_complete_page_units(self):
        pages = [
            (number, f"# Page {number}\nBalance sheet assets cash receivables inventories {number * 100}")
            for number in range(1, 9)
        ]
        selected, diagnostics = select_evidence_pages(pages, pages_with_tables=[2, 4, 6])
        self.assertGreaterEqual(len(selected), 3)
        self.assertLessEqual(len(selected), 5)
        self.assertEqual(diagnostics["selected_pages"], sorted(diagnostics["selected_pages"]))
        for page, body in selected:
            self.assertEqual(next(text for number, text in pages if number == page), body)

    def test_right_of_use_note_receives_critical_schema_evidence_bonus(self):
        pages = [
            (1, "# Financial Note\nAssets current financial other amounts 100 200 300"),
            (2, "# Note 18. Leases\nRight of use assets | Other assets | 516"),
        ]
        ranked = score_pages(pages, pages_with_tables=[1, 2])
        lease = next(item for item in ranked if item["page"] == 2)

        self.assertIn("right_of_use_assets", lease["critical_evidence"])
        self.assertEqual(2, ranked[0]["page"])


class _Pixmap:
    def tobytes(self, kind: str) -> bytes:
        if kind != "png":
            raise AssertionError(kind)
        return b"page-image"


class _Page:
    def __init__(self, rendered: list[int], index: int) -> None:
        self.rendered = rendered
        self.index = index

    def get_pixmap(self, *, matrix, alpha: bool):
        self.rendered.append(self.index)
        self.matrix = matrix
        self.alpha = alpha
        return _Pixmap()


class _Document:
    def __init__(self, rendered: list[int]) -> None:
        self.rendered = rendered

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __getitem__(self, index: int):
        return _Page(self.rendered, index)


class StrategyThreeExtractionTests(unittest.TestCase):
    def test_pdf_inspector_routes_ocr_then_gate_selects_unified_pages(self):
        pages = [
            types.SimpleNamespace(page=0, markdown="# Cover\nAnnual report", needs_ocr=False),
            types.SimpleNamespace(page=1, markdown="", needs_ocr=True),
            types.SimpleNamespace(page=2, markdown="# Consolidated Balance Sheets\n| Total assets | 900 |", needs_ocr=False),
            types.SimpleNamespace(page=3, markdown="# Property Plant and Equipment\nLand buildings machinery depreciation", needs_ocr=False),
            types.SimpleNamespace(page=4, markdown="# Notes\nCash receivables inventory other current assets", needs_ocr=False),
            types.SimpleNamespace(page=5, markdown="# Governance\nBoard of directors", needs_ocr=False),
        ]
        extracted_pages = types.SimpleNamespace(
            pages=pages,
            pages_needing_ocr=[2],
            ocr_reasons_by_page=[types.SimpleNamespace(page=2, reasons=["scanned"])],
            pages_with_tables=[2, 3],
            pages_with_columns=[3],
            is_complex=True,
        )
        classification = types.SimpleNamespace(
            pdf_type="mixed",
            confidence=0.91,
            pages_needing_ocr=[2],
            has_encoding_issues=False,
        )
        inspector = types.SimpleNamespace(
            extract_pages_markdown=lambda _path: extracted_pages,
            detect_pdf=lambda _path: classification,
        )
        rendered: list[int] = []

        class Matrix:
            def __init__(self, x: float, y: float) -> None:
                self.x, self.y = x, y

        pymupdf = types.SimpleNamespace(Matrix=Matrix, open=lambda _path: _Document(rendered))
        with patch.dict(sys.modules, {"pdf_inspector": inspector, "pymupdf": pymupdf}), patch.object(
            extraction,
            "_local_ocr_markdown",
            return_value="# Intangible Assets\nGoodwill and intangible assets 400",
        ) as ocr:
            result = extraction.extract_with_intelligent_scanning_gate(
                Path("report.pdf"),
            )

        ocr.assert_called_once()
        self.assertEqual([1], rendered)
        self.assertEqual([2], result.diagnostics["selected_pages"][:1])
        self.assertIn("--- PAGE 2 ---\n# Intangible Assets", result.text)
        self.assertEqual(1, result.diagnostics["ocr_page_count"])
        self.assertEqual("mixed", result.diagnostics["document_type"])
        self.assertGreaterEqual(result.readable_pages, 3)
        self.assertLessEqual(result.readable_pages, 5)


if __name__ == "__main__":
    unittest.main()
