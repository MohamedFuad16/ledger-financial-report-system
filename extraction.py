"""
PDF → text conversion for each strategy, plus the text-health checks that tell
us when a document simply cannot be read as text.

Every strategy returns the same ``ExtractedText`` shape so the rest of the
pipeline is strategy-agnostic.
"""

from __future__ import annotations

import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

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
    semantic chunking, or retrieval — the deliberately plain baseline.
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


def extract_with_pymupdf4llm(pdf_path: Path) -> ExtractedText:
    """
    STRATEGY 2: layout-aware markdown with table structure preserved.

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

    # Recent PyMuPDF4LLM releases enable OCR automatically on pages whose text
    # detector is empty. Strategy 2 is specifically a document-representation
    # comparison, not an OCR strategy, so keep that extra variable disabled.
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


# Docling loads an ML layout model. Building a converter per call reloads that
# model every time, and several threads loading it at once is what produces
# "Failed to load model … [Errno 32] Broken pipe". Build it once, and let only
# one conversion run at a time: the work is CPU-bound and does not benefit from
# running concurrently anyway.
_DOCLING_LOCK = threading.Lock()
_docling_converter = None


def _docling_converter_once():
    global _docling_converter
    if _docling_converter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions()
        # Every document in the benchmark is text-based; running OCR anyway
        # found nothing and dominated the runtime.
        options.do_ocr = False
        options.do_table_structure = True
        options.table_structure_options.do_cell_matching = True

        _docling_converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
    return _docling_converter


def extract_with_docling(pdf_path: Path) -> ExtractedText:
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
            converter = _docling_converter_once()
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
    diagnostics: dict = {"source": "Docling"}
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


@dataclass(frozen=True)
class Strategy:
    key: str
    run_prefix: str
    label: str
    extraction_note: str
    extract: object

    def __call__(self, pdf_path: Path) -> ExtractedText:
        return self.extract(pdf_path)


STRATEGIES: dict[str, Strategy] = {
    "s1": Strategy(
        key="s1",
        run_prefix="S1",
        label="Strategy 1 - direct LLM baseline",
        extraction_note=(
            "raw page-by-page text using basic PyPDF extraction only. Table columns "
            "may be flattened or interleaved. Page markers identify the source PDF page."
        ),
        extract=extract_with_pypdf,
    ),
    "s2": Strategy(
        key="s2",
        run_prefix="S2",
        label="Strategy 2 - layout-aware markdown",
        extraction_note=(
            "layout-aware Markdown using PyMuPDF4LLM with table structure preserved. "
            "Page markers identify the source PDF page."
        ),
        extract=extract_with_pymupdf4llm,
    ),
    "s2-docling": Strategy(
        key="s2-docling",
        run_prefix="S2DL",
        label="Strategy 2 - Docling",
        extraction_note=(
            "layout-aware Markdown produced by Docling's document model, with table "
            "structure and cell matching. Page markers identify the source PDF page."
        ),
        extract=extract_with_docling,
    ),
    "s2-inspector": Strategy(
        key="s2-inspector",
        run_prefix="S2FC",
        label="Strategy 2 - Firecrawl pdf-inspector",
        extraction_note=(
            "position-aware Markdown produced by Firecrawl's pdf-inspector, with "
            "multi-column reading order and table detection. Page markers identify "
            "the source PDF page."
        ),
        extract=extract_with_pdf_inspector,
    ),
}

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
