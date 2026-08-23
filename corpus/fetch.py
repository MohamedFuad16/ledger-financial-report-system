"""Download, normalize, hash, screen, and file Annual Report PDFs."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any
from urllib.parse import urlparse

import requests

from .manifest import CORPUS_ROOT, upsert_document
from .screen import screen_pdf
from schema import ASSET_SCHEMA


MAX_PDF_BYTES = 100 * 1024 * 1024


def company_slug(name: str) -> str:
    # Keep Unicode letters/numbers so distinct Japanese company names cannot
    # collapse into the same ``Unknown_Company/<year>`` directory. ``\w`` is
    # Unicode-aware in Python; punctuation and path separators are still
    # replaced, and dots are deliberately excluded to avoid traversal tokens.
    slug = re.sub(r"[^\w-]+", "_", name, flags=re.UNICODE).strip("_")
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
    slug = company_slug(company)
    directory = CORPUS_ROOT / slug / str(year)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / canonical_report_name(company, year)
    temporary = directory / f".{target.stem}.{uuid.uuid4().hex}.pdf"
    try:
        sha256, size = _download(str(candidate["url"]), temporary)
        expected_sha256 = str(candidate.get("expected_sha256") or "").strip().lower()
        if expected_sha256 and sha256.lower() != expected_sha256:
            raise ValueError(
                "Downloaded PDF SHA-256 does not match the independently audited source."
            )
        screening = screen_pdf(
            temporary,
            year,
            expected_company=company,
            require_annual_document=True,
        )
        if screening.get("screened") != "ok":
            reasons = "; ".join(str(reason) for reason in screening.get("screen_reasons") or [])
            raise ValueError(f"Downloaded PDF failed Annual Report screening: {reasons or 'review required'}")
        # The last verified download remains usable until its replacement has
        # passed both the PDF signature check and document screening.
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
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
            candidate.get("source_verified")
            or (
                candidate.get("official_domain")
                and (
                urlparse(str(candidate["url"])).netloc.lower().removeprefix("www.")
                == str(candidate["official_domain"]).lower().removeprefix("www.")
                or urlparse(str(candidate["url"])).netloc.lower().endswith(
                    "." + str(candidate["official_domain"]).lower().removeprefix("www.")
                )
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


def _normalize_candidate_rows(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize one Firecrawl response to the canonical 27-row schema."""
    returned = {
        str(row.get("item") or ""): row
        for row in (parsed.get("rows") or [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for schema_row in ASSET_SCHEMA:
        candidate = returned.get(str(schema_row["item"]), {})
        answer = candidate.get("answer_m_usd")
        confidence = candidate.get("confidence")
        source_page = candidate.get("source_page")
        rows.append({
            "classification": schema_row["classification"],
            "subclassification": schema_row["subclassification"],
            "item": schema_row["item"],
            "answer_m_usd": float(answer) if isinstance(answer, (int, float)) and not isinstance(answer, bool) else None,
            "confidence": float(confidence) if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else None,
            "source_page": int(source_page) if isinstance(source_page, (int, float)) and not isinstance(source_page, bool) and source_page >= 1 else None,
            "evidence": str(candidate.get("evidence") or "").strip() or None,
        })
    return rows


def _consensus_rows(pass_rows: list[list[dict[str, Any]]], *, requested_passes: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Build a conservative provisional key and expose disagreement explicitly.

    Repeated Firecrawl answers measure repeatability, not truth.  The median is
    therefore only a review convenience; no row becomes benchmark gold here.
    """
    consensus: list[dict[str, Any]] = []
    exact_count = stable_count = disagreement_count = missing_count = 0
    for index, schema_row in enumerate(ASSET_SCHEMA):
        candidates = [rows[index] for rows in pass_rows]
        numeric = [
            (pass_index, float(row["answer_m_usd"]))
            for pass_index, row in enumerate(candidates)
            if isinstance(row.get("answer_m_usd"), (int, float)) and not isinstance(row.get("answer_m_usd"), bool)
        ]
        if not numeric:
            selected_index = 0
            selected_answer = None
            agreeing_indexes: list[int] = []
            stability = "missing"
            missing_count += 1
        else:
            center = float(median(value for _, value in numeric))
            tolerance = max(0.5, abs(center) * 0.001)
            agreeing_indexes = [pass_index for pass_index, value in numeric if abs(value - center) <= tolerance]
            selected_index = min(numeric, key=lambda pair: abs(pair[1] - center))[0]
            selected_answer = center
            if len(numeric) == requested_passes and all(value == numeric[0][1] for _, value in numeric):
                stability = "exact"
                exact_count += 1
            elif len(agreeing_indexes) >= 2:
                stability = "stable"
                stable_count += 1
            else:
                stability = "disagreement"
                disagreement_count += 1
        selected = candidates[selected_index]
        confidence_values = [
            float(candidates[pass_index]["confidence"])
            for pass_index in agreeing_indexes
            if isinstance(candidates[pass_index].get("confidence"), (int, float))
        ]
        agreement_count = len(agreeing_indexes)
        consensus.append({
            "classification": schema_row["classification"],
            "subclassification": schema_row["subclassification"],
            "item": schema_row["item"],
            "answer_m_usd": selected_answer,
            "confidence": (
                round((sum(confidence_values) / len(confidence_values)) * (agreement_count / requested_passes), 6)
                if confidence_values else None
            ),
            "source_page": selected.get("source_page"),
            "evidence": selected.get("evidence"),
            "pass_values": [row.get("answer_m_usd") for row in candidates],
            "agreement_count": agreement_count,
            "successful_passes": len(pass_rows),
            "agreement_ratio": round(agreement_count / requested_passes, 6),
            "stability": stability,
        })
    return consensus, {
        "requested_passes": requested_passes,
        "successful_passes": len(pass_rows),
        "exact_agreement_rows": exact_count,
        "stable_rows": stable_count,
        "disagreement_rows": disagreement_count,
        "missing_rows": missing_count,
    }


def pin_candidate_answers(
    document: dict[str, Any],
    parsed: dict[str, Any] | list[dict[str, Any]],
    *,
    requested_passes: int = 1,
    provider: str = "firecrawl",
) -> dict[str, Any]:
    """Persist source-bound model passes and a non-authoritative consensus."""
    pdf_path = Path(str(document["local_path"])).resolve()
    if not pdf_path.is_relative_to(CORPUS_ROOT.resolve()) or not pdf_path.is_file():
        raise ValueError("The canonical PDF is outside corpus storage or missing.")

    parsed_passes = parsed if isinstance(parsed, list) else [parsed]
    parsed_passes = [item for item in parsed_passes if isinstance(item, dict)]
    if not parsed_passes:
        raise ValueError("At least one successful candidate pass is required.")
    requested_passes = max(int(requested_passes), len(parsed_passes))
    normalized_provider = str(provider or "configured_llm").strip().lower()
    candidate_method = f"{normalized_provider}_semantic_mapping" if requested_passes == 1 else f"{normalized_provider}_multi_pass_consensus"
    normalized_passes = [_normalize_candidate_rows(item) for item in parsed_passes]
    rows, consensus_summary = _consensus_rows(normalized_passes, requested_passes=requested_passes)

    verification_dir = pdf_path.parent / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)
    # Replace the candidate session as one unit so a shorter later session
    # cannot inherit an old third pass and overstate agreement.
    for stale_pass in verification_dir.glob("candidate_pass_*.json"):
        stale_pass.unlink(missing_ok=True)
    pass_paths: list[str] = []
    for pass_number, (pass_payload, normalized_rows) in enumerate(zip(parsed_passes, normalized_passes), start=1):
        pass_path = verification_dir / f"candidate_pass_{pass_number}.json"
        pass_artifact = {
            "status": "provisional_candidate_pass",
            "authoritative_golden_set": False,
            "provider": normalized_provider,
            "pass_number": pass_number,
            "pdf_sha256": document.get("sha256"),
            "source_url": document.get("source_url"),
            "mode": str(pass_payload.get("mode") or "auto"),
            "detected_fiscal_year": pass_payload.get("detected_fiscal_year"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rows": normalized_rows,
            "response_metadata": pass_payload.get("metadata") or {},
        }
        pass_temporary = pass_path.with_suffix(".json.tmp")
        pass_temporary.write_text(json.dumps(pass_artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        pass_temporary.replace(pass_path)
        pass_paths.append(str(pass_path))
    candidate_path = verification_dir / "candidate_answers.json"
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = {
        "status": "human_review_required",
        "authoritative_golden_set": False,
        "provider": normalized_provider,
        "candidate_method": candidate_method,
        "pdf_sha256": document.get("sha256"),
        "source_url": document.get("source_url"),
        "mode": str(parsed_passes[0].get("mode") or "auto"),
        "detected_fiscal_year": parsed_passes[0].get("detected_fiscal_year"),
        "generated_at": generated_at,
        "rows": rows,
        "consensus_summary": consensus_summary,
        "candidate_pass_paths": pass_paths,
    }
    temporary = candidate_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(candidate_path)
    existing_verification = document.get("verification") if isinstance(document.get("verification"), dict) else {}
    preserve_approval = (
        existing_verification.get("status") == "human_verified"
        and existing_verification.get("source_sha256") == document.get("sha256")
        and bool(existing_verification.get("approved_path"))
    )
    updated = {
        **document,
        "verification": {
            **existing_verification,
            "status": "human_verified" if preserve_approval else "human_review_required",
            "source_sha256": document.get("sha256"),
            "provider": normalized_provider,
            "candidate_path": str(candidate_path),
            "candidate_pass_paths": pass_paths,
            "candidate_method": candidate_method,
            "consensus_summary": consensus_summary,
            "approved_path": existing_verification.get("approved_path") if preserve_approval else None,
            "generated_at": generated_at,
            "approved_at": existing_verification.get("approved_at") if preserve_approval else None,
        },
    }
    return upsert_document(updated)
