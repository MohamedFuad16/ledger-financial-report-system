"""Re-run the two independent text checks for the FY2022 expansion sources.

Usage:
    .venv/bin/python research/benchmark/verify_fy2022_expansion_sources.py /path/to/pdfs

The directory must contain the filenames below. The script checks exact bytes,
page counts, and filing-page markers through both Poppler and PyMuPDF.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "research" / "benchmark" / "fy2022_expansion_sources.json"
FILES = {
    "株式会社アップガレージグループ": ("upgarage_2022.pdf", 52, ["3,535,891", "907,489", "5,338,173"]),
    "株式会社トーエネック": ("toenec_2022.pdf", 53, ["113,270", "145,891", "301,599"]),
    "西尾レントオール株式会社": ("nishio_2022.pdf", 49, ["105,927", "143,825", "261,699"]),
    "トヨタ自動車株式会社": ("toyota_2022.pdf", 132, ["23,722,290", "12,326,640", "67,688,771"]),
    "ソニーグループ株式会社": ("sony_2022.pdf", 111, ["5,535,208", "24,945,759", "30,480,967"]),
}


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def main(pdf_root: Path) -> None:
    sources = {item["company"]: item for item in json.loads(REGISTRY.read_text())["sources"]}
    for company, (filename, page, markers) in FILES.items():
        path = pdf_root / filename
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        source = sources[company]
        if digest != source["sha256"]:
            raise AssertionError(f"{company}: SHA-256 mismatch")

        pdf = pymupdf.open(path)
        if pdf.page_count != source["pages"]:
            raise AssertionError(f"{company}: page-count mismatch")
        pymupdf_text = compact(pdf.load_page(page - 1).get_text("text"))
        poppler_text = compact(subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(path), "-"],
            check=True, capture_output=True, text=True,
        ).stdout)
        for marker in markers:
            expected = compact(marker)
            if expected not in poppler_text:
                raise AssertionError(f"{company}: Poppler missed {marker} on page {page}")
            if expected not in pymupdf_text:
                raise AssertionError(f"{company}: PyMuPDF missed {marker} on page {page}")
        print(f"PASS {company}: sha256 + {source['pages']} pages + Poppler/PyMuPDF page {page}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Pass the directory containing the five audited PDFs")
    main(Path(sys.argv[1]).expanduser().resolve())
