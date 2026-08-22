"""Run the locked five-company, nine-arm extraction bake-off.

Strategy 1 and Strategy 2 each exercise all four parsers. Strategy 3 uses its
finalized pdf-inspector + intelligent-scanning-gate pipeline. Existing runs are
reused only when they match the exact PDF hash, current model, strategy, and
experiment so an interrupted benchmark can resume without paying twice.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import compute_metrics, iter_run_dirs, load_prediction, run_pipeline
from prompts import SYSTEM_PROMPT
from reconcile import reconcile
from settings import current_settings


OUTPUT_JSON = ROOT / "research" / "benchmark" / "five_company_bakeoff_results.json"
OUTPUT_CSV = ROOT / "research" / "benchmark" / "five_company_bakeoff_results.csv"
OUTPUT_MD = ROOT / "research" / "benchmark" / "five_company_bakeoff_results.md"

COHORT = [
    ("AppBank株式会社", ROOT / "corpus_dataset/AppBank/2022/AppBank_annual_report_2022.pdf"),
    ("ダイニチ工業株式会社", ROOT / "corpus_dataset/ダイニチ工業株式会社/2022/ダイニチ工業株式会社_annual_report_2022.pdf"),
    ("ラクスル株式会社", ROOT / "corpus_dataset/ラクスル株式会社/2022/ラクスル株式会社_annual_report_2022.pdf"),
    ("株式会社プレイド", ROOT / "corpus_dataset/株式会社プレイド/2022/株式会社プレイド_annual_report_2022.pdf"),
    ("株式会社帝国ホテル", ROOT / "corpus_dataset/株式会社帝国ホテル/2022/株式会社帝国ホテル_annual_report_2022.pdf"),
]

ARMS = [
    ("Strategy 1", "s1"),
    ("Strategy 1", "s1-pymupdf"),
    ("Strategy 1", "s1-inspector"),
    ("Strategy 1", "s1-docling"),
    ("Strategy 2", "s2-pypdf"),
    ("Strategy 2", "s2"),
    ("Strategy 2", "s2-inspector"),
    ("Strategy 2", "s2-docling"),
    ("Strategy 3", "s3"),
]

EXPECTED_EXPERIMENT = {
    "Strategy 1": "no_ocr",
    "Strategy 2": "ocr",
    "Strategy 3": "intelligent_scan",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _current_metrics(prediction: dict[str, Any]) -> dict[str, Any]:
    metrics = compute_metrics(
        prediction.get("rows") or [],
        str(prediction.get("fiscal_year") or prediction.get("detected_fiscal_year") or "2022"),
        str(prediction.get("company") or ""),
        str(prediction.get("source_pdf_sha256") or ""),
        str(prediction.get("currency") or "JPY"),
    )
    report = reconcile(
        prediction.get("rows") or [],
        value_quantum=float(prediction.get("source_value_quantum") or 0.0),
    )
    metrics["consistency"] = report.get("consistency")
    return metrics


def _result(prediction: dict[str, Any], *, company: str, strategy_name: str, reused: bool) -> dict[str, Any]:
    metrics = _current_metrics(prediction)
    diagnostics = prediction.get("parser_diagnostics") or {}
    usage = prediction.get("usage") or {}
    return {
        "company": company,
        "fiscal_year": 2022,
        "currency": str(prediction.get("currency") or "JPY"),
        "strategy": strategy_name,
        "strategy_key": prediction.get("strategy"),
        "parser": prediction.get("parser"),
        "ocr_policy": prediction.get("ocr_policy") or "off",
        "status": "complete",
        "reused": reused,
        "run_id": prediction.get("run_id"),
        "exact_matches": metrics.get("exact_matches"),
        "total_compared": metrics.get("total_compared"),
        "accuracy_pct": metrics.get("accuracy"),
        "coverage_pct": metrics.get("coverage"),
        "confidence_coverage_pct": metrics.get("confidence_accepted_coverage"),
        "consistency_pct": metrics.get("consistency"),
        "parser_seconds": prediction.get("extract_seconds"),
        "model_seconds": prediction.get("api_elapsed_seconds"),
        "total_seconds": prediction.get("total_seconds"),
        "approx_input_tokens": prediction.get("approx_input_tokens"),
        "reported_prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "pages": prediction.get("page_count"),
        "readable_pages": prediction.get("readable_pages"),
        "selected_pages": diagnostics.get("selected_pages"),
        "ocr_page_count": diagnostics.get("ocr_page_count"),
        "warnings": prediction.get("warnings") or [],
        "error": None,
    }


def _existing(settings: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    hashes = {company: _sha256(path) for company, path in COHORT}
    candidates: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
    for run_dir in iter_run_dirs():
        prediction = load_prediction(run_dir.name)
        if not prediction:
            continue
        company = str(prediction.get("company") or "")
        strategy_key = str(prediction.get("strategy") or "")
        strategy_name = next((name for name, key in ARMS if key == strategy_key), "")
        if not strategy_name or company not in hashes:
            continue
        if prediction.get("source_pdf_sha256") != hashes[company]:
            continue
        if prediction.get("model") != settings["model"]:
            continue
        if prediction.get("experiment") != EXPECTED_EXPERIMENT[strategy_name]:
            continue
        if float(prediction.get("temperature") or 0.0) != 0.0:
            continue
        key = (company, strategy_key)
        modified = (run_dir / "prediction.json").stat().st_mtime
        if key not in candidates or modified > candidates[key][0]:
            candidates[key] = (modified, prediction)
    return {key: prediction for key, (_, prediction) in candidates.items()}


def _write_results(rows: list[dict[str, Any]], settings: dict[str, Any]) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            [company for company, _ in COHORT].index(row["company"]),
            [key for _, key in ARMS].index(row["strategy_key"]),
        ),
    )
    OUTPUT_JSON.write_text(
        json.dumps({"model": settings["model"], "temperature": 0.0, "rows": ordered}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    fields = [
        "company", "fiscal_year", "currency", "strategy", "strategy_key", "parser", "ocr_policy",
        "status", "reused", "run_id", "exact_matches", "total_compared", "accuracy_pct", "coverage_pct",
        "confidence_coverage_pct", "consistency_pct", "parser_seconds", "model_seconds", "total_seconds",
        "approx_input_tokens", "reported_prompt_tokens", "completion_tokens", "pages", "readable_pages",
        "selected_pages", "ocr_page_count", "warnings", "error",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in ordered:
            writer.writerow({**row, "selected_pages": json.dumps(row["selected_pages"], ensure_ascii=False), "warnings": json.dumps(row["warnings"], ensure_ascii=False)})

    complete = [row for row in ordered if row["status"] == "complete"]
    lines = [
        "# Five-company, three-strategy parser bake-off",
        "",
        f"Model: `{settings['model']}` · temperature 0.0 · unit M JPY · {len(complete)}/{len(ARMS) * len(COHORT)} arms complete.",
        "Gold is used only after inference for evaluation and is never included in model requests.",
        "",
        "| Company | Strategy | Parser | OCR | Exact | Coverage | Parser s | Model s | Total s | Approx tokens | Run |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in ordered:
        exact = f"{row['exact_matches']}/{row['total_compared']} ({row['accuracy_pct']}%)" if row["status"] == "complete" else "failed"
        lines.append(
            f"| {row['company']} | {row['strategy']} | {row['parser'] or row['strategy_key']} | {row['ocr_policy']} | "
            f"{exact} | {row['coverage_pct'] if row['coverage_pct'] is not None else '—'} | "
            f"{row['parser_seconds'] if row['parser_seconds'] is not None else '—'} | "
            f"{row['model_seconds'] if row['model_seconds'] is not None else '—'} | "
            f"{row['total_seconds'] if row['total_seconds'] is not None else '—'} | "
            f"{row['approx_input_tokens'] if row['approx_input_tokens'] is not None else '—'} | "
            f"`{row['run_id'] or '—'}` |"
        )
    lines.extend(["", "## Aggregate timing", "", "| Strategy | Parser | Completed | Mean parser s | Mean model s | Mean total s | Mean accuracy |", "|---|---|---:|---:|---:|---:|---:|"])
    for strategy_name, strategy_key in ARMS:
        group = [row for row in complete if row["strategy_key"] == strategy_key]
        mean = lambda field: round(statistics.fmean(float(row[field]) for row in group if row[field] is not None), 2) if group else None
        lines.append(
            f"| {strategy_name} | {group[0]['parser'] if group else strategy_key} | {len(group)}/5 | "
            f"{mean('parser_seconds') if group else '—'} | {mean('model_seconds') if group else '—'} | "
            f"{mean('total_seconds') if group else '—'} | {mean('accuracy_pct') if group else '—'}% |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    settings = current_settings()
    if not settings.get("api_key"):
        raise SystemExit("No configured LLM API key.")
    missing = [str(path) for _, path in COHORT if not path.is_file()]
    if missing:
        raise SystemExit("Missing benchmark PDFs: " + ", ".join(missing))

    existing = {} if args.force else _existing(settings)
    rows: list[dict[str, Any]] = []
    lock = threading.Lock()
    tasks: list[tuple[str, Path, str, str]] = []
    for company, path in COHORT:
        for strategy_name, strategy_key in ARMS:
            prediction = existing.get((company, strategy_key))
            if prediction:
                rows.append(_result(prediction, company=company, strategy_name=strategy_name, reused=True))
            else:
                tasks.append((company, path, strategy_name, strategy_key))

    print(f"Reusing {len(rows)} matching runs; executing {len(tasks)} missing arms.", flush=True)
    _write_results(rows, settings)

    def execute(task: tuple[str, Path, str, str]) -> dict[str, Any]:
        company, path, strategy_name, strategy_key = task
        started = time.perf_counter()
        try:
            prediction = run_pipeline(
                pdf_path=path,
                settings=settings,
                strategy_key=strategy_key,
                system_prompt=SYSTEM_PROMPT,
                fiscal_year_hint="2022",
                company_hint=company,
                output_currency="JPY",
                display_name=path.name,
                workspace_id="five-company-bakeoff",
                enable_reasoning=bool(settings.get("enable_reasoning", True)),
                reasoning_effort=str(settings.get("reasoning_effort") or "medium"),
                temperature=0.0,
            )
            return _result(prediction, company=company, strategy_name=strategy_name, reused=False)
        except Exception as exc:  # benchmark must retain failures as observations
            return {
                "company": company, "fiscal_year": 2022, "currency": "JPY", "strategy": strategy_name,
                "strategy_key": strategy_key, "parser": None, "ocr_policy": None, "status": "failed",
                "reused": False, "run_id": None, "exact_matches": None, "total_compared": None,
                "accuracy_pct": None, "coverage_pct": None, "confidence_coverage_pct": None,
                "consistency_pct": None, "parser_seconds": None, "model_seconds": None,
                "total_seconds": round(time.perf_counter() - started, 2), "approx_input_tokens": None,
                "reported_prompt_tokens": None, "completion_tokens": None, "pages": None,
                "readable_pages": None, "selected_pages": None, "ocr_page_count": None,
                "warnings": [], "error": f"{type(exc).__name__}: {exc}",
            }

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 5))) as executor:
        future_map = {executor.submit(execute, task): task for task in tasks}
        for completed, future in enumerate(as_completed(future_map), start=1):
            row = future.result()
            with lock:
                rows.append(row)
                _write_results(rows, settings)
            print(
                f"[{completed}/{len(tasks)}] {row['company']} {row['strategy_key']} {row['status']} "
                f"total={row['total_seconds']}s accuracy={row['accuracy_pct']}",
                flush=True,
            )

    failures = [row for row in rows if row["status"] != "complete"]
    print(f"Wrote {OUTPUT_MD.relative_to(ROOT)} with {len(rows) - len(failures)}/45 complete arms.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
