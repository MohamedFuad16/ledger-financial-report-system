"""
End-to-end extraction pipeline shared by every entry point.

The Flask API (single + batch) and the legacy Streamlit app all call
``run_pipeline`` so that a run produced by one of them is byte-for-byte
comparable with a run produced by another: same strategies, same prompt
assembly, same Pydantic validation, same prediction.json layout.
"""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from api_client import GLMError, parse_assistant_json, response_usage, run_extraction
from extraction import STRATEGIES, get_strategy
from models import EXPECTED_ROW_COUNT, SchemaValidationError, rows_as_dicts, validate_extraction
from normalize import normalize_payload
from reconcile import derive_identity_values, reconcile, reconciliation_summary
from prompts import build_evidence_retry_prompt, build_user_prompt
from schema import (
    ASSET_SCHEMA,
    ASSIGNMENT_GOLDEN_SOURCE_SHA256,
    GOLDEN_ANSWERS_STORE,
    SOURCE_BOUND_GOLDEN_ANSWERS,
    SUBTOTAL_IDENTITIES,
)

UPLOAD_DIR = Path("uploads")
RUNS_DIR = Path("runs")

# The workspace the corpus evaluation runner stamps on its runs. The published
# benchmark feed serves only this workspace, so a visitor's demo extraction on
# a corpus PDF can never move the numbers the dashboard reports.
BENCHMARK_WORKSPACE_ID = "full-corpus-eval"

# Values below this confidence are treated as "the model did not answer".
#
# 0.8, not 0.5, and the cut-off is measured rather than chosen. Across 824
# scored (row, run) observations the model's own confidence separates cleanly
# at exactly this point:
#
#     confidence      n     actually correct
#     < 0.50        104          2.9%
#     0.50-0.70      91         60.4%
#     0.70-0.80      88         58.0%
#     0.80-0.90     160         93.8%
#     0.90-0.95      78        100.0%
#     >= 0.95       303        100.0%
#
# Accepting at 0.5 admits the 0.50-0.80 band, which is 59% correct - a coin
# flip counted as an answer. Precision of accepted answers: 88.5% at 0.5,
# 98.2% at 0.8.
CONFIDENCE_THRESHOLD = 0.8

# Run ids and upload names are timestamped to the second; a batch can start
# several runs inside the same second, so a process-wide counter keeps them
# unique instead of letting two runs share (and overwrite) one directory.
_name_lock = threading.Lock()
_name_counter = 0


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    """Reduce arbitrary user input to a single safe path component."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(str(name)).name).strip("._")
    return cleaned or "annual_report.pdf"


def report_identity(name: str, fiscal_year: Any = "") -> tuple[str, str, str]:
    """Return ``(company_slug, year, canonical_filename)`` for a report name."""
    stem = Path(str(name or "annual_report.pdf")).name.rsplit(".", 1)[0]
    # Uploaded files and corpus files may already carry our unique timestamp.
    stem = re.sub(r"^\d{8}T\d{6}Z_\d{3}_", "", stem)
    match = re.search(r"(19|20)\d{2}", str(fiscal_year or "")) or re.search(r"(19|20)\d{2}", stem)
    year = match.group() if match else "unknown"
    company = re.sub(r"(?i)annual[_\s-]*report|form[_\s-]*10[_\s-]*k", "_", stem)
    company = re.sub(r"(19|20)\d{2}", "_", company)
    company = re.sub(r"(?i)updated|final|online|pdfa|web", "_", company)
    company = re.sub(r"[^\w]+", "_", company, flags=re.UNICODE).strip("_") or "Unknown_Company"
    return company, year, f"{company}_annual_report_{year}.pdf"


def normalize_company_key(value: Any) -> str:
    """Unicode-safe company identity for source-bound benchmark matching."""
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def _unique_stamp() -> str:
    global _name_counter
    with _name_lock:
        _name_counter += 1
        counter = _name_counter
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{counter:03d}"


# Runs are filed as runs/<strategy>/FY<year>/<run_id>/. The fiscal year is only
# known once the model has replied, so a run starts in the strategy's _pending
# folder and is moved when it finishes. A run that never produced a fiscal year
# stays under _pending, which is also where a failed run's artifacts remain.
PENDING = "_pending"


def create_run_dir(prefix: str = "S1", strategy_key: str = "s1") -> Path:
    ensure_dirs()
    run_dir = RUNS_DIR / strategy_key / PENDING / f"{prefix}_{_unique_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def fiscal_year_folder(fiscal_year: Any) -> str:
    match = re.search(r"(19|20)\d{2}", str(fiscal_year or ""))
    return f"FY{match.group()}" if match else "FY-unknown"


def file_run(
    run_dir: Path,
    strategy_key: str,
    fiscal_year: Any,
    report_name: str | None = None,
) -> Path:
    """File new runs as ``company/year/output-timestamp``; retain a legacy fallback."""
    company, _, _ = report_identity(report_name or strategy_key, fiscal_year)
    target_parent = RUNS_DIR / company / fiscal_year_folder(fiscal_year)
    target_parent.mkdir(parents=True, exist_ok=True)
    target = target_parent / run_dir.name
    if target.resolve() == run_dir.resolve():
        return run_dir
    suffix = 1
    while target.exists():
        # A collision means another process produced the same stamped id;
        # deleting its artifacts would destroy a finished run.
        target = target_parent / f"{run_dir.name}_dup{suffix}"
        suffix += 1
    shutil.move(str(run_dir), str(target))

    # Leave no empty _pending folder behind once it has been drained.
    try:
        pending = run_dir.parent
        if pending.name == PENDING and not any(pending.iterdir()):
            pending.rmdir()
    except OSError:
        pass
    return target


def find_run_dir(run_id: str) -> Optional[Path]:
    """Locate a run anywhere in the tree by its id."""
    safe = safe_filename(run_id)
    if not RUNS_DIR.exists():
        return None
    direct = RUNS_DIR / safe
    if direct.is_dir():
        return direct                      # pre-migration layout
    for candidate in RUNS_DIR.rglob(safe):
        if candidate.is_dir():
            return candidate
    return None


def iter_run_dirs():
    """Every run directory, whatever layout it is stored in."""
    if not RUNS_DIR.exists():
        return
    seen: set[Path] = set()
    for artifact in list(RUNS_DIR.rglob("prediction.json")) + list(RUNS_DIR.rglob("request.json")):
        directory = artifact.parent
        if directory not in seen:
            seen.add(directory)
            yield directory


def store_pdf(source: Path | str, original_name: str | None = None) -> Path:
    """Copy an on-disk PDF into ``uploads/company/year/timestamp``."""
    ensure_dirs()
    source = Path(source)
    stamp = _unique_stamp()
    company, year, canonical = report_identity(original_name or source.name)
    target = UPLOAD_DIR / company / year / stamp / canonical
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def save_upload(file_storage) -> Path:
    """Persist a browser upload under ``uploads/company/year/timestamp``."""
    ensure_dirs()
    stamp = _unique_stamp()
    company, year, canonical = report_identity(file_storage.filename)
    target = UPLOAD_DIR / company / year / stamp / canonical
    target.parent.mkdir(parents=True, exist_ok=True)
    file_storage.save(target)
    return target


def apply_confidence_gate(rows: list[dict]) -> list[dict]:
    """
    Stamp each row with the gate result, once, so nothing downstream re-derives it.

    The raw ``answer_m_usd`` is deliberately preserved rather than overwritten
    with null: the value the model produced is evidence, and keeping it is what
    made it possible to re-score every historical run when the threshold moved
    from 0.5 to 0.8. ``accepted`` is the field every consumer should read.
    """
    gated = []
    for row in rows:
        confidence = row.get("confidence")
        confident = confidence is None or float(confidence) >= CONFIDENCE_THRESHOLD
        gated.append({**row, "accepted": bool(confident and row.get("answer_m_usd") is not None)})
    return gated


def merge_retry_rows(
    rows: list[dict],
    retry_rows: list[dict],
    missing_items: list[str],
    replaceable_items: list[str] | None = None,
) -> tuple[list[dict], list[str], list[str]]:
    """
    Merge one evidence-retry reply into the first-pass rows.

    Rows that were null in the first pass and explicitly re-asked are filled.
    Rows named in ``replaceable_items`` (participants of failed deterministic
    identities) may be *proposed* for replacement; the caller must accept the
    proposal only when reconciliation strictly improves. Any other row keeps
    its first-pass value untouched.
    """
    wanted = {str(item) for item in missing_items}
    replaceable = {str(item) for item in replaceable_items or []}
    retry_by_item = {str(row.get("item")): row for row in retry_rows}
    merged: list[dict] = []
    recovered: list[str] = []
    replaced: list[str] = []
    for row in rows:
        item = str(row.get("item"))
        candidate = retry_by_item.get(item)
        candidate_value = candidate.get("answer_m_usd") if candidate else None
        first_pass_value = row.get("answer_m_usd")
        take = False
        if candidate_value is not None and item in wanted and first_pass_value is None:
            recovered.append(item)
            take = True
        elif (
            candidate_value is not None
            and item in replaceable
            and first_pass_value is not None
            and float(candidate_value) != float(first_pass_value)
        ):
            replaced.append(item)
            take = True
        if take:
            merged.append({
                **row,
                "answer_m_usd": candidate_value,
                "confidence": candidate.get("confidence"),
                "source_page": candidate.get("source_page"),
                "source_label": candidate.get("source_label"),
                "evidence": ("[evidence retry] " + str(candidate.get("evidence") or "")).strip(),
            })
        else:
            merged.append(row)
    return merged, recovered, replaced


def detect_source_value_quantum(text: str) -> float:
    """Return the report's displayed monetary precision in million units."""
    sample = str(text or "")[:200_000].lower()
    if re.search(r"単位\s*[：:]\s*千円|in thousands|thousands of", sample):
        return 0.001
    if re.search(r"単位\s*[：:]\s*百万円|in millions|millions of", sample):
        return 1.0
    if re.search(r"単位\s*[：:]\s*円", sample):
        return 0.000001
    return 0.0


def compute_metrics(
    rows: list[dict] | None,
    fiscal_year: Any,
    company: str | None = None,
    source_pdf_sha256: str | None = None,
    currency: str = "USD",
) -> dict[str, Any]:
    """
    Score a prediction against the golden answers for its fiscal year.

    Four different questions, four numbers:

    - ``coverage``  - of the fixed schema, how many rows contain a value?
    - ``accuracy``  - of the rows the answer key defines, how many are exactly
      right, independent of the model's self-reported confidence?
    - ``precision`` - of the rows containing a value, how many are right?
    - ``confidence_accepted_coverage`` - how many values also clear the
      diagnostic confidence threshold? This is a review-priority signal, not a
      correctness gate: model confidence is not ground truth.

    A fiscal year with no golden set scores no accuracy at all rather than being
    silently compared against another year.
    """
    year = re.search(r"(19|20)\d{2}", str(fiscal_year or ""))
    normalized_company = normalize_company_key(company)
    normalized_currency = str(currency or "USD").strip().upper()
    golden: dict[str, float] = {}
    gold_status = "human_review_required"
    gold_company = None
    gold_value_quantum = 0.0
    # FY2022 is the only answer key supplied by the assignment. It is bound to
    # the exact official PDF bytes so a mislabeled replacement cannot inherit
    # the assignment answers.
    if (
        year
        and year.group() == "2022"
        and normalized_company == "3m"
        and normalized_currency == "USD"
        and source_pdf_sha256 == ASSIGNMENT_GOLDEN_SOURCE_SHA256
    ):
        golden = GOLDEN_ANSWERS_STORE["2022"]
        gold_status = "assignment_supplied"
        gold_company = "3M"
        gold_value_quantum = 1.0
    elif source_pdf_sha256:
        # Independently audited fixtures and human-approved corpus keys are
        # bound to the exact bytes that were run. A same-year PDF replacement
        # cannot inherit gold.
        audited = SOURCE_BOUND_GOLDEN_ANSWERS.get(source_pdf_sha256)
        if audited:
            audited_currency = str(audited.get("currency") or "USD").strip().upper()
            # The SHA-256 already pins the exact bytes, so the fixture's own
            # company and fiscal year are authoritative; a filename-derived
            # identity on an uploaded copy of the same PDF must not detach the
            # gold. Only the output currency must agree, because values in a
            # different display currency are not comparable numbers.
            if audited_currency == normalized_currency:
                golden = {
                    str(item): float(value)
                    for item, value in dict(audited.get("answers") or {}).items()
                }
                gold_status = str(audited.get("status") or "independently_verified")
                gold_company = str(audited.get("company") or company or "")
                gold_value_quantum = float(audited.get("source_value_quantum") or 1.0)

        # A corpus review is the fallback for documents not in the fixed audit
        # fixtures above.
        try:
            from corpus.manifest import find_document, verification_payload

            document = find_document(source_pdf_sha256)
            verification = verification_payload(document) if document else None
        except Exception:  # a malformed gold artifact must degrade to unscored, never crash a paid run
            verification = None
        verification_currency = str((verification or {}).get("currency") or "USD").strip().upper()
        if (
            not golden
            and verification
            and verification.get("status") == "human_verified"
            and verification_currency == normalized_currency
        ):
            golden = {
                str(item.get("item")): float(item["answer_m_usd"])
                for item in verification.get("rows", [])
                if item.get("answer_m_usd") is not None
            }
            gold_status = "human_verified"
            gold_company = str(company or document.get("company") or "")
            gold_value_quantum = float((verification or {}).get("source_value_quantum") or 0.0)

    exact = 0
    accepted_exact = 0
    compared = 0
    filled = 0
    accepted_filled = 0
    committed = 0
    accepted_committed = 0

    for row in rows or []:
        if not isinstance(row, dict):
            continue
        value = row.get("answer_m_usd")
        # Prefer the stamped gate result; fall back for rows stored before it existed.
        if "accepted" in row:
            confident = bool(row["accepted"]) or value is None
            accepted = bool(row["accepted"])
        else:
            confidence = row.get("confidence")
            confident = confidence is None or float(confidence) >= CONFIDENCE_THRESHOLD
            accepted = confident and value is not None
        has_value = value is not None
        if has_value:
            filled += 1
        if accepted:
            accepted_filled += 1

        expected = golden.get(row.get("item"))
        if expected is None:
            continue
        compared += 1
        if not has_value:
            continue
        committed += 1
        try:
            exact_tolerance = gold_value_quantum / 2 + 1e-9 if gold_value_quantum > 0 else 0.5
            if abs(float(value) - float(expected)) <= exact_tolerance:
                exact += 1
                if accepted:
                    accepted_exact += 1
        except (TypeError, ValueError):
            continue
        if accepted:
            accepted_committed += 1

    return {
        "accuracy": round(exact / compared * 100, 1) if compared else None,
        "coverage": round(filled / EXPECTED_ROW_COUNT * 100, 1),
        "precision": round(exact / committed * 100, 1) if committed else None,
        "exact_matches": exact,
        "total_compared": compared,
        "filled_fields": filled,
        "committed_and_compared": committed,
        "confidence_accepted_coverage": round(accepted_filled / EXPECTED_ROW_COUNT * 100, 1),
        "confidence_accepted_precision": (
            round(accepted_exact / accepted_committed * 100, 1) if accepted_committed else None
        ),
        "confidence_accepted_fields": accepted_filled,
        "has_golden": bool(golden),
        "gold_company": gold_company if golden else None,
        "gold_status": gold_status if golden else "human_review_required",
        "gold_currency": normalized_currency if golden else None,
        "answer_unit": f"M {normalized_currency}",
        "gold_value_quantum": gold_value_quantum if golden else None,
    }


def result_table(rows: list[dict], answer_unit: str = "M USD") -> list[dict]:
    return [
        {
            "Classification": r["classification"],
            "Subclassification": r["subclassification"],
            "Item": r["item"],
            "Description": r["description"],
            # Confidence controls review priority, not whether an extracted
            # value is visible. The reviewer must be able to inspect and amend
            # every pre-filled value side by side with the source PDF.
            f"Answer ({answer_unit})": r["answer_m_usd"],
        }
        for r in rows
    ]


def evidence_table(rows: list[dict]) -> list[dict]:
    return [
        {
            "Item": r["item"],
            "Source Page": r["source_page"],
            "Source Label": r["source_label"],
            "Evidence": r["evidence"],
        }
        for r in rows
    ]


def run_pipeline(
    *,
    pdf_path: Path,
    settings: dict[str, Any],
    strategy_key: str = "s1",
    system_prompt: str,
    fiscal_year_hint: str = "",
    enable_reasoning: bool = True,
    temperature: float = 0.0,
    reasoning_effort: str = "",
    display_name: Optional[str] = None,
    company_hint: str = "",
    output_currency: str = "USD",
    workspace_id: str = "legacy-public",
    on_progress=None,
) -> dict[str, Any]:
    """
    Convert one PDF, call the model once, validate the reply, persist the run.

    Returns the prediction dict that is also written to ``prediction.json``.
    Raises GLMError / SchemaValidationError / RuntimeError on failure; the run
    directory is kept either way so request.json and raw_response.json survive
    for debugging.
    """
    strategy = get_strategy(strategy_key)
    run_dir = create_run_dir(prefix=strategy.run_prefix, strategy_key=strategy.key)

    try:
        return _run_pipeline_inner(
            strategy=strategy, run_dir=run_dir, pdf_path=pdf_path, settings=settings,
            system_prompt=system_prompt, fiscal_year_hint=fiscal_year_hint,
            enable_reasoning=enable_reasoning, temperature=temperature,
            reasoning_effort=reasoning_effort,
            display_name=display_name, company_hint=company_hint,
            output_currency=output_currency, workspace_id=workspace_id, on_progress=on_progress,
        )
    except Exception:
        # A run that failed before writing anything leaves an empty directory
        # behind; those accumulate and clutter the tree. Artifacts that *were*
        # written are kept, under _pending, so a failure stays inspectable.
        try:
            if run_dir.is_dir() and not any(run_dir.iterdir()):
                run_dir.rmdir()
                pending = run_dir.parent
                if pending.name == PENDING and not any(pending.iterdir()):
                    pending.rmdir()
        except OSError:
            pass
        raise


def _run_pipeline_inner(
    *,
    strategy,
    run_dir: Path,
    pdf_path: Path,
    settings: dict[str, Any],
    system_prompt: str,
    fiscal_year_hint: str,
    enable_reasoning: bool,
    temperature: float,
    reasoning_effort: str,
    display_name: Optional[str],
    company_hint: str,
    output_currency: str,
    workspace_id: str,
    on_progress,
) -> dict[str, Any]:
    pipeline_started = time.perf_counter()
    step_started: dict[str, float] = {}

    def progress(step: str, message: str, **extra: Any) -> None:
        """Report pipeline position. ``step`` matches the UI's step ids."""
        now = time.perf_counter()
        if step not in step_started:
            step_started[step] = now
        if extra.get("done") and "duration_seconds" not in extra:
            extra["duration_seconds"] = round(now - step_started[step], 2)
        if on_progress:
            on_progress({"step": step, "message": message, "run_id": run_dir.name, **extra})

    progress("upload", f"Saved {Path(pdf_path).name}", done=True, duration_seconds=0.0)

    progress("extract", f"Extracting text · {strategy.label}")
    extract_started = time.perf_counter()
    ocr_enabled = bool(getattr(strategy, "ocr_enabled", False))
    ocr_policy = str(getattr(strategy, "ocr_policy", "off")) if ocr_enabled else "off"
    extracted = (
        strategy(pdf_path, ocr_policy=ocr_policy, ocr_context=settings)
        if ocr_enabled
        else strategy(pdf_path)
    )
    extract_seconds = round(time.perf_counter() - extract_started, 2)
    if not extracted.text.strip() or extracted.readable_pages == 0:
        detail = extracted.warnings[-1] if extracted.warnings else (
            "No readable text could be extracted from the PDF."
        )
        raise RuntimeError(detail)
    selected_page_count = extracted.diagnostics.get("selected_page_count")
    extraction_summary = (
        f"{extracted.page_count} pages inspected · {selected_page_count} selected · "
        f"{extracted.char_count:,} characters · {extract_seconds:.1f}s"
        if selected_page_count is not None
        else f"{extracted.page_count} pages · {extracted.char_count:,} characters · {extract_seconds:.1f}s"
    )
    progress(
        "extract",
        extraction_summary,
        done=True,
        page_count=extracted.page_count,
        selected_page_count=selected_page_count,
        selected_pages=extracted.diagnostics.get("selected_pages"),
        approx_tokens=extracted.approx_tokens,
        extract_seconds=extract_seconds,
    )

    progress("prompt", f"Building {EXPECTED_ROW_COUNT}-row schema prompt")
    user_prompt = build_user_prompt(
        report_text=extracted.text,
        extraction_note=strategy.extraction_note,
        fiscal_year=fiscal_year_hint,
        # Each parser contributes whatever structure it discovered. Parsers that
        # discover nothing send nothing, so the prompt is unchanged for them.
        diagnostics=extracted.diagnostics,
        output_currency=output_currency,
    )
    progress("prompt", f"~{extracted.approx_tokens:,} input tokens", done=True)

    progress("api", f"Waiting on {settings['model']}")
    effective_effort = (
        reasoning_effort or settings.get("reasoning_effort", "") or "medium"
    ) if enable_reasoning else "none"
    raw_response, elapsed = run_extraction(
        api_key=settings["api_key"],
        model=settings["model"],
        base_url=settings["base_url"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        run_dir=run_dir,
        enable_reasoning=enable_reasoning,
        temperature=temperature,
        provider=settings.get("provider", ""),
        session_id=run_dir.name,
        # A per-run override from the strategy panel wins over the saved default.
        reasoning_effort=effective_effort,
        on_retry=lambda attempt, delay: progress(
            "api", f"Rate limited — retry {attempt} in {delay:.0f}s", throttled=True
        ),
    )
    usage = response_usage(raw_response)
    cache_note = ""
    if usage.get("cached_tokens"):
        cache_note = f" · {usage['cached_tokens']:,} tokens from cache ({usage.get('cache_hit_rate', 0)}%)"
    progress("api", f"Model replied in {elapsed:.1f}s{cache_note}", done=True)

    progress("validate", "Checking the reply against the output contract")
    contract_repair_attempts = 0
    contract_repair_usage: dict[str, Any] = {}

    def parse_and_validate(response: dict[str, Any]):
        parsed_payload = parse_assistant_json(response)
        # Repair representation first, then validate. The two are separate on
        # purpose: repairs are recorded, and anything unrepairable still fails.
        normalized_payload, normalization_notes = normalize_payload(parsed_payload)
        return validate_extraction(normalized_payload), normalization_notes

    try:
        result, repairs = parse_and_validate(raw_response)
    except (GLMError, SchemaValidationError) as exc:
        # One bounded semantic repair is materially different from transport
        # retries: the invalid assistant reply and the exact contract error are
        # preserved in context, while the original system/user prefix stays intact.
        contract_repair_attempts = 1
        progress("validate", "Contract mismatch · asking the model for corrected JSON")
        try:
            previous_content = raw_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            previous_content = json.dumps(raw_response, ensure_ascii=False)
        if not isinstance(previous_content, str):
            previous_content = json.dumps(previous_content, ensure_ascii=False)
        repair_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": previous_content},
            {
                "role": "user",
                "content": (
                    "Your previous JSON did not satisfy the required output contract. "
                    "Return one corrected JSON object only. Preserve evidence-supported "
                    f"values and fix exactly these contract errors:\n{exc}"
                ),
            },
        ]
        repaired_response, repair_elapsed = run_extraction(
            api_key=settings["api_key"],
            model=settings["model"],
            base_url=settings["base_url"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            run_dir=run_dir,
            enable_reasoning=enable_reasoning,
            temperature=temperature,
            provider=settings.get("provider", ""),
            session_id=run_dir.name,
            reasoning_effort=effective_effort,
            messages=repair_messages,
            artifact_suffix="_repair_1",
            on_retry=lambda attempt, delay: progress(
                "validate", f"Rate limited during repair — retry {attempt} in {delay:.0f}s", throttled=True
            ),
        )
        elapsed += repair_elapsed
        contract_repair_usage = response_usage(repaired_response)
        result, repairs = parse_and_validate(repaired_response)
    # Complete only algebraically unique nulls before applying the confidence
    # gate. This uses the public schema identities, never benchmark gold.
    rows, deterministic_derivations = derive_identity_values(rows_as_dicts(result))
    # Apply the confidence gate once, here, so scoring and reconciliation below
    # agree on what counts as an answer.
    rows = apply_confidence_gate(rows)
    progress("validate", f"{len(rows)} rows conform to the contract")

    # Strategy 3 evaluation loop: when the selected evidence packet left rows
    # unanswered, or deterministic identity checks failed, verify whether the
    # needed pages were actually retrieved and, if unsent ranked pages remain,
    # run exactly one targeted follow-up call. The retry consults the public
    # schema and parser output only — never gold. Null rows may be filled;
    # failed-identity rows may be replaced only when the replacement makes
    # reconciliation strictly better, so a second call cannot corrupt evidence
    # the first call already established.
    evidence_retry: dict[str, Any] = {"attempted": False, "reason": None}
    source_value_quantum = detect_source_value_quantum(extracted.text)
    missing_items = [str(row.get("item")) for row in rows if row.get("answer_m_usd") is None]
    failed_identity_items: list[str] = []
    pre_reconciliation: dict[str, Any] | None = None
    if strategy.experiment == "intelligent_scan" and getattr(extracted, "retained_pages", None):
        pre_reconciliation = reconcile(rows, value_quantum=source_value_quantum)
        failed_identity_names = set(pre_reconciliation.get("failed_identities") or [])
        if failed_identity_names:
            participants: list[str] = []
            for total_item, parts in SUBTOTAL_IDENTITIES:
                if total_item in failed_identity_names:
                    participants.extend([total_item, *parts])
            seen: set[str] = set()
            failed_identity_items = [
                item for item in participants
                if item not in seen and not seen.add(item) and item not in set(missing_items)
            ]
    # A packet that already contains every readable page decides absence and
    # zeros on its own — nulls there are answers, not evidence gaps, so only a
    # failed deterministic identity (a misread) justifies the second call.
    # A one-page filing is fully seen by every strategy, so the sparse-total
    # verification applies beyond the gate's own complete-packet diagnostic.
    complete_packet = bool(
        extracted.diagnostics.get("complete_document_packet")
        or (int(extracted.page_count or 0) == 1 and int(extracted.readable_pages or 0) == 1)
    )
    # Exception: a condensed statutory summary yields essentially one number
    # (Total Assets) and nothing for the identities to check, so a misread —
    # e.g. a capital reserve mistaken for the total — is invisible to
    # arithmetic. Those runs get one verification call that must re-derive the
    # total from BOTH sides of the printed balance sheet.
    # Zeros are decided absences, not substantive answers: a model that fills
    # every schema row with 0.0 on a one-page gazette must not bypass the
    # sparse-total verification the way a 27-zero response otherwise would.
    answered_row_count = sum(
        1 for row in rows
        if row.get("answer_m_usd") is not None and float(row.get("answer_m_usd") or 0.0) != 0.0
    )
    total_assets_answered = any(
        str(row.get("item")) == "Total Assets" and row.get("answer_m_usd") is not None
        for row in rows
    )
    verification_mode = (
        complete_packet
        and not failed_identity_items
        and total_assets_answered
        and answered_row_count <= 3
    )
    if verification_mode:
        # The both-sides verification derives the printed section totals on
        # the way to the total, so a misassigned section (a neighboring
        # column or company read into the wrong row) is correctable too.
        retry_items = ["Total Assets", "Current Assets", "Fixed Assets", "Deferred Charges"]
    elif complete_packet:
        retry_items = failed_identity_items
    else:
        retry_items = missing_items + failed_identity_items
    if complete_packet and missing_items and not failed_identity_items and not verification_mode:
        evidence_retry = {
            "attempted": False,
            "reason": "packet covers the complete readable document; remaining nulls are decided absences",
            "missing_rows": missing_items,
        }
    if (
        strategy.experiment == "intelligent_scan"
        and retry_items
        and getattr(extracted, "retained_pages", None)
    ):
        from intelligent_scan import select_retry_pages

        already_sent = set(extracted.diagnostics.get("selected_pages") or [])
        retry_pages, retry_diagnostics = select_retry_pages(
            extracted.retained_pages,
            missing_items=retry_items,
            exclude_pages=already_sent,
            maximum_pages=3,
        )
        if retry_pages or extracted.text.strip():
            progress(
                "validate",
                f"{len(missing_items)} rows unanswered, {len(failed_identity_items)} in failed identities "
                + (
                    "· retrying with pages " + ", ".join(str(page) for page, _ in retry_pages)
                    if retry_pages
                    else "· re-reading the complete packet (no unsent pages remain)"
                ),
            )
            retry_prompt = build_evidence_retry_prompt(
                additional_pages_text="\n\n".join(
                    f"[page {page}]\n{text}" for page, text in retry_pages
                ),
                missing_items=retry_items,
                detected_fiscal_year=result.detected_fiscal_year or "",
                output_currency=output_currency,
                # A failed identity often means a figure in the original packet
                # was misread — and when no unsent pages remain the packet IS
                # the complete readable report — so the second look re-reads it
                # alongside any additional pages.
                original_packet_text=(
                    extracted.text
                    if (failed_identity_items or verification_mode or not retry_pages)
                    else ""
                ),
                verification_note=(
                    (
                        "VERIFICATION: the first pass committed a Total Assets figure from a "
                        "condensed balance-sheet summary where no other row can cross-check it. "
                        "Re-derive Total Assets independently from BOTH sides of the printed "
                        "statement: it must equal the sum of the printed asset components AND "
                        "equal liabilities plus net assets computed from the printed equity "
                        "components (capital, reserves, retained earnings/deficit, share "
                        "warrants). The largest printed figure is often a capital reserve, not "
                        "the total. Return the figure that reconciles on both sides."
                    )
                    if verification_mode
                    else ""
                ),
            )
            retry_started = time.perf_counter()
            retry_time_accounted = 0.0
            try:
                retry_response, retry_elapsed = run_extraction(
                    api_key=settings["api_key"],
                    model=settings["model"],
                    base_url=settings["base_url"],
                    system_prompt=system_prompt,
                    user_prompt=retry_prompt,
                    run_dir=run_dir,
                    enable_reasoning=enable_reasoning,
                    temperature=temperature,
                    provider=settings.get("provider", ""),
            session_id=run_dir.name,
                    reasoning_effort=effective_effort,
                    artifact_suffix="_evidence_retry_1",
                    on_retry=lambda attempt, delay: progress(
                        "validate",
                        f"Rate limited during evidence retry — retry {attempt} in {delay:.0f}s",
                        throttled=True,
                    ),
                )
                elapsed += retry_elapsed
                retry_time_accounted = retry_elapsed
                retry_result, _ = parse_and_validate(retry_response)
                replaceable_items = (
                    ["Total Assets", "Current Assets", "Fixed Assets", "Deferred Charges"]
                    if verification_mode else failed_identity_items
                )
                merged_rows, recovered, replaced = merge_retry_rows(
                    rows, rows_as_dicts(retry_result), missing_items, replaceable_items
                )
                if replaced and not verification_mode:
                    # Replacements are accepted only as a block and only when
                    # they deterministically improve reconciliation. In
                    # verification mode nothing reconciles either way, so the
                    # both-sides re-derivation is accepted as the answer.
                    trial = reconcile(merged_rows, value_quantum=source_value_quantum)
                    improves = (
                        int(trial.get("failed") or 0) < int(pre_reconciliation.get("failed") or 0)
                        and int(trial.get("passed") or 0) >= int(pre_reconciliation.get("passed") or 0)
                    )
                    if not improves:
                        merged_rows, recovered, replaced = merge_retry_rows(
                            rows, rows_as_dicts(retry_result), missing_items, []
                        )
                merged_rows, retry_derivations = derive_identity_values(merged_rows)
                deterministic_derivations = deterministic_derivations + retry_derivations
                rows = apply_confidence_gate(merged_rows)
                evidence_retry = {
                    "attempted": True,
                    "verification_mode": verification_mode,
                    "missing_rows": missing_items,
                    "failed_identity_rows": failed_identity_items,
                    "pages_added": retry_diagnostics.get("retry_pages"),
                    "page_scores": retry_diagnostics.get("retry_scores"),
                    "recovered_rows": recovered,
                    "replaced_rows": replaced,
                    "still_missing_rows": [
                        str(row.get("item")) for row in rows if row.get("answer_m_usd") is None
                    ],
                    "usage": response_usage(retry_response),
                    "elapsed_seconds": round(retry_elapsed, 2),
                }
                progress(
                    "validate",
                    f"Evidence retry recovered {len(recovered)} and re-derived {len(replaced)} "
                    f"of {len(retry_items)} targeted rows",
                )
            except Exception as exc:  # noqa: BLE001 - the retry must never fail the run
                # A failed attempt still burned real wall-clock (including any
                # backoff sleeps inside the client); it must not vanish from
                # the run's timing.
                # Add only wall-clock not already booked by a successful API
                # call earlier in this try-block, so a post-API parsing
                # failure cannot double-count the provider time.
                retry_wasted = round(max(0.0, time.perf_counter() - retry_started - retry_time_accounted), 2)
                elapsed += retry_wasted
                evidence_retry = {
                    "attempted": True,
                    "missing_rows": missing_items,
                    "failed_identity_rows": failed_identity_items,
                    "pages_added": retry_diagnostics.get("retry_pages"),
                    "recovered_rows": [],
                    "replaced_rows": [],
                    "elapsed_seconds": retry_wasted,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                progress("validate", "Evidence retry failed — keeping first-pass values")

    # Deterministic arithmetic check, separate from the type contract above and
    # from scoring below. Needs no answer key, so it is the only quality signal
    # that survives the move to companies we have no golden data for.
    reconciliation = reconcile(rows, value_quantum=source_value_quantum)
    progress("validate", reconciliation_summary(reconciliation), done=True)

    pinned_year = (fiscal_year_hint or "").strip()
    fiscal_year = pinned_year or result.detected_fiscal_year
    if pinned_year and result.detected_fiscal_year and result.detected_fiscal_year != pinned_year:
        # The corpus year was screened against the filing's own cover; a model
        # that answers the comparative year must not re-file the run or detach
        # it from its source-bound gold.
        extracted.warnings.append(
            f"Model reported fiscal year {result.detected_fiscal_year}; "
            f"kept the screened corpus year {pinned_year} as authoritative."
        )
    company, _, _ = report_identity(company_hint or display_name or Path(pdf_path).name, fiscal_year)
    currency = str(output_currency or "USD").strip().upper() or "USD"
    answer_unit = f"M {currency}"
    source_pdf_sha256 = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    metrics = compute_metrics(rows, fiscal_year, company, source_pdf_sha256, currency)
    metrics["consistency"] = reconciliation["consistency"]

    progress("output", "Saving extraction result")
    prediction: dict[str, Any] = {
        "run_id": run_dir.name,
        "workspace_id": workspace_id,
        "strategy": strategy.key,
        "strategy_label": strategy.label,
        "parser": strategy.parser,
        "experiment": strategy.experiment,
        "experiment_schema_version": 2,
        "ocr_enabled": strategy.ocr_enabled,
        "ocr_policy": ocr_policy if strategy.ocr_enabled else "off",
        "company": company,
        "currency": currency,
        "value_scale": "millions",
        "answer_unit": answer_unit,
        "source_value_quantum": source_value_quantum,
        "source_pdf_sha256": source_pdf_sha256,
        "model": settings["model"],
        "base_url": settings["base_url"],
        "fiscal_year": fiscal_year,
        "detected_fiscal_year": result.detected_fiscal_year or "",
        "enable_reasoning": enable_reasoning,
        "temperature": temperature,
        "pdf_file": display_name or Path(pdf_path).name,
        "pdf_path": str(pdf_path),
        "page_count": extracted.page_count,
        "input_characters": extracted.char_count,
        "approx_input_tokens": extracted.approx_tokens,
        "api_elapsed_seconds": round(elapsed, 2),
        "provider": settings.get("provider", ""),
        "reasoning_effort": effective_effort,
        "usage": usage,
        "contract_repair_usage": contract_repair_usage,
        "extract_seconds": extract_seconds,
        "total_seconds": round(time.perf_counter() - pipeline_started, 2),
        "garbled_pages": extracted.garbled_pages,
        "readable_pages": extracted.readable_pages,
        "parser_diagnostics": extracted.diagnostics,
        "warnings": extracted.warnings,
        "contract_repairs": repairs,
        "contract_repair_attempts": contract_repair_attempts,
        "evidence_retry": evidence_retry,
        "deterministic_derivations": deterministic_derivations,
        "reconciliation": reconciliation,
        "schema_rows": EXPECTED_ROW_COUNT,
        "metrics": metrics,
        "rows": rows,
    }

    # File the completed run under its strategy and fiscal year.
    run_dir = file_run(run_dir, strategy.key, fiscal_year, company_hint or display_name or Path(pdf_path).name)
    prediction["run_dir"] = str(run_dir.relative_to(RUNS_DIR))
    (run_dir / "prediction.json").write_text(
        json.dumps(prediction, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    progress(
        "output",
        f"Run {run_dir.name} complete",
        done=True,
        accuracy=metrics["accuracy"],
        coverage=metrics["coverage"],
        fiscal_year=fiscal_year,
    )
    return prediction


def _usage_pots(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        prediction.get("usage") or {},
        prediction.get("contract_repair_usage") or {},
        ((prediction.get("evidence_retry") or {}).get("usage")) or {},
    ]


def _total_prompt_tokens(prediction: dict[str, Any]) -> Optional[int]:
    values = [pot.get("prompt_tokens") for pot in _usage_pots(prediction)]
    present = [int(value) for value in values if value is not None]
    return sum(present) if present else None


def _total_completion_tokens(prediction: dict[str, Any]) -> Optional[int]:
    values = [pot.get("completion_tokens") for pot in _usage_pots(prediction)]
    present = [int(value) for value in values if value is not None]
    return sum(present) if present else None


def load_prediction(run_id: str) -> Optional[dict[str, Any]]:
    """Read a stored run by id. Returns None for unknown or unreadable runs."""
    run_dir = find_run_dir(run_id)
    if run_dir is None:
        return None
    pred_file = run_dir / "prediction.json"
    if not pred_file.is_file():
        return None
    try:
        return json.loads(pred_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def run_timestamp(run_id: str) -> str:
    """Sortable timestamp portion of a run id (``S1_20260819T221530Z_001``)."""
    match = re.search(r"(\d{8}T\d{6}Z(?:_\d+)?)", run_id or "")
    return match.group(1) if match else ""


# Computed run summaries keyed by prediction path; an entry is reused while
# the file's (mtime, size) is unchanged, so a feed request re-parses and
# re-scores only runs that actually changed since the previous request.
_SUMMARY_CACHE: dict[str, tuple[float, int, str, dict[str, Any]]] = {}


def _summarize_run_dir(directory: Path) -> tuple[str, dict[str, Any]] | None:
    """(workspace_id, summary) for one run directory, cached by file identity."""
    pred_file = directory / "prediction.json"
    try:
        stat = pred_file.stat()
    except OSError:
        return None
    cache_key = str(pred_file)
    cached = _SUMMARY_CACHE.get(cache_key)
    if cached and cached[0] == stat.st_mtime and cached[1] == stat.st_size:
        return cached[2], cached[3]
    try:
        prediction = json.loads(pred_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(prediction, dict):
        return None

    rows, _ = derive_identity_values(prediction.get("rows", []))
    rows = apply_confidence_gate(rows)
    # The screened corpus year is authoritative (run_pipeline files runs by
    # it); the model-detected year is only a fallback for ad-hoc uploads.
    fiscal_year = prediction.get("fiscal_year") or prediction.get("detected_fiscal_year", "")
    # Always recompute rather than trusting the stored block: the stored
    # metrics were calculated under whatever CONFIDENCE_THRESHOLD was in
    # force at the time, and a history scored under two different rules is
    # not comparable.
    company = prediction.get("company") or report_identity(
        prediction.get("pdf_file", ""), fiscal_year
    )[0]
    currency = str(prediction.get("currency") or "USD").strip().upper()
    metrics = compute_metrics(
        rows, fiscal_year, company, prediction.get("source_pdf_sha256"), currency
    )
    report = reconcile(
        rows, value_quantum=float(prediction.get("source_value_quantum") or 0.0)
    )
    metrics["consistency"] = report["consistency"]
    # Accept any registered strategy key. The old whitelist collapsed
    # s2-docling / s2-inspector into plain "s2", which made the parser used
    # by a run unrecoverable from its record.
    strategy = prediction.get("strategy")
    if strategy not in STRATEGIES:
        prefix = directory.name.split("_", 1)[0]
        strategy = next(
            (k for k, v in STRATEGIES.items() if v.run_prefix == prefix),
            "s2" if directory.name.startswith("S2") else "s1",
        )

    registered = STRATEGIES.get(strategy)
    if prediction.get("experiment"):
        experiment = prediction["experiment"]
        parser = prediction.get("parser") or (registered.parser if registered else strategy)
        ocr_enabled = bool(prediction.get("ocr_enabled"))
        ocr_policy = prediction.get("ocr_policy", "off")
    else:
        # The former Strategy 2 keys were all text-only.  Do not silently
        # relabel historical observations as OCR runs now that those keys
        # are used by the revised matched experiment.
        experiment = "legacy_no_ocr"
        parser = {
            "s1": "pypdf", "s2": "pymupdf",
            "s2-docling": "docling", "s2-inspector": "inspector",
        }.get(strategy, registered.parser if registered else strategy)
        ocr_enabled = False
        ocr_policy = "off"

    summary = {
        "run_id": prediction.get("run_id", directory.name),
        "timestamp": run_timestamp(directory.name),
        "strategy": strategy,
        "parser": parser,
        "experiment": experiment,
        "ocr_enabled": ocr_enabled,
        "ocr_policy": ocr_policy,
        "company": company,
        "currency": currency,
        "value_scale": prediction.get("value_scale", "millions"),
        "answer_unit": prediction.get("answer_unit") or f"M {currency}",
        "source_pdf_sha256": prediction.get("source_pdf_sha256"),
        "model": prediction.get("model", ""),
        "fiscal_year": fiscal_year,
        "detected_fiscal_year": prediction.get("detected_fiscal_year", ""),
        "enable_reasoning": prediction.get("enable_reasoning", True),
        "reasoning_effort": prediction.get("reasoning_effort", ""),
        "temperature": prediction.get("temperature"),
        "pdf_file": prediction.get("pdf_file", ""),
        "page_count": prediction.get("page_count"),
        "approx_input_tokens": prediction.get("approx_input_tokens"),
        # Total model input across every call the run made: main pass,
        # bounded contract repair, and Strategy 3's evidence retry. None
        # only when no call reported usage, so legacy runs still read as
        # "estimated" rather than a false zero.
        "input_tokens": _total_prompt_tokens(prediction),
        "output_tokens": _total_completion_tokens(prediction),
        "contract_repair_attempts": prediction.get("contract_repair_attempts", 0),
        "evidence_retry_attempted": bool((prediction.get("evidence_retry") or {}).get("attempted")),
        "evidence_retry_recovered": len((prediction.get("evidence_retry") or {}).get("recovered_rows") or []),
        "input_characters": prediction.get("input_characters"),
        "strategy_label": prediction.get("strategy_label", ""),
        "row_count": len(rows),
        "api_elapsed": prediction.get("api_elapsed_seconds", 0),
        "extract_seconds": prediction.get("extract_seconds"),
        "total_seconds": prediction.get("total_seconds"),
        "warnings": prediction.get("warnings", []),
        "contract_repairs": prediction.get("contract_repairs", []),
        "failed_identities": report["failed_identities"],
        **metrics,
    }
    workspace = str(prediction.get("workspace_id") or "legacy-public")
    _SUMMARY_CACHE[cache_key] = (stat.st_mtime, stat.st_size, workspace, summary)
    return workspace, summary


def invalidate_run_summaries(run_dir: Path | None = None) -> None:
    """Drop cached summaries for one deleted run directory, or all of them."""
    if run_dir is None:
        _SUMMARY_CACHE.clear()
        return
    prefix = str(run_dir)
    for key in [key for key in _SUMMARY_CACHE if key.startswith(prefix)]:
        _SUMMARY_CACHE.pop(key, None)


def list_runs(workspace_id: str | None = None) -> list[dict[str, Any]]:
    """Summarize every stored run, newest first."""
    summaries: list[dict[str, Any]] = []
    if not RUNS_DIR.exists():
        return summaries
    for directory in iter_run_dirs():
        try:
            entry = _summarize_run_dir(directory)
        except Exception:
            # One malformed historical artifact must not take down the whole
            # feed; the run is skipped and every valid run still returns.
            continue
        if entry is None:
            continue
        workspace, summary = entry
        if workspace_id is not None and workspace != workspace_id:
            continue
        # Shallow copy so a caller cannot mutate the cached record.
        summaries.append(dict(summary))
    summaries.sort(key=lambda r: (r["timestamp"], r["run_id"]), reverse=True)
    return summaries


__all__ = [
    "ASSET_SCHEMA",
    "BENCHMARK_WORKSPACE_ID",
    "CONFIDENCE_THRESHOLD",
    "RUNS_DIR",
    "UPLOAD_DIR",
    "apply_confidence_gate",
    "compute_metrics",
    "derive_identity_values",
    "create_run_dir",
    "ensure_dirs",
    "evidence_table",
    "invalidate_run_summaries",
    "list_runs",
    "load_prediction",
    "merge_retry_rows",
    "result_table",
    "run_pipeline",
    "safe_filename",
    "save_upload",
    "store_pdf",
]
