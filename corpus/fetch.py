"""Download, normalize, hash, screen, and file Annual Report PDFs."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .manifest import CORPUS_ROOT, upsert_document
from .screen import screen_pdf


MAX_PDF_BYTES = 100 * 1024 * 1024


def company_slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return slug or "Unknown_Company"


def canonical_report_name(company: str, year: int) -> str:
    return f"{company_slug(company)}_annual_report_{int(year)}.pdf"


def _download(url: str, target: Path) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only public HTTP(S) PDF URLs are supported.")
    digest = hashlib.sha256()
    size = 0
    with requests.get(url, stream=True, timeout=(15, 120), allow_redirects=True, headers={"User-Agent": "LedgerCorpusBuilder/1.0"}) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_PDF_BYTES:
                    raise ValueError("PDF exceeds the 100 MB corpus limit.")
                digest.update(chunk)
                handle.write(chunk)
    with target.open("rb") as handle:
        header = handle.read(5)
    if header != b"%PDF-":
        raise ValueError("The discovered URL did not return a PDF file.")
    return digest.hexdigest(), size


def fetch_report(candidate: dict[str, Any]) -> dict[str, Any]:
    company = str(candidate["company"])
    year = int(candidate["year"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = company_slug(company)
    directory = CORPUS_ROOT / slug / str(year) / stamp
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / canonical_report_name(company, year)
    try:
        sha256, size = _download(str(candidate["url"]), target)
        screening = screen_pdf(target, year)
    except Exception:
        target.unlink(missing_ok=True)
        try:
            directory.rmdir()
        except OSError:
            pass
        raise

    document = {
        "company": company,
        "company_slug": slug,
        "fiscal_year": year,
        "source_url": candidate["url"],
        "source_title": candidate.get("title", ""),
        "official_domain": candidate.get("official_domain", ""),
        "official_source_verified": bool(
            candidate.get("official_domain")
            and (
                urlparse(str(candidate["url"])).netloc.lower().removeprefix("www.")
                == str(candidate["official_domain"]).lower().removeprefix("www.")
                or urlparse(str(candidate["url"])).netloc.lower().endswith(
                    "." + str(candidate["official_domain"]).lower().removeprefix("www.")
                )
            )
        ),
        "discovery": candidate.get("discovery", ""),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "local_path": str(target),
        "filename": target.name,
        "sha256": sha256,
        "size_bytes": size,
        "golden_answers": None,
        **screening,
    }
    return upsert_document(document)
