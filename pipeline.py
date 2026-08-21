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
from reconcile import reconcile, reconciliation_summary
from prompts import build_user_prompt
from schema import ASSET_SCHEMA, GOLDEN_ANSWERS_STORE

UPLOAD_DIR = Path("uploads")
RUNS_DIR = Path("runs")

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
    stem = Path(safe_filename(name)).stem
    # Uploaded files and corpus files may already carry our unique timestamp.
    stem = re.sub(r"^\d{8}T\d{6}Z_\d{3}_", "", stem)
    match = re.search(r"(19|20)\d{2}", str(fiscal_year or "")) or re.search(r"(19|20)\d{2}", stem)
    year = match.group() if match else "unknown"
    company = re.sub(r"(?i)annual[_\s-]*report|form[_\s-]*10[_\s-]*k", "_", stem)
    company = re.sub(r"(19|20)\d{2}", "_", company)
    company = re.sub(r"(?i)updated|final|online|pdfa|web", "_", company)
    company = re.sub(r"[^A-Za-z0-9]+", "_", company).strip("_") or "Unknown_Company"
    return company, year, f"{company}_annual_report_{year}.pdf"


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
    if target.exists():
        shutil.rmtree(target)
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


def compute_metrics(
    rows: list[dict] | None,
    fiscal_year: Any,
    company: str | None = None,
    source_pdf_sha256: str | None = None,
) -> dict[str, Any]:
    """
    Score a prediction against the golden answers for its fiscal year.

    Three different questions, three numbers:

    - ``coverage``  - of the fixed schema, how many rows did the model commit to
      (a value it was at least CONFIDENCE_THRESHOLD confident about)?
    - ``accuracy``  - of the rows the answer key defines, how many are exactly
      right? An unconfident row counts as a miss, so this is "right and sure".
    - ``precision`` - of the rows the model *did* commit to, how many are right?
      This answers "can I trust a confident answer?", and it is what separates a
      cautious model from an unreliable one.

    A fiscal year with no golden set scores no accuracy at all rather than being
    silently compared against another year.
    """
    year = re.search(r"(19|20)\d{2}", str(fiscal_year or ""))
    normalized_company = re.sub(r"[^a-z0-9]+", "", str(company or "").lower())
    golden: dict[str, float] = {}
    gold_status = "human_review_required"
    gold_company = None
    # FY2022 is the only answer key supplied by the assignment. It remains
    # authoritative for 3M even when the run came from a direct upload.
    if year and year.group() == "2022" and normalized_company == "3m":
        golden = GOLDEN_ANSWERS_STORE["2022"]
        gold_status = "assignment_supplied"
        gold_company = "3M"
    elif source_pdf_sha256:
        # All other answer keys must be human-approved and bound to the exact
        # bytes that were run. A same-year PDF replacement cannot inherit gold.
        try:
            from corpus.manifest import find_document, verification_payload

            document = find_document(source_pdf_sha256)
            verification = verification_payload(document) if document else None
        except (OSError, ValueError, KeyError):
            verification = None
        if verification and verification.get("status") == "human_verified":
            golden = {
                str(item.get("item")): float(item["answer_m_usd"])
                for item in verification.get("rows", [])
                if item.get("answer_m_usd") is not None
            }
            gold_status = "human_verified"
            gold_company = str(company or document.get("company") or "")

    exact = 0
    compared = 0
    filled = 0
    committed = 0  # answered confidently AND covered by the answer key

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
        if accepted:
            filled += 1

        expected = golden.get(row.get("item"))
        if expected is None:
            continue
        compared += 1
        if not accepted:
            continue
        committed += 1
        try:
            if abs(float(value) - float(expected)) < 0.5:
                exact += 1
        except (TypeError, ValueError):
            continue

    return {
        "accuracy": round(exact / compared * 100, 1) if compared else None,
        "coverage": round(filled / EXPECTED_ROW_COUNT * 100, 1),
        "precision": round(exact / committed * 100, 1) if committed else None,
        "exact_matches": exact,
        "total_compared": compared,
        "filled_fields": filled,
        "committed_and_compared": committed,
        "has_golden": bool(golden),
        "gold_company": gold_company if golden else None,
        "gold_status": gold_status if golden else "human_review_required",
    }


def result_table(rows: list[dict]) -> list[dict]:
    return [
        {
            "Classification": r["classification"],
            "Subclassification": r["subclassification"],
            "Item": r["item"],
            "Description": r["description"],
            # A rejected value remains available on the raw row for audit, but
            # generic result/export consumers must follow the confidence gate.
            "Answer (M USD)": r["answer_m_usd"] if r.get("accepted", True) else None,
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
    temperature: float = 0.1,
    reasoning_effort: str = "",
    display_name: Optional[str] = None,
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
            display_name=display_name, on_progress=on_progress,
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
    on_progress,
) -> dict[str, Any]:
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
    progress(
        "extract",
        f"{extracted.page_count} pages · {extracted.char_count:,} characters · {extract_seconds:.1f}s",
        done=True,
        page_count=extracted.page_count,
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
    # Apply the confidence gate once, here, so scoring and reconciliation below
    # agree on what counts as an answer.
    rows = apply_confidence_gate(rows_as_dicts(result))
    progress("validate", f"{len(rows)} rows conform to the contract")

    # Deterministic arithmetic check, separate from the type contract above and
    # from scoring below. Needs no answer key, so it is the only quality signal
    # that survives the move to companies we have no golden data for.
    reconciliation = reconcile(rows)
    progress("validate", reconciliation_summary(reconciliation), done=True)

    fiscal_year = result.detected_fiscal_year or (fiscal_year_hint or "").strip()
    company, _, _ = report_identity(display_name or Path(pdf_path).name, fiscal_year)
    source_pdf_sha256 = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    metrics = compute_metrics(rows, fiscal_year, company, source_pdf_sha256)
    metrics["consistency"] = reconciliation["consistency"]

    progress("output", "Saving extraction result")
    prediction: dict[str, Any] = {
        "run_id": run_dir.name,
        "strategy": strategy.key,
        "strategy_label": strategy.label,
        "parser": strategy.parser,
        "experiment": strategy.experiment,
        "experiment_schema_version": 2,
        "ocr_enabled": strategy.ocr_enabled,
        "ocr_policy": ocr_policy if strategy.ocr_enabled else "off",
        "company": company,
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
        "total_seconds": round(extract_seconds + elapsed, 2),
        "garbled_pages": extracted.garbled_pages,
        "readable_pages": extracted.readable_pages,
        "parser_diagnostics": extracted.diagnostics,
        "warnings": extracted.warnings,
        "contract_repairs": repairs,
        "contract_repair_attempts": contract_repair_attempts,
        "reconciliation": reconciliation,
        "schema_rows": EXPECTED_ROW_COUNT,
        "metrics": metrics,
        "rows": rows,
    }

    # File the completed run under its strategy and fiscal year.
    run_dir = file_run(run_dir, strategy.key, fiscal_year, display_name or Path(pdf_path).name)
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


def list_runs() -> list[dict[str, Any]]:
    """Summarize every stored run, newest first."""
    summaries: list[dict[str, Any]] = []
    if not RUNS_DIR.exists():
        return summaries

    for directory in iter_run_dirs():
        prediction = load_prediction(directory.name)
        if prediction is None:
            continue

        rows = apply_confidence_gate(prediction.get("rows", []))
        fiscal_year = prediction.get("detected_fiscal_year") or prediction.get("fiscal_year", "")
        # Always recompute rather than trusting the stored block: the stored
        # metrics were calculated under whatever CONFIDENCE_THRESHOLD was in
        # force at the time, and a history scored under two different rules is
        # not comparable.
        company = prediction.get("company") or report_identity(
            prediction.get("pdf_file", ""), fiscal_year
        )[0]
        metrics = compute_metrics(rows, fiscal_year, company, prediction.get("source_pdf_sha256"))
        report = prediction.get("reconciliation") or reconcile(rows)
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

        summaries.append({
            "run_id": prediction.get("run_id", directory.name),
            "timestamp": run_timestamp(directory.name),
            "strategy": strategy,
            "parser": parser,
            "experiment": experiment,
            "ocr_enabled": ocr_enabled,
            "ocr_policy": ocr_policy,
            "company": company,
            "model": prediction.get("model", ""),
            "fiscal_year": fiscal_year,
            "detected_fiscal_year": prediction.get("detected_fiscal_year", ""),
            "enable_reasoning": prediction.get("enable_reasoning", True),
            "temperature": prediction.get("temperature"),
            "pdf_file": prediction.get("pdf_file", ""),
            "page_count": prediction.get("page_count"),
            "approx_input_tokens": prediction.get("approx_input_tokens"),
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
        })

    summaries.sort(key=lambda r: (r["timestamp"], r["run_id"]), reverse=True)
    return summaries


__all__ = [
    "ASSET_SCHEMA",
    "CONFIDENCE_THRESHOLD",
    "RUNS_DIR",
    "UPLOAD_DIR",
    "apply_confidence_gate",
    "compute_metrics",
    "create_run_dir",
    "ensure_dirs",
    "evidence_table",
    "list_runs",
    "load_prediction",
    "result_table",
    "run_pipeline",
    "safe_filename",
    "save_upload",
    "store_pdf",
]
