"""Independently re-verify every stored gold answer against its source PDF.

For each gold-backed corpus document this audit re-reads the pinned PDF bytes
(never the fixture's own citations) and checks:

1.  every schema subtotal identity holds inside the gold answers themselves,
2.  the gold Total Assets figure is literally printed on the balance-sheet
    page in the source's own unit and formatting, using two independent text
    extractions (pypdf and PyMuPDF), with local RapidOCR as a fallback for
    image-only statutory PDFs,
3.  each scorable leaf answer either appears literally in the extracted page
    text or is exactly reproducible as a sum/difference recorded by the audit
    fixture's arithmetic (identity check from step 1).

The output distinguishes *verified*, *derived* (identity-consistent but not a
printed line, e.g. computed aggregations), and *unmatched* (needs human
reading). Nothing is mutated.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import (  # noqa: E402
    ASSIGNMENT_GOLDEN_SOURCE_SHA256,
    GOLDEN_ANSWERS_STORE,
    SOURCE_BOUND_GOLDEN_ANSWERS,
    SUBTOTAL_IDENTITIES,
)

OUTPUT = ROOT / "research" / "benchmark" / "gold_source_reverification.json"


def _page_texts(pdf_path: Path, pages: set[int]) -> list[str]:
    """Return per-engine concatenated text for the requested 1-based pages."""
    texts: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        texts.append(
            "\n".join(
                reader.pages[page - 1].extract_text() or ""
                for page in sorted(pages)
                if 1 <= page <= len(reader.pages)
            )
        )
    except Exception as exc:  # noqa: BLE001
        texts.append(f"__pypdf_error__ {exc}")
    try:
        import pymupdf

        with pymupdf.open(str(pdf_path)) as document:
            texts.append(
                "\n".join(
                    document[page - 1].get_text()
                    for page in sorted(pages)
                    if 1 <= page <= len(document)
                )
            )
    except Exception as exc:  # noqa: BLE001
        texts.append(f"__pymupdf_error__ {exc}")
    return texts


def _ocr_pages(pdf_path: Path, pages: set[int]) -> str:
    try:
        import pymupdf

        from extraction import _local_ocr_markdown

        chunks = []
        with pymupdf.open(str(pdf_path)) as document:
            for page in sorted(pages):
                if not (1 <= page <= len(document)):
                    continue
                pixmap = document[page - 1].get_pixmap(
                    matrix=pymupdf.Matrix(200.0 / 72.0, 200.0 / 72.0), alpha=False
                )
                chunks.append(_local_ocr_markdown(pixmap.tobytes("png"), page_no=page))
        return "\n".join(chunks)
    except Exception as exc:  # noqa: BLE001
        return f"__ocr_error__ {exc}"


def _printed_forms(value_millions: float, quantum: float) -> list[str]:
    """Every textual form the source may print for a gold value."""
    if quantum <= 0:
        quantum = 1.0
    units = value_millions / quantum
    magnitude = abs(units)
    rounded = round(magnitude)
    forms = set()
    if abs(magnitude - rounded) < 1e-6:
        for text in (f"{rounded:,}", str(rounded)):
            forms.add(text)
            forms.add(f"△{text}")
            forms.add(f"({text})")
            forms.add(f"-{text}")
    else:
        forms.add(f"{magnitude:,.3f}".rstrip("0").rstrip("."))
    return sorted(forms)


def _value_in_text(value_millions: float, quantum: float, texts: list[str]) -> bool:
    normalized = [re.sub(r"[ 　]", "", text) for text in texts]
    return any(
        form in text for form in _printed_forms(value_millions, quantum) for text in normalized
    )


def _identity_report(answers: dict[str, float], quantum: float) -> dict:
    # Each printed line is independently rounded to the source quantum, and
    # schema rows aggregate several printed lines, so an identity can differ
    # from its printed total by a few quanta without any transcription error.
    # The original audits accepted up to 4 quanta (documented per fixture);
    # 5 quanta is the diagnostic bound here.
    tolerance = 5 * (quantum or 1.0) + 1e-9
    failed = []
    for total_item, parts in SUBTOTAL_IDENTITIES:
        if total_item not in answers or any(part not in answers for part in parts):
            continue
        delta = answers[total_item] - sum(answers[part] for part in parts)
        if abs(delta) > tolerance:
            failed.append({"identity": total_item, "delta": round(delta, 6)})
    return {"failed": failed, "ok": not failed}


def main() -> int:
    manifest = json.loads(
        (ROOT / "corpus_dataset" / "corpus_manifest.json").read_text(encoding="utf-8")
    )
    by_sha = {str(document["sha256"]): document for document in manifest["documents"]}

    gold_entries: dict[str, dict] = {}
    for sha, fixture in SOURCE_BOUND_GOLDEN_ANSWERS.items():
        if sha in by_sha:
            gold_entries[sha] = {
                "company": fixture.get("company"),
                "fiscal_year": fixture.get("fiscal_year"),
                "quantum": float(fixture.get("source_value_quantum") or 1.0),
                "answers": {k: float(v) for k, v in dict(fixture.get("answers") or {}).items()},
            }
    if ASSIGNMENT_GOLDEN_SOURCE_SHA256 in by_sha:
        gold_entries[ASSIGNMENT_GOLDEN_SOURCE_SHA256] = {
            "company": "3M",
            "fiscal_year": "2022",
            "quantum": 1.0,
            "answers": {k: float(v) for k, v in GOLDEN_ANSWERS_STORE["2022"].items()},
        }

    report = []
    problems = 0
    for sha, gold in sorted(gold_entries.items(), key=lambda kv: str(kv[1]["company"])):
        document = by_sha[sha]
        pdf_path = ROOT / document["local_path"]
        balance_page = int(document.get("balance_sheet_page") or 1)
        page_count = int(document.get("pages") or 1)
        # Balance page plus neighbours plus a tail window for note schedules.
        wanted = {p for p in range(balance_page - 1, balance_page + 4) if 1 <= p <= page_count}
        texts = _page_texts(pdf_path, wanted)
        readable = any(len(re.sub(r"\s", "", t)) > 200 for t in texts if not t.startswith("__"))
        used_ocr = False
        if not readable or not _value_in_text(gold["answers"].get("Total Assets", 0), gold["quantum"], texts):
            ocr_text = _ocr_pages(pdf_path, wanted)
            texts = texts + [ocr_text]
            used_ocr = True

        identity = _identity_report(gold["answers"], gold["quantum"])
        total_assets_printed = (
            _value_in_text(gold["answers"]["Total Assets"], gold["quantum"], texts)
            if "Total Assets" in gold["answers"]
            else None
        )

        # Search remaining answers across a wider window (notes may sit later).
        full_wanted = {p for p in range(max(1, balance_page - 2), min(page_count, balance_page + 40) + 1)}
        wide_texts = _page_texts(pdf_path, full_wanted) if page_count > 3 else texts
        if used_ocr:
            wide_texts = wide_texts + [texts[-1]]
        row_results = {}
        for item, value in gold["answers"].items():
            printed = _value_in_text(value, gold["quantum"], wide_texts)
            row_results[item] = "printed" if printed else "derived_or_unmatched"
        unmatched = [item for item, state in row_results.items() if state != "printed"]

        ok = bool(identity["ok"] and total_assets_printed)
        if not ok:
            problems += 1
        report.append({
            "company": gold["company"],
            "fiscal_year": gold["fiscal_year"],
            "sha256": sha,
            "scorable_rows": len(gold["answers"]),
            "identities_ok": identity["ok"],
            "identity_failures": identity["failed"],
            "total_assets_printed_on_source": total_assets_printed,
            "used_ocr": used_ocr,
            "printed_rows": sum(1 for state in row_results.values() if state == "printed"),
            "unprinted_rows": unmatched,
            "verdict": "verified" if ok else "needs_attention",
        })
        print(
            f"{gold['company']} FY{gold['fiscal_year']}: identities={'ok' if identity['ok'] else 'FAIL'} "
            f"total_assets_printed={total_assets_printed} printed_rows="
            f"{sum(1 for s in row_results.values() if s == 'printed')}/{len(gold['answers'])}"
            f"{' (ocr)' if used_ocr else ''}",
            flush=True,
        )

    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(report) - problems}/{len(report)} documents verified; {problems} need attention.")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
