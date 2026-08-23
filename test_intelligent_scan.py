"""Focused tests for Strategy 3's deterministic complete-page gate."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import extraction
from intelligent_scan import score_pages, select_evidence_pages, select_retry_pages


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

    def test_japanese_balance_sheet_outranks_governance(self):
        pages = [
            (1, "コーポレートガバナンス 取締役 役員の状況"),
            (2, "連結貸借対照表 資産の部 流動資産 現金及び預金 売掛金 固定資産 資産合計"),
            (3, "事業の状況 従業員 株主総会"),
        ]
        ranked = score_pages(pages, pages_with_tables=[2])

        self.assertEqual(2, ranked[0]["page"])
        self.assertIn("貸借対照表", ranked[0]["japanese_accounting_hits"])

    def test_japanese_loan_maturity_table_is_critical_evidence(self):
        pages = [
            (1, "連結貸借対照表 資産の部 現金及び預金 資産合計"),
            (2, "金融商品関係 金銭債権の連結決算日後の償還予定額 １年以内 長期貸付金 2,156"),
            (3, "事業の状況"),
        ]
        ranked = score_pages(pages, pages_with_tables=[1, 2])
        maturity = next(item for item in ranked if item["page"] == 2)

        self.assertIn("japanese_loan_maturity", maturity["critical_evidence"])


class RetryPageSelectionTests(unittest.TestCase):
    def test_retry_excludes_sent_pages_caps_at_three_and_targets_missing_terms(self):
        pages = [
            (1, "# Consolidated Balance Sheets\n| Cash | 100 |\n| Total assets | 900 |"),
            (2, "# Corporate Governance\nBoard of directors."),
            (3, "# Note 5. Inventories\nInventories raw materials finished goods 120"),
            (4, "# Note 7. Receivables\nAccounts receivable trade allowance 300"),
            (5, "# Note 9. Property\nLand buildings machinery accumulated depreciation"),
            (6, "# Officers\nExecutive compensation shareholder proposal"),
        ]
        selected, diagnostics = select_retry_pages(
            pages,
            missing_items=["Inventories, Net", "Accounts Receivable - Trade"],
            exclude_pages=[1],
            maximum_pages=3,
        )

        chosen = [page for page, _ in selected]
        self.assertNotIn(1, chosen)
        self.assertLessEqual(len(chosen), 3)
        self.assertIn(3, chosen)
        self.assertIn(4, chosen)
        self.assertEqual(chosen, sorted(chosen))
        self.assertEqual(diagnostics["retry_pages"], [item["page"] for item in diagnostics["retry_scores"]])

    def test_retry_reports_when_every_page_was_already_sent(self):
        selected, diagnostics = select_retry_pages(
            [(1, "Balance sheet"), (2, "Notes")],
            missing_items=["Inventories, Net"],
            exclude_pages=[1, 2],
        )
        self.assertEqual(selected, [])
        self.assertEqual(diagnostics["reason"], "no_remaining_pages")


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
    def __init__(self, rendered: list[int], page_count: int = 0) -> None:
        self.rendered = rendered
        self.page_count = page_count

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __getitem__(self, index: int):
        return _Page(self.rendered, index)


class _TextPage(_Page):
    def __init__(self, rendered: list[int], index: int, text: str) -> None:
        super().__init__(rendered, index)
        self.text = text

    def get_text(self, kind: str):
        if kind != "text":
            raise AssertionError(kind)
        return self.text


class _TextDocument(_Document):
    def __init__(self, rendered: list[int], texts: list[str]) -> None:
        super().__init__(rendered, page_count=len(texts))
        self.texts = texts

    def __getitem__(self, index: int):
        return _TextPage(self.rendered, index, self.texts[index])


class StrategyThreeExtractionTests(unittest.TestCase):
    def test_text_based_japanese_pdf_uses_embedded_text_instead_of_ocr(self):
        native = [
            "表紙 有価証券報告書",
            "連結貸借対照表 資産の部 流動資産 現金及び預金 売掛金 固定資産 資産合計 100",
            "有形固定資産 建物及び構築物 機械装置 土地 減価償却累計額 50",
            "投資その他の資産 投資有価証券 敷金及び保証金 繰延税金資産 25",
        ]
        pages = [
            types.SimpleNamespace(page=index, markdown="", needs_ocr=True)
            for index in range(len(native))
        ]
        extracted_pages = types.SimpleNamespace(
            pages=pages, pages_needing_ocr=[1, 2, 3, 4],
            ocr_reasons_by_page=[], pages_with_tables=[2, 3, 4],
            pages_with_columns=[], is_complex=False,
        )
        classification = types.SimpleNamespace(
            pdf_type="text_based", confidence=0.99, pages_needing_ocr=[],
            has_encoding_issues=False,
        )
        inspector = types.SimpleNamespace(
            extract_pages_markdown=lambda _path: extracted_pages,
            detect_pdf=lambda _path: classification,
        )
        rendered: list[int] = []
        pymupdf = types.SimpleNamespace(
            Matrix=lambda x, y: (x, y), open=lambda _path: _TextDocument(rendered, native)
        )
        with patch.dict(sys.modules, {"pdf_inspector": inspector, "pymupdf": pymupdf}), patch.object(
            extraction, "_local_ocr_markdown"
        ) as ocr:
            result = extraction.extract_with_intelligent_scanning_gate(Path("report.pdf"))

        ocr.assert_not_called()
        self.assertEqual([], rendered)
        self.assertEqual(4, result.diagnostics["native_text_fallback_page_count"])
        self.assertEqual(0, result.diagnostics["ocr_page_count"])
        self.assertIn(2, result.diagnostics["selected_pages"])

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

        pymupdf = types.SimpleNamespace(Matrix=Matrix, open=lambda _path: _Document(rendered, page_count=len(pages)))
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
