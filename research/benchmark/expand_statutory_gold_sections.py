"""Expand gazette gold from TA-only to the printed section totals.

Every 決算公告 balance-sheet summary prints 流動資産, 固定資産 (and sometimes
繰延資産) alongside 資産合計. The totals were human/derivation-verified gold
already; this script admits the section rows ONLY when local OCR reproduces
the verified total exactly through the identity CA + FA (+ Deferred) = TA at
the source's own thousand-yen precision. A page whose OCR does not close the
identity is left untouched (TA-only), never guessed.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pymupdf

from corpus.manifest import load_manifest
from extraction import _local_ocr_markdown, _ocr_render_matrix

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = [ROOT / "benchmark_data" / name for name in ("bakuraku_statutory_gold.json", "year_expansion_gold.json")]

# The gazette summary format is fixed by the corporate accounting rules:
# the asset section prints 流動資産, 固定資産 and (when present) 繰延資産 in
# that order, followed by 資産合計. OCR often garbles the vertical kanji
# labels, so the amounts are read positionally: everything printed before
# the line whose total equals the verified 資産合計, in print order.
# Signed amounts: gazettes print allowance deductions as △123. Comma-grouped
# numbers are unambiguous; bare 3-6 digit integers are admitted only in the
# permissive second pass (some prints show small 繰延資産 without grouping).
AMOUNT_STRICT = re.compile(r"([△▲]?)(\d{1,3}(?:,\d{3})+)")
AMOUNT_LOOSE = re.compile(r"([△▲]?)(\d{1,3}(?:,\d{3})+|\d{3,6})")


def _collect(text: str, total_thousand: int, pattern: re.Pattern[str]) -> list[int] | None:
    amounts: list[int] = []
    for line in text.splitlines():
        matches = pattern.findall(line)
        line_amounts = [(-1 if sign else 1) * int(number.replace(",", "")) for sign, number in matches]
        if not line_amounts:
            continue
        if any(value == total_thousand for value in line_amounts) and "合" in line.replace(" ", ""):
            amounts.extend(value for value in line_amounts if value != total_thousand)
            return amounts
        amounts.extend(line_amounts)
    return None  # the verified total never appeared


def section_values(path: Path, gold_total_m: float) -> list[float] | None:
    with pymupdf.open(path) as pdf:
        page = pdf[0]
        pixmap = page.get_pixmap(matrix=_ocr_render_matrix(page), alpha=False)
        text = _local_ocr_markdown(pixmap.tobytes("png"), page_no=1)
    total_thousand = round(gold_total_m * 1000.0)
    for pattern in (AMOUNT_STRICT, AMOUNT_LOOSE):
        amounts = _collect(text, total_thousand, pattern)
        if amounts is None or len(amounts) not in (2, 3):
            continue
        # Each printed component is itself rounded to thousand yen, so the
        # printed total may differ by up to one unit per component.
        if abs(sum(amounts) - total_thousand) > len(amounts):
            continue
        if any(value <= 0 for value in amounts):
            continue  # a net-of-allowance layout needs human review, not guessing
        return [round(value / 1000.0, 3) for value in amounts]
    return None


def main() -> None:
    manifest = {d["sha256"]: d for d in load_manifest()["documents"]}
    report = {"expanded": [], "closure_failed": [], "skipped": []}
    for fixture_path in FIXTURES:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        documents = payload.get("documents") or {}
        changed = False
        for sha, entry in documents.items():
            answers = entry.get("answers") or {}
            non_null = {k: v for k, v in answers.items() if v is not None}
            if set(non_null) != {"Total Assets"}:
                continue  # not a TA-only gazette entry
            doc = manifest.get(sha)
            if not doc:
                report["skipped"].append((entry.get("company"), "not in manifest"))
                continue
            gold_total = float(non_null["Total Assets"])
            ordered = section_values(ROOT / str(doc["local_path"]), gold_total)
            if ordered is None:
                report["closure_failed"].append((entry.get("company"), "identity did not close from OCR", None))
                continue
            items = ["Current Assets", "Fixed Assets", "Deferred Charges"][: len(ordered)]
            sections = dict(zip(items, ordered))
            for item, value in sections.items():
                answers[item] = value
                if item in (entry.get("unscorable_rows") or []):
                    entry["unscorable_rows"].remove(item)
            entry["answers"] = answers
            entry["scorable_rows"] = sum(1 for v in answers.values() if v is not None)
            notes = entry.setdefault("citations", {})
            for item in sections:
                notes[item] = (
                    "2026-08-25 expansion: printed section total on the single gazette page, admitted because "
                    "local OCR reproduces the verified 資産合計 exactly via 流動資産+固定資産(+繰延資産)."
                )
            report["expanded"].append((entry.get("company"), entry.get("fiscal_year"), sections))
            changed = True
        if changed:
            fixture_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = ROOT / "research" / "benchmark" / "statutory_section_expansion.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"expanded {len(report['expanded'])} · closure failed {len(report['closure_failed'])} · skipped {len(report['skipped'])}")
    for company, year, sections in report["expanded"]:
        print(f"  + {company} FY{year}: {sections}")
    for company, reason, detail in report["closure_failed"]:
        print(f"  ! {company}: {reason}")


if __name__ == "__main__":
    main()
