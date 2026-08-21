"""
PDF → text conversion for each strategy, plus the text-health checks that tell
us when a document simply cannot be read as text.

Every strategy returns the same ``ExtractedText`` shape so the rest of the
pipeline is strategy-agnostic.
"""

from __future__ import annotations

import base64
import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader

from intelligent_scan import select_evidence_pages

# Characters that carry no information but do consume tokens and confuse models.
_INVISIBLE = dict.fromkeys(
    map(ord, "\u200b\u200c\u200d\ufeff\u00ad"), None
)

_REPLACEMENTS = {
    "\u00a0": " ",   # non-breaking space (3M's 2020 report is full of these)
    "\u2007": " ",   # figure space
    "\u202f": " ",   # narrow no-break space
    "\u2009": " ",   # thin space
    "\u2212": "-",   # unicode minus
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\ufb01": "fi",  # fi ligature
    "\ufb02": "fl",  # fl ligature
}


def normalize_text(text: str) -> str:
    """
    Make extracted page text safe to hand to an LLM.

    Non-breaking spaces, ligatures and unicode dashes are folded to ASCII so that
    token-level pattern matching ("Total current assets", "-16,820") behaves the
    same across reports produced by different PDF toolchains.
    """
    if not text:
        return ""
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = text.translate(_INVISIBLE)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{4,}", "\n\n\n", text)


# A page whose text layer is this badly mangled is reported as unreadable.
GARBLE_THRESHOLD = 0.15

# Glyph-shifted text mixes letters and digits inside single tokens - "3M Company
# and Subsidiaries" arrives from Docling as "$ B@C4AL 4A7 *H5F<7<4E<8F". Real
# text almost never does: a financial table has "United" (letters) and "3,861"
# (digits) as separate tokens, not "B@C4AL".
#
# Measured on this corpus: mojibake pages score 0.38-0.45, every readable page
# scores 0.00. The threshold sits in the middle of that gap with wide margin.
MIXED_TOKEN_THRESHOLD = 0.15


def garble_ratio(text: str) -> float:
    """
    Fraction of characters that are not ordinary readable text.

    Subset fonts embedded without a ToUnicode CMap (Identity-H) extract as raw
    glyph ids, and every extractor surfaces that differently:

      - PyPDF emits raw control bytes (category Cc/Co/Cn),
      - PyMuPDF4LLM substitutes U+FFFD,
      - Docling maps the glyph ids into printable ASCII.

    This catches the first two; ``mixed_token_ratio`` catches the third.
    """
    if not text:
        return 0.0
    bad = sum(
        1
        for ch in text
        if ch not in "\n\t" and (ch == "\ufffd" or unicodedata.category(ch) in {"Cc", "Co", "Cn"})
    )
    return bad / len(text)


def mixed_token_ratio(text: str) -> float:
    """
    Share of word-like tokens containing both letters and digits.

    Returns 0.0 for pages with too few tokens to judge, so a chart or a cover
    page is never flagged.
    """
    # Split on markdown delimiters as well as whitespace: a table row like
    # "|**$**<br>**3,861**|" is one whitespace token containing both letters and
    # digits, which would otherwise look exactly like mojibake.
    cleaned = re.sub(r"<br\s*/?>", " ", text)
    tokens = [t for t in re.split(r"[\s|*#`_~\[\]()]+", cleaned) if len(t) >= 3]
    if len(tokens) < 25:
        return 0.0
    mixed = sum(1 for t in tokens if re.search(r"[A-Za-z]", t) and re.search(r"\d", t))
    return mixed / len(tokens)


def page_is_unreadable(text: str) -> bool:
    """A page is unreadable if either mojibake test fires."""
    return garble_ratio(text) >= GARBLE_THRESHOLD or mixed_token_ratio(text) >= MIXED_TOKEN_THRESHOLD


# Outline entries worth showing the model: the ones that lead to the numbers.
_FINANCIAL_HINTS = (
    "balance sheet", "financial position", "statement of", "consolidated",
    "notes to", "note ", "property", "plant", "equipment", "asset", "inventor",
    "goodwill", "intangible", "receivable", "supplemental", "financial statements",
)


def _relevant_outline(entries: list[tuple[str, int]], limit: int = 28) -> list[str]:
    """Keep outline entries that point at financial content, newest-first order kept."""
    seen: set[str] = set()
    keep: list[str] = []
    for title, page in entries:
        label = " ".join(str(title).split())
        if not label or label.lower() in seen:
            continue
        if any(h in label.lower() for h in _FINANCIAL_HINTS):
            seen.add(label.lower())
            keep.append(f"p{page}: {label}"[:110])
        if len(keep) >= limit:
            break
    return keep


def _compress_pages(pages: list[int], limit: int = 60) -> str:
    """[6,7,8,10,11] -> '6-8, 10-11'. Keeps a long page list cheap in tokens."""
    nums = sorted({int(p) for p in pages if isinstance(p, int) or str(p).isdigit()})
    if not nums:
        return ""
    runs: list[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        runs.append(f"{start}-{prev}" if prev > start else f"{start}")
        start = prev = n
    runs.append(f"{start}-{prev}" if prev > start else f"{start}")
    text = ", ".join(runs)
    return text if len(text) <= limit * 6 else text[: limit * 6] + " …"


@dataclass
class ExtractedText:
    """Uniform result of any PDF → text strategy."""

    text: str
    page_count: int
    garbled_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    readable_pages: int = 0
    # Structural facts the parser discovered about the document: outline,
    # which pages hold tables, whether the text layer is sound, and so on.
    # Empty for parsers that cannot supply any. This is the capability that
    # separates the technologies, so it is carried, not discarded.
    diagnostics: dict = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def approx_tokens(self) -> int:
        return max(1, self.char_count // 4)


def _finalize(pages: list[tuple[int, str]], page_count: int, label: str,
              diagnostics: dict | None = None) -> ExtractedText:
    garbled = [no for no, body in pages if page_is_unreadable(body)]
    empty = [no for no, body in pages if body.strip() == "" and no not in set(garbled)]
    warnings: list[str] = []
    kept = pages

    if garbled:
        shown = ", ".join(str(p) for p in garbled[:12])
        more = "" if len(garbled) <= 12 else f" (+{len(garbled) - 12} more)"
        # Glyph-code pages carry no information but cost real tokens and make the
        # model reason for minutes over noise. Drop them from the prompt and say
        # so, rather than paying to send unreadable bytes.
        kept = [(no, text) for no, text in pages if no not in set(garbled)]
        dropped_chars = sum(len(text) for no, text in pages if no in set(garbled))
        warnings.append(
            f"{len(garbled)} of {page_count} pages have an unreadable text layer "
            f"(subset fonts with no ToUnicode mapping) and extracted as glyph codes: "
            f"pages {shown}{more}. They were excluded from the prompt "
            f"(~{max(1, dropped_chars // 4):,} tokens of noise removed). Values that appear "
            f"only on those pages cannot be recovered by {label}; they need OCR or a "
            f"vision model."
        )
    if empty:
        warnings.append(
            f"{len(empty)} of {page_count} page(s) produced no text at all and are "
            f"not recoverable by {label}."
        )

    # An empty page is not a readable page; count only pages with real text.
    kept = [(no, text) for no, text in kept if text.strip()]
    if not kept:
        warnings.append(
            "No readable page text remains, so there is nothing safe to send to the "
            "model. This document needs OCR or a vision-capable strategy."
        )
    body = "\n\n".join(f"--- PAGE {no} ---\n{text}" for no, text in kept)
    return ExtractedText(
        text=body,
        page_count=page_count,
        garbled_pages=garbled,
        warnings=warnings,
        readable_pages=len(kept),
        diagnostics=diagnostics or {},
    )


def extract_with_pypdf(pdf_path: Path) -> ExtractedText:
    """
    STRATEGY 1: basic local text extraction.

    No layout-aware conversion, OCR, table reconstruction, page selection,
    semantic chunking, or external context lookup — the deliberately plain baseline.
    """
    reader = PdfReader(str(pdf_path))
    pages = [
        (page_no, normalize_text(page.extract_text() or ""))
        for page_no, page in enumerate(reader.pages, start=1)
    ]

    # PyPDF exposes little beyond document metadata and a shallow outline;
    # that is exactly the capability gap this bake-off is measuring.
    diagnostics: dict = {"source": "PyPDF"}
    try:
        meta = reader.metadata or {}
        title = meta.get("/Title") or meta.get("/Subject")
        if title:
            diagnostics["title"] = str(title)[:120]
        entries = []
        for item in (reader.outline or []):
            if isinstance(item, dict) and item.get("/Title"):
                try:
                    entries.append((item["/Title"], reader.get_destination_page_number(item) + 1))
                except Exception:  # noqa: BLE001
                    continue
        outline = _relevant_outline(entries)
        if outline:
            diagnostics["outline"] = outline
    except Exception:  # noqa: BLE001 - metadata is advisory only
        pass

    return _finalize(pages, len(reader.pages), "PyPDF text extraction", diagnostics)


def extract_with_pypdf_ocr(pdf_path: Path, *, ocr_policy: str = "force") -> ExtractedText:
    """PyPDF representation with compulsory RapidOCR preprocessing.

    PyPDF has no reliable page-level OCR router. Strategy 2 therefore sends
    every page through the configured OCR layer before building the same
    page-marked prompt contract used by the other parser arms.
    """
    import pymupdf4llm

    reader = PdfReader(str(pdf_path))
    native_pages = [
        (page_no, normalize_text(page.extract_text() or ""))
        for page_no, page in enumerate(reader.pages, start=1)
    ]
    policy = str(ocr_policy or "adaptive").lower()
    targets = [
        page_no for page_no, body in native_pages
        if policy == "force" or not body.strip() or page_is_unreadable(body)
    ]
    recovered: dict[int, str] = {}
    for page_no in targets:
        chunks = pymupdf4llm.to_markdown(
            str(pdf_path),
            page_chunks=True,
            pages=[page_no - 1],
            use_ocr=True,
            force_ocr=True,
        )
        if chunks:
            chunk = chunks[0]
            body = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            recovered[page_no] = normalize_text(body)
    pages = [(page_no, recovered.get(page_no, body)) for page_no, body in native_pages]
    diagnostics = {
        "source": "PyPDF + RapidOCR recovery",
        "ocr_policy": policy,
        "ocr_pages": _compress_pages(list(recovered)),
        "ocr_page_count": len(recovered),
    }
    return _finalize(pages, len(reader.pages), "PyPDF with OCR recovery", diagnostics)


def extract_with_pymupdf4llm(pdf_path: Path) -> ExtractedText:
    """
    Layout-aware Markdown with table structure preserved and OCR disabled.

    ``page_chunks=True`` keeps the per-page split so we can emit the same
    ``--- PAGE n ---`` markers as Strategy 1. Without them the model has no way
    to fill ``source_page`` and silently invents page numbers.
    """
    try:
        import pymupdf
        import pymupdf4llm
    except ImportError as exc:  # pragma: no cover - depends on install
        raise RuntimeError("pymupdf4llm is not installed. Run: pip install pymupdf4llm") from exc

    diagnostics: dict = {"source": "PyMuPDF4LLM"}
    with pymupdf.open(str(pdf_path)) as doc:
        page_count = len(doc)
        try:
            title = (doc.metadata or {}).get("title")
            if title:
                diagnostics["title"] = str(title)[:120]
            toc = doc.get_toc() or []
            outline = _relevant_outline([(t[1], t[2]) for t in toc])
            if outline:
                diagnostics["outline"] = outline
                diagnostics["outline_entries_total"] = len(toc)
        except Exception:  # noqa: BLE001
            pass

    # Recent PyMuPDF4LLM releases can enable OCR automatically on pages whose
    # text detector is empty. The no-OCR arm is strict, so keep
    # both OCR switches disabled here.
    chunks = pymupdf4llm.to_markdown(
        str(pdf_path), page_chunks=True, use_ocr=False, force_ocr=False
    )
    pages: list[tuple[int, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata") or {}
            # pymupdf4llm names this "page_number"; "page" is accepted as a
            # fallback so a version change degrades to sequential numbering
            # rather than mislabelling every citation.
            raw_page = metadata.get("page_number", metadata.get("page"))
            page_no = int(raw_page) if isinstance(raw_page, int) and raw_page > 0 else index
            body = chunk.get("text", "")
        else:  # pragma: no cover - defensive, older pymupdf4llm returned strings
            page_no, body = index, str(chunk)
        pages.append((page_no, normalize_text(body)))

    return _finalize(pages, page_count or len(pages), "PyMuPDF4LLM markdown extraction", diagnostics)


def extract_with_pymupdf4llm_ocr(pdf_path: Path, *, ocr_policy: str = "adaptive") -> ExtractedText:
    """Layout Markdown with integrated RapidOCR recovery."""
    try:
        import pymupdf
        import pymupdf4llm
    except ImportError as exc:  # pragma: no cover - depends on install
        raise RuntimeError("pymupdf4llm is not installed. Run: pip install pymupdf4llm") from exc

    policy = str(ocr_policy or "adaptive").lower()
    with pymupdf.open(str(pdf_path)) as doc:
        page_count = len(doc)
    chunks = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        use_ocr=True,
        force_ocr=policy == "force",
    )
    pages: list[tuple[int, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata") or {}
            raw_page = metadata.get("page_number", metadata.get("page"))
            page_no = int(raw_page) if isinstance(raw_page, int) and raw_page > 0 else index
            body = chunk.get("text", "")
        else:
            page_no, body = index, str(chunk)
        pages.append((page_no, normalize_text(body)))
    return _finalize(
        pages,
        page_count or len(pages),
        "PyMuPDF4LLM with RapidOCR",
        {"source": "PyMuPDF4LLM + RapidOCR", "ocr_policy": policy},
    )


# Docling loads an ML layout model. Building a converter per call reloads that
# model every time, and several threads loading it at once is what produces
# "Failed to load model … [Errno 32] Broken pipe". Build it once, and let only
# one conversion run at a time: the work is CPU-bound and does not benefit from
# running concurrently anyway.
_DOCLING_LOCK = threading.Lock()
_docling_converters: dict[tuple[bool, bool], object] = {}


def _docling_converter_once(*, do_ocr: bool = False, force_ocr: bool = False):
    key = (bool(do_ocr), bool(force_ocr))
    if key not in _docling_converters:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions()
        # The no-OCR arm disables OCR. The OCR-enabled arm deliberately forces
        # a full-page OCR treatment because Docling does not expose the trusted per-page
        # classifier required by this experiment's adaptive contract.
        options.do_ocr = bool(do_ocr)
        if options.do_ocr:
            options.ocr_options.force_full_page_ocr = bool(force_ocr)
        options.do_table_structure = True
        options.table_structure_options.do_cell_matching = True

        _docling_converters[key] = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
    return _docling_converters[key]


def extract_with_docling(pdf_path: Path, *, ocr_policy: str = "off") -> ExtractedText:
    """
    Layout-aware conversion with Docling's ML document model.

    Serialized behind a lock. Docling is the slowest strategy by a wide margin,
    so a batch will queue here; that is preferable to the model-load race that
    fails the run outright.
    """
    try:
        import logging
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("docling is not installed. Run: pip install docling") from exc

    logging.getLogger("docling").setLevel(logging.ERROR)

    with _DOCLING_LOCK:
        try:
            policy = str(ocr_policy or "off").lower()
            converter = _docling_converter_once(
                do_ocr=policy != "off",
                force_ocr=policy == "force",
            )
        except ImportError as exc:  # pragma: no cover - depends on install
            raise RuntimeError("docling is not installed. Run: pip install docling") from exc
        except Exception as exc:  # noqa: BLE001 - model load can fail for many reasons
            raise RuntimeError(
                f"Docling could not load its layout model ({exc}). "
                "Re-run to retry, or deselect Docling to continue without it."
            ) from exc

        result = converter.convert(str(pdf_path))

    document = result.document
    page_count = len(document.pages) or 1

    # Docling exports per page, which keeps the --- PAGE n --- markers the
    # schema's source_page field depends on.
    pages: list[tuple[int, str]] = []
    for page_no in sorted(document.pages):
        try:
            body = document.export_to_markdown(page_no=page_no)
        except (TypeError, ValueError):
            body = ""
        pages.append((int(page_no), normalize_text(body)))

    if not any(text for _, text in pages):
        pages = [(1, normalize_text(document.export_to_markdown()))]

    # Docling's differentiator is a typed document graph: it knows what is a
    # table, where it sits, and how it is shaped.
    diagnostics: dict = {"source": "Docling", "ocr_policy": str(ocr_policy or "off").lower()}
    try:
        table_pages, shapes = [], []
        for table in getattr(document, "tables", []) or []:
            prov = getattr(table, "prov", None)
            page_no = getattr(prov[0], "page_no", None) if prov else None
            if page_no:
                table_pages.append(int(page_no))
            data = getattr(table, "data", None)
            rows, cols = getattr(data, "num_rows", None), getattr(data, "num_cols", None)
            if page_no and rows and cols:
                shapes.append(f"p{page_no}: {rows}x{cols}")
        if table_pages:
            diagnostics["table_count"] = len(table_pages)
            diagnostics["pages_with_tables"] = _compress_pages(table_pages)
            diagnostics["largest_tables"] = shapes[:12]

        headers = []
        for item in getattr(document, "texts", []) or []:
            if getattr(item, "label", "") in ("section_header", "title"):
                prov = getattr(item, "prov", None)
                page_no = getattr(prov[0], "page_no", None) if prov else None
                headers.append((getattr(item, "text", ""), page_no or 0))
        outline = _relevant_outline(headers)
        if outline:
            diagnostics["outline"] = outline
    except Exception:  # noqa: BLE001 - diagnostics are advisory only
        pass

    return _finalize(pages, page_count, "Docling conversion", diagnostics)


def extract_with_pdf_inspector(pdf_path: Path) -> ExtractedText:
    """
    Firecrawl's pdf-inspector: Rust, position-aware, no OCR, no network.

    It also classifies the document (text_based / scanned / image_based /
    mixed), which is recorded as a warning when the class is not text_based —
    that is the same defect `garble_ratio` catches, detected up front.
    """
    try:
        import pdf_inspector
    except ImportError as exc:  # pragma: no cover - depends on install
        raise RuntimeError("pdf-inspector is not installed. Run: pip install pdf-inspector") from exc

    pages_result = pdf_inspector.extract_pages_markdown(str(pdf_path))
    raw_pages = getattr(pages_result, "pages", pages_result)

    pages: list[tuple[int, str]] = []
    for index, page in enumerate(raw_pages, start=1):
        body = getattr(page, "markdown", None)
        if body is None:
            body = getattr(page, "text", "") or ""
        # `page_number` is one-based when available; the library's `page`
        # fallback is a zero-based index. The old truthy `or` chain collapsed
        # page 0 to 1 and then labelled every later page one page early.
        one_based = getattr(page, "page_number", None)
        zero_based = getattr(page, "page", None)
        if isinstance(one_based, int) and one_based > 0:
            number = one_based
        elif isinstance(zero_based, int) and zero_based >= 0:
            number = zero_based + 1
        else:
            number = index
        pages.append((int(number), normalize_text(body)))

    # pdf-inspector's differentiator: it classifies the document and maps which
    # pages carry tables, columns or unreadable text. All of it is carried
    # forward rather than reduced to a yes/no.
    diagnostics: dict = {"source": "pdf-inspector"}
    kind = ""
    try:
        report = pdf_inspector.process_pdf(str(pdf_path))
        kind = str(getattr(report, "pdf_type", "") or "")
        if getattr(report, "title", None):
            diagnostics["title"] = str(report.title)[:120]
        if kind:
            diagnostics["document_type"] = kind
        confidence = getattr(report, "confidence", None)
        if confidence is not None:
            diagnostics["type_confidence"] = round(float(confidence), 3)
        if getattr(report, "has_encoding_issues", None) is not None:
            diagnostics["has_encoding_issues"] = bool(report.has_encoding_issues)
        if getattr(report, "is_complex_layout", None) is not None:
            diagnostics["complex_layout"] = bool(report.is_complex_layout)
        for attr, key in (("pages_with_tables", "pages_with_tables"),
                          ("pages_with_columns", "pages_with_multiple_columns"),
                          ("pages_needing_ocr", "pages_needing_ocr")):
            values = getattr(report, attr, None) or []
            if values:
                diagnostics[key] = _compress_pages(list(values))
                if attr == "pages_with_tables":
                    diagnostics["table_page_count"] = len(values)
    except Exception:  # noqa: BLE001 - diagnostics are advisory only
        pass

    extracted = _finalize(pages, len(pages), "pdf-inspector extraction", diagnostics)

    if kind and "text_based" not in kind:
        extracted.warnings.append(
            f"pdf-inspector classified this document as '{kind}'. A text-only "
            f"strategy cannot read pages that are images; they need OCR."
        )
    if diagnostics.get("has_encoding_issues"):
        extracted.warnings.append(
            "pdf-inspector reports encoding problems in this document's text layer: "
            "some characters cannot be mapped to real text."
        )

    return extracted


_GLM_OCR_REQUEST_LOCK = threading.Lock()
_GLM_OCR_NEXT_REQUEST_AT = 0.0


def _glm_ocr_markdown(
    image_bytes: bytes,
    *,
    api_key: str,
    endpoint: str,
    page_no: int,
    timeout: float = 180.0,
) -> str:
    """Return GLM-OCR Markdown for one rendered page with bounded retries.

    The official layout-parsing API accepts an image data URL. Calls are kept
    sequential and lightly spaced because a scanned report can otherwise turn
    one user action into a burst of dozens of OCR requests.
    """
    if not api_key.strip():
        raise RuntimeError(
            "GLM-OCR requires a Z.AI API key. Configure GLM_OCR_API_KEY or "
            "save a Z.AI model gateway key in Settings."
        )
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
    url = endpoint.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": "glm-ocr",
        "file": data_url,
        "return_crop_images": False,
        "need_layout_visualization": False,
    }
    last_error = "Unknown GLM-OCR error"
    for attempt in range(1, 5):
        global _GLM_OCR_NEXT_REQUEST_AT
        with _GLM_OCR_REQUEST_LOCK:
            delay = max(0.0, _GLM_OCR_NEXT_REQUEST_AT - time.monotonic())
            if delay:
                time.sleep(delay)
            _GLM_OCR_NEXT_REQUEST_AT = time.monotonic() + float(
                os.getenv("GLM_OCR_REQUEST_INTERVAL_SECONDS", "1.25")
            )
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            except requests.RequestException as exc:
                response = None
                last_error = str(exc)

        if response is not None:
            try:
                body = response.json()
            except ValueError:
                body = {}
            if response.ok:
                data = body.get("data") if isinstance(body.get("data"), dict) else body
                markdown = data.get("md_results") if isinstance(data, dict) else None
                if isinstance(markdown, list):
                    parts: list[str] = []
                    for item in markdown:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict):
                            parts.append(str(item.get("markdown") or item.get("text") or ""))
                    markdown = "\n\n".join(part for part in parts if part.strip())
                if isinstance(markdown, str) and markdown.strip():
                    return normalize_text(markdown)
                last_error = "GLM-OCR returned no Markdown."
            else:
                message = body.get("error") or body.get("message") or response.text[:300]
                last_error = f"HTTP {response.status_code}: {message}"
                if response.status_code not in {408, 409, 425, 429, 500, 502, 503, 504}:
                    break
        if attempt < 4:
            time.sleep(min(12.0, 2.0 ** attempt))
    raise RuntimeError(f"GLM-OCR failed on page {page_no}: {last_error}")


def extract_with_pdf_inspector_ocr(
    pdf_path: Path,
    *,
    ocr_policy: str = "adaptive",
    ocr_context: dict[str, Any] | None = None,
) -> ExtractedText:
    """Rust page classification plus selective 200-DPI GLM-OCR.

    pdf-inspector owns the page decision and native Markdown representation.
    Only pages marked ``needs_ocr`` are rasterized and replaced by hosted
    GLM-OCR Markdown. This keeps the adaptive treatment observable per page.
    """
    try:
        import pdf_inspector
        import pymupdf
    except ImportError as exc:  # pragma: no cover - depends on install
        raise RuntimeError("pdf-inspector and PyMuPDF are required for adaptive GLM-OCR.") from exc
    policy = str(ocr_policy or "adaptive").lower()
    context = ocr_context or {}
    api_key = str(context.get("glm_ocr_api_key") or context.get("api_key") or "")
    endpoint = str(
        context.get("glm_ocr_endpoint")
        or os.getenv("GLM_OCR_ENDPOINT")
        or "https://api.z.ai/api/paas/v4/layout_parsing"
    )
    try:
        result = pdf_inspector.extract_pages_markdown(str(pdf_path))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"pdf-inspector page classification failed ({exc}).") from exc

    raw_pages = list(getattr(result, "pages", result) or [])
    pages: list[tuple[int, str]] = []
    page_provenance: list[dict[str, Any]] = []
    ocr_pages: list[int] = []
    with pymupdf.open(str(pdf_path)) as document:
        for index, page in enumerate(raw_pages, start=1):
            zero_based = getattr(page, "page", None)
            one_based = getattr(page, "page_number", None)
            if isinstance(one_based, int) and one_based > 0:
                page_no = one_based
            elif isinstance(zero_based, int) and zero_based >= 0:
                page_no = zero_based + 1
            else:
                page_no = index
            native_markdown = normalize_text(
                str(getattr(page, "markdown", None) or getattr(page, "text", "") or "")
            )
            classifier_decision = bool(
                getattr(page, "needs_ocr", False)
                or not native_markdown.strip()
                or page_is_unreadable(native_markdown)
            )
            use_ocr = policy == "force" or classifier_decision
            if use_ocr:
                pixmap = document[page_no - 1].get_pixmap(
                    matrix=pymupdf.Matrix(200.0 / 72.0, 200.0 / 72.0),
                    alpha=False,
                )
                markdown = _glm_ocr_markdown(
                    pixmap.tobytes("png"),
                    api_key=api_key,
                    endpoint=endpoint,
                    page_no=page_no,
                )
                ocr_pages.append(page_no)
                source = "glm_ocr"
            else:
                markdown = native_markdown
                source = "pdf_inspector_native_rust"
            pages.append((page_no, markdown))
            page_provenance.append({
                "page": page_no,
                "classification_decision": "ocr_needed" if classifier_decision else "text_page",
                "source": source,
                "render_dpi": 200 if use_ocr else None,
                "ocr_model": "glm-ocr" if use_ocr else None,
            })

    diagnostics = {
        "source": "pdf-inspector native Rust + GLM-OCR",
        "ocr_policy": policy,
        "ocr_router": "pdf-inspector per-page classification",
        "render_dpi": 200,
        "ocr_engine": "glm-ocr",
        "ocr_pages": _compress_pages(ocr_pages),
        "ocr_page_count": len(ocr_pages),
        "page_provenance": page_provenance,
    }
    return _finalize(pages, len(raw_pages), "pdf-inspector with adaptive GLM-OCR", diagnostics)


def extract_with_intelligent_scanning_gate(
    pdf_path: Path,
    *,
    ocr_policy: str = "adaptive",
    ocr_context: dict[str, Any] | None = None,
) -> ExtractedText:
    """Strategy 3: selective OCR, unified Markdown, then whole-page ranking.

    pdf-inspector owns PDF classification, layout metadata, native Markdown,
    and the per-page OCR decision.  GLM-OCR replaces only routed page bodies.
    The deterministic intelligent scanning gate then sends the best three to
    five *complete pages* to the semantic-mapping model.
    """
    try:
        import pdf_inspector
        import pymupdf
    except ImportError as exc:  # pragma: no cover - depends on install
        raise RuntimeError("Strategy 3 requires pdf-inspector and PyMuPDF.") from exc

    context = ocr_context or {}
    api_key = str(context.get("glm_ocr_api_key") or context.get("api_key") or "")
    endpoint = str(
        context.get("glm_ocr_endpoint")
        or os.getenv("GLM_OCR_ENDPOINT")
        or "https://api.z.ai/api/paas/v4/layout_parsing"
    )
    try:
        result = pdf_inspector.extract_pages_markdown(str(pdf_path))
        classification = pdf_inspector.detect_pdf(str(pdf_path))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"pdf-inspector page extraction failed ({exc}).") from exc

    raw_pages = list(getattr(result, "pages", result) or [])
    aggregate_ocr_pages = {
        int(page) for page in (getattr(result, "pages_needing_ocr", None) or [])
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1
    }
    aggregate_ocr_pages.update(
        int(page) for page in (getattr(classification, "pages_needing_ocr", None) or [])
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1
    )
    ocr_reasons: dict[int, list[str]] = {}
    for entry in getattr(result, "ocr_reasons_by_page", None) or []:
        page_no = getattr(entry, "page", None)
        if isinstance(page_no, int) and page_no >= 1:
            ocr_reasons[page_no] = [str(reason) for reason in (getattr(entry, "reasons", None) or [])]

    unified_pages: list[tuple[int, str]] = []
    page_provenance: list[dict[str, Any]] = []
    routed_pages: list[int] = []
    with pymupdf.open(str(pdf_path)) as document:
        for fallback, page in enumerate(raw_pages, start=1):
            zero_based = getattr(page, "page", None)
            one_based = getattr(page, "page_number", None)
            if isinstance(one_based, int) and one_based > 0:
                page_no = one_based
            elif isinstance(zero_based, int) and zero_based >= 0:
                page_no = zero_based + 1
            else:
                page_no = fallback
            native_markdown = normalize_text(
                str(getattr(page, "markdown", None) or getattr(page, "text", "") or "")
            )
            needs_ocr = bool(getattr(page, "needs_ocr", False) or page_no in aggregate_ocr_pages)
            if needs_ocr:
                pixmap = document[page_no - 1].get_pixmap(
                    matrix=pymupdf.Matrix(200.0 / 72.0, 200.0 / 72.0),
                    alpha=False,
                )
                markdown = _glm_ocr_markdown(
                    pixmap.tobytes("png"),
                    api_key=api_key,
                    endpoint=endpoint,
                    page_no=page_no,
                )
                routed_pages.append(page_no)
                source = "glm_ocr"
            else:
                markdown = native_markdown
                source = "pdf_inspector_native_rust"
            unified_pages.append((page_no, markdown))
            page_provenance.append({
                "page": page_no,
                "needs_ocr": needs_ocr,
                "ocr_reasons": ocr_reasons.get(page_no, []),
                "source": source,
                "render_dpi": 200 if needs_ocr else None,
            })

    table_pages = list(getattr(result, "pages_with_tables", None) or [])
    column_pages = list(getattr(result, "pages_with_columns", None) or [])
    selected_pages, gate = select_evidence_pages(
        unified_pages,
        pages_with_tables=table_pages,
        pages_with_columns=column_pages,
    )
    if not selected_pages:
        raise RuntimeError("The intelligent scanning gate found no readable Markdown pages.")

    diagnostics = {
        "source": "pdf-inspector + selective GLM-OCR + intelligent scanning gate",
        "document_type": str(getattr(classification, "pdf_type", "") or "unknown"),
        "type_confidence": round(float(getattr(classification, "confidence", 0.0) or 0.0), 3),
        "has_encoding_issues": bool(getattr(classification, "has_encoding_issues", False)),
        "ocr_policy": str(ocr_policy or "adaptive").lower(),
        "ocr_router": "pdf-inspector per-page needs_ocr",
        "ocr_engine": "glm-ocr",
        "render_dpi": 200,
        "ocr_pages": _compress_pages(routed_pages),
        "ocr_page_count": len(routed_pages),
        "pages_with_tables": _compress_pages(table_pages),
        "pages_with_multiple_columns": _compress_pages(column_pages),
        "complex_layout": bool(getattr(result, "is_complex", False)),
        "page_provenance": page_provenance,
        **gate,
    }
    extracted = _finalize(
        selected_pages,
        len(raw_pages),
        "Strategy 3 intelligent scanning",
        diagnostics,
    )
    extracted.warnings.append(
        f"The intelligent scanning gate retained {len(selected_pages)} of {len(raw_pages)} complete pages "
        f"for semantic mapping ({gate.get('character_reduction_percent', 0):.1f}% fewer Markdown characters)."
    )
    return extracted


@dataclass(frozen=True)
class Strategy:
    key: str
    run_prefix: str
    label: str
    extraction_note: str
    extract: object
    parser: str
    experiment: str
    ocr_enabled: bool = False
    ocr_policy: str = "off"

    def __call__(
        self,
        pdf_path: Path,
        *,
        ocr_policy: str = "adaptive",
        ocr_context: dict[str, Any] | None = None,
    ) -> ExtractedText:
        if self.ocr_enabled:
            # OCR behavior is part of the experimental treatment, not a user
            # preference. Parsers with a real page classifier stay adaptive;
            # parsers without one OCR every page in the OCR-enabled arm.
            if self.key in {"s2-inspector", "s3"}:
                return self.extract(
                    pdf_path,
                    ocr_policy=self.ocr_policy,
                    ocr_context=ocr_context,
                )
            return self.extract(pdf_path, ocr_policy=self.ocr_policy)
        return self.extract(pdf_path)


STRATEGIES: dict[str, Strategy] = {
    "s1": Strategy(
        key="s1",
        run_prefix="S1",
        label="Strategy 1 - PyPDF without OCR",
        extraction_note=(
            "raw page-by-page text using basic PyPDF extraction only. Table columns "
            "may be flattened or interleaved. Page markers identify the source PDF page."
        ),
        extract=extract_with_pypdf,
        parser="pypdf",
        experiment="no_ocr",
    ),
    "s1-pymupdf": Strategy(
        key="s1-pymupdf",
        run_prefix="S1PM",
        label="Strategy 1 - PyMuPDF4LLM without OCR",
        extraction_note=(
            "layout-aware Markdown using PyMuPDF4LLM with table structure preserved. "
            "Page markers identify the source PDF page."
        ),
        extract=extract_with_pymupdf4llm,
        parser="pymupdf",
        experiment="no_ocr",
    ),
    "s1-docling": Strategy(
        key="s1-docling",
        run_prefix="S1DL",
        label="Strategy 1 - Docling without OCR",
        extraction_note=(
            "layout-aware Markdown produced by Docling's document model, with table "
            "structure and cell matching. Page markers identify the source PDF page."
        ),
        extract=extract_with_docling,
        parser="docling",
        experiment="no_ocr",
    ),
    "s1-inspector": Strategy(
        key="s1-inspector",
        run_prefix="S1FC",
        label="Strategy 1 - pdf-inspector without OCR",
        extraction_note=(
            "position-aware Markdown produced by Firecrawl's pdf-inspector, with "
            "multi-column reading order and table detection. Page markers identify "
            "the source PDF page."
        ),
        extract=extract_with_pdf_inspector,
        parser="inspector",
        experiment="no_ocr",
    ),
    "s2-pypdf": Strategy(
        key="s2-pypdf",
        run_prefix="S2PY",
        label="Strategy 2 - PyPDF with compulsory OCR",
        extraction_note=(
            "Every page is rendered and processed with RapidOCR because PyPDF has no trusted "
            "per-page OCR classifier. Page markers identify the source PDF page."
        ),
        extract=extract_with_pypdf_ocr,
        parser="pypdf",
        experiment="ocr",
        ocr_enabled=True,
        ocr_policy="force",
    ),
    "s2": Strategy(
        key="s2",
        run_prefix="S2",
        label="Strategy 2 - PyMuPDF4LLM with OCR",
        extraction_note=(
            "layout-aware Markdown using PyMuPDF4LLM with integrated RapidOCR recovery and table structure preserved. "
            "Page markers identify the source PDF page."
        ),
        extract=extract_with_pymupdf4llm_ocr,
        parser="pymupdf",
        experiment="ocr",
        ocr_enabled=True,
        ocr_policy="adaptive",
    ),
    "s2-docling": Strategy(
        key="s2-docling",
        run_prefix="S2DL",
        label="Strategy 2 - Docling with compulsory OCR",
        extraction_note=(
            "Docling document-graph conversion with OCR forced on every page, table structure, and cell matching. "
            "Page markers identify the source PDF page."
        ),
        extract=extract_with_docling,
        parser="docling",
        experiment="ocr",
        ocr_enabled=True,
        ocr_policy="force",
    ),
    "s2-inspector": Strategy(
        key="s2-inspector",
        run_prefix="S2FC",
        label="Strategy 2 - pdf-inspector with adaptive OCR",
        extraction_note=(
            "pdf-inspector classifies every page. Text pages keep native Rust Markdown; OCR-needed pages "
            "are rendered at 200 DPI and replaced by GLM-OCR Markdown before page-ordered assembly."
        ),
        extract=extract_with_pdf_inspector_ocr,
        parser="inspector",
        experiment="ocr",
        ocr_enabled=True,
        ocr_policy="adaptive",
    ),
    "s3": Strategy(
        key="s3",
        run_prefix="S3",
        label="Strategy 3 - intelligent scanning gate",
        extraction_note=(
            "a three-to-five-page evidence packet. pdf-inspector produced complete per-page Markdown; "
            "only pages it marked as needing OCR were replaced by 200-DPI GLM-OCR Markdown; the unified "
            "pages were then ranked by the deterministic intelligent scanning gate using table presence, "
            "financial headings, the fixed 27-field vocabulary, and layout metadata. Page markers identify "
            "the original source PDF pages."
        ),
        extract=extract_with_intelligent_scanning_gate,
        parser="inspector-gate",
        experiment="intelligent_scan",
        ocr_enabled=True,
        ocr_policy="adaptive",
    ),
}

# Historical keys already match the public numbering: Strategy 1 is the
# no-OCR control and Strategy 2 is the OCR-enabled arm.
DEFAULT_STRATEGY = "s1"


def get_strategy(key: str | None) -> Strategy:
    """Resolve a strategy key, defaulting only when no key was supplied."""
    normalized = (key or "").strip().lower()
    if not normalized:
        return STRATEGIES[DEFAULT_STRATEGY]
    if normalized not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy {key!r}. Choose one of: {', '.join(STRATEGIES)}"
        )
    return STRATEGIES[normalized]


def estimate_pdf_load(pdf_path: Path) -> dict[str, object]:
    """
    Fast pre-flight estimate of how big a PDF will be as prompt input.

    Samples a handful of pages instead of extracting the whole document, so a
    six-file batch can be sized in well under a second. The result is an
    estimate and is labelled as such wherever it is shown.
    """
    import pymupdf

    with pymupdf.open(str(pdf_path)) as doc:
        page_count = len(doc)
        if page_count == 0:
            return {"pages": 0, "approx_tokens": 0, "sampled_pages": 0, "estimated": True}

        # Sample across the document: annual reports are front-loaded with
        # graphics and back-loaded with dense financial tables.
        step = max(1, page_count // 12)
        sampled = list(range(0, page_count, step))[:12]
        chars = sum(len(normalize_text(doc[i].get_text())) for i in sampled)

    chars_per_page = chars / len(sampled) if sampled else 0
    total_chars = int(chars_per_page * page_count)
    # Page markers add roughly 20 characters per page.
    total_chars += page_count * 20

    return {
        "pages": page_count,
        "approx_characters": total_chars,
        "approx_tokens": max(1, total_chars // 4),
        "sampled_pages": len(sampled),
        "estimated": True,
    }
