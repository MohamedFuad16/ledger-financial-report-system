"""Focused contract tests for Strategy 2's adaptive pdf-inspector OCR arm."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import extraction


class _Pixmap:
    def tobytes(self, kind: str) -> bytes:
        if kind != "png":
            raise AssertionError(f"expected PNG rendering, got {kind}")
        return b"rendered-page"


class _RenderedPage:
    def __init__(self, matrices: list[tuple[float, float]]) -> None:
        self.matrices = matrices

    def get_pixmap(self, *, matrix, alpha: bool):
        if alpha:
            raise AssertionError("OCR input must not render an alpha channel")
        self.matrices.append((matrix.x, matrix.y))
        return _Pixmap()


class _Document:
    def __init__(self, matrices: list[tuple[float, float]], page_count: int = 0) -> None:
        self.matrices = matrices
        self.page_count = page_count

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __getitem__(self, _index: int):
        return _RenderedPage(self.matrices)


class PdfInspectorAdaptiveOcrTests(unittest.TestCase):
    def _modules(self, pages):
        matrices: list[tuple[float, float]] = []
        inspector = types.SimpleNamespace(
            extract_pages_markdown=lambda _path: types.SimpleNamespace(pages=pages),
            detect_pdf=lambda _path: types.SimpleNamespace(
                pdf_type="mixed",
                has_encoding_issues=False,
                pages_needing_ocr=[],
            ),
        )

        class Matrix:
            def __init__(self, x: float, y: float) -> None:
                self.x = x
                self.y = y

        pymupdf = types.SimpleNamespace(
            Matrix=Matrix,
            open=lambda _path: _Document(matrices, page_count=len(pages)),
        )
        return inspector, pymupdf, matrices

    def test_only_classifier_marked_page_is_rendered_at_200_dpi(self):
        pages = [
            types.SimpleNamespace(page=0, markdown="Native Rust page one", needs_ocr=False),
            types.SimpleNamespace(page=1, markdown="Image placeholder", needs_ocr=True),
        ]
        inspector, pymupdf, matrices = self._modules(pages)
        ocr_calls: list[dict] = []

        def fake_ocr(image_bytes: bytes, **kwargs) -> str:
            ocr_calls.append({"image_bytes": image_bytes, **kwargs})
            return "Local OCR page two"

        with (
            patch.dict(sys.modules, {"pdf_inspector": inspector, "pymupdf": pymupdf}),
            patch.object(extraction, "_local_ocr_markdown", side_effect=fake_ocr),
        ):
            result = extraction.extract_with_pdf_inspector_ocr(Path("annual-report.pdf"))

        self.assertEqual(1, len(ocr_calls))
        self.assertEqual(2, ocr_calls[0]["page_no"])
        self.assertEqual(b"rendered-page", ocr_calls[0]["image_bytes"])
        self.assertEqual([(200.0 / 72.0, 200.0 / 72.0)], matrices)
        self.assertIn("--- PAGE 1 ---\nNative Rust page one", result.text)
        self.assertIn("--- PAGE 2 ---\nLocal OCR page two", result.text)
        self.assertEqual(1, result.diagnostics["ocr_page_count"])
        self.assertEqual(
            "pdf_inspector_native_rust",
            result.diagnostics["page_provenance"][0]["source"],
        )
        self.assertEqual("rapidocr_local", result.diagnostics["page_provenance"][1]["source"])
        self.assertEqual(200, result.diagnostics["page_provenance"][1]["render_dpi"])

    def test_text_only_pdf_does_not_require_an_ocr_api_key(self):
        pages = [types.SimpleNamespace(page=0, markdown="Readable native text", needs_ocr=False)]
        inspector, pymupdf, matrices = self._modules(pages)
        with (
            patch.dict(sys.modules, {"pdf_inspector": inspector, "pymupdf": pymupdf}),
            patch.object(extraction, "_local_ocr_markdown") as ocr,
        ):
            result = extraction.extract_with_pdf_inspector_ocr(Path("text-report.pdf"), ocr_context={})

        ocr.assert_not_called()
        self.assertEqual([], matrices)
        self.assertEqual(0, result.diagnostics["ocr_page_count"])
        self.assertEqual("Readable native text", result.text.splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
