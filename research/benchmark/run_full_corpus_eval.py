"""End-to-end three-strategy evaluation over every gold-backed corpus PDF.

One arm per strategy: Strategy 1 (no-OCR PyPDF control), Strategy 2 (adaptive
pdf-inspector OCR), Strategy 3 (intelligent scanning gate). Gold is consulted
only after inference for scoring; prompts never see it. Existing runs are
reused when they match the exact PDF hash, model, strategy, experiment, and
temperature 0.0 so interrupted sweeps resume without re-spending.
"""

from __future__ import annotations

import argparse
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
from schema import ASSIGNMENT_GOLDEN_SOURCE_SHA256, SOURCE_BOUND_GOLDEN_ANSWERS
from settings import current_settings

OUTPUT_JSON = ROOT / "research" / "benchmark" / "full_corpus_eval_results.json"
OUTPUT_MD = ROOT / "research" / "benchmark" / "full_corpus_eval_results.md"

ARMS = [
    ("Strategy 1", "s1"),
    ("Strategy 2", "s2-inspector"),
    ("Strategy 3", "s3"),
]
EXPECTED_EXPERIMENT = {
    "Strategy 1": "no_ocr",
    "Strategy 2": "ocr",
    "Strategy 3": "intelligent_scan",
}


def _gold_backed_documents(one_per_company: bool = False) -> list[dict[str, Any]]:
    manifest = json.loads(
        (ROOT / "corpus_dataset" / "corpus_manifest.json").read_text(encoding="utf-8")
    )
    documents = []
    for document in manifest.get("documents", []):
        sha = str(document.get("sha256") or "")
        has_gold = sha == ASSIGNMENT_GOLDEN_SOURCE_SHA256 or sha in SOURCE_BOUND_GOLDEN_ANSWERS
        if not has_gold:
            continue
        path = ROOT / str(document.get("local_path"))
        if not path.is_file():
            print(f"SKIP missing file: {path}")
            continue
        fixture = SOURCE_BOUND_GOLDEN_ANSWERS.get(sha) or {}
        scorable = (
            27 if sha == ASSIGNMENT_GOLDEN_SOURCE_SHA256
            else len(fixture.get("answers") or {})
        )
        documents.append({
            "company": str(document.get("company")),
            "fiscal_year": str(document.get("fiscal_year")),
            "currency": str(document.get("currency") or "JPY"),
            "sha256": sha,
            "path": path,
            "scorable_rows": scorable,
        })
    if one_per_company:
        # One document per company: richest gold first, then the human-audited
        # FY2022 vintage, then the newest year.
        best: dict[str, dict[str, Any]] = {}
        for document in documents:
            key = document["company"]
            rank = (
                document["scorable_rows"],
                document["fiscal_year"] == "2022",
                document["fiscal_year"],
            )
            if key not in best or rank > best[key]["_rank"]:
                best[key] = {**document, "_rank": rank}
        documents = [
            {k: v for k, v in entry.items() if k != "_rank"}
            for entry in best.values()
        ]
    return documents


def _score(prediction: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    metrics = compute_metrics(
        prediction.get("rows") or [],
        document["fiscal_year"],
        document["company"],
        document["sha256"],
        document["currency"],
    )
    report = reconcile(
        prediction.get("rows") or [],
        value_quantum=float(prediction.get("source_value_quantum") or 0.0),
    )
    usage = prediction.get("usage") or {}
    retry = prediction.get("evidence_retry") or {}
    return {
        "company": document["company"],
        "fiscal_year": document["fiscal_year"],
        "currency": document["currency"],
        "sha256": document["sha256"],
        "strategy_key": prediction.get("strategy"),
        "status": "complete",
        "run_id": prediction.get("run_id"),
        "exact_matches": metrics.get("exact_matches"),
        "total_compared": metrics.get("total_compared"),
        "accuracy_pct": metrics.get("accuracy"),
        "coverage_pct": metrics.get("coverage"),
        "consistency_pct": report.get("consistency"),
        "gold_status": metrics.get("gold_status"),
        "parser_seconds": prediction.get("extract_seconds"),
        "model_seconds": prediction.get("api_elapsed_seconds"),
        "total_seconds": prediction.get("total_seconds"),
        "approx_input_tokens": prediction.get("approx_input_tokens"),
        "reported_prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "pages": prediction.get("page_count"),
        "evidence_retry_attempted": bool(retry.get("attempted")),
        "evidence_retry_recovered": len(retry.get("recovered_rows") or []),
        "error": None,
    }


def _existing(settings: dict[str, Any], documents: list[dict[str, Any]]):
    by_sha = {document["sha256"]: document for document in documents}
    found: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
    for run_dir in iter_run_dirs():
        prediction = load_prediction(run_dir.name)
        if not prediction:
            continue
        sha = str(prediction.get("source_pdf_sha256") or "")
        strategy_key = str(prediction.get("strategy") or "")
        if sha not in by_sha or strategy_key not in {key for _, key in ARMS}:
            continue
        strategy_name = next(name for name, key in ARMS if key == strategy_key)
        if prediction.get("model") != settings["model"]:
            continue
        if prediction.get("experiment") != EXPECTED_EXPERIMENT[strategy_name]:
            continue
        if float(prediction.get("temperature") or 0.0) != 0.0:
            continue
        if str(prediction.get("currency") or "") != by_sha[sha]["currency"]:
            continue
        if str(prediction.get("reasoning_effort") or "") != str(
            settings.get("reasoning_effort") or "medium"
        ):
            continue
        key = (sha, strategy_key)
        modified = (run_dir / "prediction.json").stat().st_mtime
        if key not in found or modified > found[key][0]:
            found[key] = (modified, prediction)
    return {key: prediction for key, (_, prediction) in found.items()}


def _percentile(values: list[float], fraction: float) -> float | None:
    ordered = sorted(value for value in values if value is not None)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * fraction
    lower, upper = int(rank), min(int(rank) + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower), 2)


def _write(rows: list[dict[str, Any]], settings: dict[str, Any], total: int) -> None:
    ordered = sorted(rows, key=lambda row: (row["company"], row["fiscal_year"], row["strategy_key"]))
    OUTPUT_JSON.write_text(
        json.dumps({"model": settings["model"], "temperature": 0.0, "rows": ordered}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    complete = [row for row in ordered if row["status"] == "complete"]
    lines = [
        "# Full-corpus three-strategy end-to-end evaluation",
        "",
        f"Model: `{settings['model']}` · temperature 0.0 · {len(complete)}/{total} arms complete.",
        "Gold is consulted only after inference for scoring; prompts never contain gold values.",
        "",
        "## Aggregates per strategy",
        "",
        "| Strategy | Complete | Scored | Mean exact accuracy | Mean coverage | P50 total s | Mean model-reported input tokens | Retries |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy_name, strategy_key in ARMS:
        group = [row for row in complete if row["strategy_key"] == strategy_key]
        scored = [row for row in group if row["accuracy_pct"] is not None]
        seconds = [float(row["total_seconds"]) for row in group if row["total_seconds"] is not None]
        tokens = [float(row["reported_prompt_tokens"]) for row in group if row["reported_prompt_tokens"] is not None]
        mean = lambda values: round(statistics.fmean(values), 2) if values else None
        lines.append(
            f"| {strategy_name} (`{strategy_key}`) | {len(group)} | {len(scored)} | "
            f"{mean([float(row['accuracy_pct']) for row in scored])} | "
            f"{mean([float(row['coverage_pct']) for row in group if row['coverage_pct'] is not None])} | "
            f"{_percentile(seconds, 0.5)} | "
            f"{mean(tokens)} | {sum(1 for row in group if row['evidence_retry_attempted'])} |"
        )
    lines.extend(["", "## Per-report results", "",
                  "| Company | FY | Strategy | Exact | Coverage | Consistency | Total s | Prompt tokens | Retry | Run |",
                  "|---|---|---|---:|---:|---:|---:|---:|---|---|"])
    for row in ordered:
        exact = (
            f"{row['exact_matches']}/{row['total_compared']} ({row['accuracy_pct']}%)"
            if row["status"] == "complete" and row["accuracy_pct"] is not None
            else ("unscored" if row["status"] == "complete" else "failed")
        )
        retry = (
            f"+{row['evidence_retry_recovered']}" if row.get("evidence_retry_attempted") else "—"
        ) if row["status"] == "complete" else "—"
        lines.append(
            f"| {row['company']} | {row['fiscal_year']} | {row['strategy_key']} | {exact} | "
            f"{row['coverage_pct'] if row['status'] == 'complete' else '—'} | "
            f"{row['consistency_pct'] if row['status'] == 'complete' else '—'} | "
            f"{row['total_seconds'] if row['total_seconds'] is not None else '—'} | "
            f"{row['reported_prompt_tokens'] if row.get('reported_prompt_tokens') is not None else '—'} | "
            f"{retry} | `{row['run_id'] or (row.get('error') or '')[:60]}` |"
        )
    failures = [row for row in ordered if row["status"] != "complete"]
    if failures:
        lines.extend(["", "## Failures", ""])
        for row in failures:
            lines.append(f"- {row['company']} FY{row['fiscal_year']} `{row['strategy_key']}`: {row.get('error')}")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="cap the number of live arms this invocation runs")
    parser.add_argument("--one-per-company", action="store_true", help="evaluate one document per company (richest gold, preferring the audited FY2022 vintage)")
    parser.add_argument("--provider", default="", help="override the configured provider key (e.g. openrouter)")
    parser.add_argument("--model", default="", help="override the configured model id (e.g. google/gemini-3.7-flash:nitro)")
    parser.add_argument("--base-url", default="", help="override the provider base URL")
    parser.add_argument("--api-key-env", default="", help="read the API key from this environment variable instead of saved settings")
    parser.add_argument("--reasoning-effort", default="", help="override the reasoning effort (e.g. low)")
    parser.add_argument("--output-suffix", default="", help="write results to full_corpus_eval_results<suffix>.{json,md}")
    parser.add_argument("--arms", default="", help="comma-separated strategy keys to run (default: all three)")
    args = parser.parse_args()
    settings = dict(current_settings())
    if args.provider:
        settings["provider"] = args.provider
    if args.model:
        settings["model"] = args.model
    if args.base_url:
        settings["base_url"] = args.base_url
    if args.api_key_env:
        import os

        key = os.environ.get(args.api_key_env, "").strip()
        if not key:
            raise SystemExit(f"Environment variable {args.api_key_env} is empty.")
        settings["api_key"] = key
    if args.reasoning_effort:
        settings["reasoning_effort"] = args.reasoning_effort
        settings["enable_reasoning"] = args.reasoning_effort != "none"
    if args.output_suffix:
        global OUTPUT_JSON, OUTPUT_MD
        OUTPUT_JSON = OUTPUT_JSON.with_name(f"full_corpus_eval_results{args.output_suffix}.json")
        OUTPUT_MD = OUTPUT_MD.with_name(f"full_corpus_eval_results{args.output_suffix}.md")
    if not settings.get("api_key"):
        raise SystemExit("No configured LLM API key.")

    global ARMS
    if args.arms:
        wanted = {key.strip() for key in args.arms.split(",") if key.strip()}
        ARMS = [(name, key) for name, key in ARMS if key in wanted]
        if not ARMS:
            raise SystemExit(f"--arms matched no strategy keys: {args.arms}")
    documents = _gold_backed_documents(one_per_company=args.one_per_company)
    total = len(documents) * len(ARMS)
    print(f"{len(documents)} gold-backed corpus documents · {total} arms")
    existing = {} if args.force else _existing(settings, documents)

    rows: list[dict[str, Any]] = []
    tasks: list[tuple[dict[str, Any], str, str]] = []
    for document in documents:
        for strategy_name, strategy_key in ARMS:
            prediction = existing.get((document["sha256"], strategy_key))
            if prediction:
                rows.append(_score(prediction, document))
            else:
                tasks.append((document, strategy_name, strategy_key))
    if args.limit:
        tasks = tasks[: args.limit]
    print(f"Reusing {len(rows)} matching runs; executing {len(tasks)} live arms.", flush=True)
    _write(rows, settings, total)

    lock = threading.Lock()

    def execute(task):
        document, strategy_name, strategy_key = task
        started = time.perf_counter()
        try:
            prediction = run_pipeline(
                pdf_path=document["path"],
                settings=settings,
                strategy_key=strategy_key,
                system_prompt=SYSTEM_PROMPT,
                fiscal_year_hint=document["fiscal_year"],
                company_hint=document["company"],
                output_currency=document["currency"],
                display_name=document["path"].name,
                workspace_id="full-corpus-eval",
                enable_reasoning=bool(settings.get("enable_reasoning", True)),
                reasoning_effort=str(settings.get("reasoning_effort") or "medium"),
                temperature=0.0,
            )
            return _score(prediction, document)
        except Exception as exc:  # keep failures as observations
            return {
                "company": document["company"], "fiscal_year": document["fiscal_year"],
                "currency": document["currency"], "sha256": document["sha256"],
                "strategy_key": strategy_key, "status": "failed", "run_id": None,
                "exact_matches": None, "total_compared": None, "accuracy_pct": None,
                "coverage_pct": None, "consistency_pct": None, "gold_status": None,
                "parser_seconds": None, "model_seconds": None,
                "total_seconds": round(time.perf_counter() - started, 2),
                "approx_input_tokens": None, "reported_prompt_tokens": None,
                "completion_tokens": None, "pages": None,
                "evidence_retry_attempted": False, "evidence_retry_recovered": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 5))) as executor:
        futures = {executor.submit(execute, task): task for task in tasks}
        for done, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            with lock:
                rows.append(row)
                _write(rows, settings, total)
            print(
                f"[{done}/{len(tasks)}] {row['company']} FY{row['fiscal_year']} {row['strategy_key']} "
                f"{row['status']} acc={row['accuracy_pct']} retry={row['evidence_retry_attempted']}",
                flush=True,
            )

    failures = [row for row in rows if row["status"] != "complete"]
    print(f"Wrote {OUTPUT_MD.relative_to(ROOT)}: {len(rows) - len(failures)} complete, {len(failures)} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
