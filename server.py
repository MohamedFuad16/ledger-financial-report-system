import csv
import json
import os
import queue
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, stream_with_context

from api_client import GLMError, QuotaExhaustedError, test_api_key
from corpus.client import FirecrawlClient, FirecrawlError
from corpus.fetch import pin_candidate_answers
from corpus.manifest import (
    CORPUS_ROOT,
    approve_document_answers,
    delete_pinned_document,
    find_document,
    load_manifest,
    migrate_corpus_layout,
    verification_payload,
)
from corpus.service import build_corpus
from extraction import STRATEGIES, estimate_pdf_load
from models import CANONICAL_ITEMS, SchemaValidationError
from ratelimit import LIMITER, estimate_batch_plan
from pipeline import (
    RUNS_DIR,
    apply_confidence_gate,
    compute_metrics,
    find_run_dir,
    iter_run_dirs,
    ensure_dirs,
    evidence_table,
    list_runs,
    load_prediction,
    result_table,
    report_identity,
    run_pipeline,
    safe_filename,
    save_upload,
)
from reconcile import reconcile
from providers import PROVIDERS, REASONING_EFFORTS, get_provider
from prompts import SYSTEM_PROMPT
from schema import BENCHMARK_SCHEMA_METADATA, GOLDEN_ANSWERS_STORE
from settings import current_settings, load_local_env, save_runtime_settings, save_verified_settings
from traffic import record_visit

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024  # a batch of annual reports
# This is a local development tool whose HTML/JS/CSS change constantly. Browser
# caching here only ever serves a stale asset — which renders as a blank page
# when the cached script and the current markup disagree.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

ACTIVE_PROMPT = SYSTEM_PROMPT

# PDFs staged by /api/uploads, waiting to be run. Keyed by a short id so the
# browser uploads each file once, not again for the actual run.
STAGED: dict[str, dict] = {}
STAGED_LOCK = threading.Lock()
CORPUS_JOBS: dict[str, dict] = {}
CORPUS_JOBS_LOCK = threading.RLock()
CORPUS_JOBS_ROOT = RUNS_DIR / "_corpus_jobs"
CORPUS_WORKER_INSTANCE_ID = uuid.uuid4().hex
EXTRACTION_JOBS_ROOT = RUNS_DIR / "_extraction_jobs"
EXTRACTION_JOBS_LOCK = threading.RLock()
WORKSPACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

ensure_dirs()
CORPUS_JOBS_ROOT.mkdir(parents=True, exist_ok=True)
EXTRACTION_JOBS_ROOT.mkdir(parents=True, exist_ok=True)
load_local_env()
migrate_corpus_layout()
LIMITER.resize(current_settings().get("max_concurrency", 6))


def _allowed_origin(origin: str) -> str | None:
    """Return an approved browser origin for the separately hosted React UI."""
    configured = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if not origin or not configured:
        return None
    allowed = {item.strip().rstrip("/") for item in configured.split(",") if item.strip()}
    return origin if "*" in allowed or origin.rstrip("/") in allowed else None


# --- Utility Functions ---

def mask_key(key: str) -> str:
    if not key:
        return "Not configured"
    if len(key) <= 8:
        return "•" * 8
    return f"{key[:4]}…{key[-4:]}"


def parse_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def parse_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def request_workspace_id() -> str:
    """Return the anonymous browser workspace that owns private run state."""
    candidate = str(request.headers.get("X-Ledger-Workspace") or "legacy-public").strip()
    return candidate if WORKSPACE_ID_PATTERN.fullmatch(candidate) else "legacy-public"


def _workspace_matches(record: dict | None, workspace_id: str) -> bool:
    return bool(record) and str(record.get("workspace_id") or "legacy-public") == workspace_id


def _workspace_prediction_count(directory: Path, workspace_id: str) -> int:
    """Count only readable run artifacts owned by one anonymous workspace."""
    if not directory.is_dir():
        return 0
    count = 0
    for prediction_path in directory.rglob("prediction.json"):
        try:
            payload = json.loads(prediction_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and _workspace_matches(payload, workspace_id):
            count += 1
    return count


def request_run_options(settings: dict) -> dict:
    """Read the per-run knobs from a multipart form, falling back to saved settings."""
    return {
        "strategy_key": (request.form.get("strategy") or "s1").strip().lower(),
        "system_prompt": (request.form.get("system_prompt") or "").strip() or ACTIVE_PROMPT,
        "fiscal_year_hint": (request.form.get("fiscal_year") or "").strip(),
        "enable_reasoning": parse_bool(
            request.form.get("enable_reasoning"), settings.get("enable_reasoning", True)
        ),
        "reasoning_effort": (request.form.get("reasoning_effort") or "").strip().lower(),
        "temperature": parse_float(
            request.form.get("temperature"), settings.get("temperature", 0.0)
        ),
    }


def prediction_response(prediction: dict) -> dict:
    """
    Augment a stored prediction with everything derived from its rows.

    Metrics and reconciliation are recomputed rather than read from the stored
    block: both depend on CONFIDENCE_THRESHOLD, and a history scored under two
    different rules is not comparable.
    """
    rows = apply_confidence_gate(prediction.get("rows", []))
    fiscal_year = prediction.get("detected_fiscal_year") or prediction.get("fiscal_year", "")
    metrics = compute_metrics(rows, fiscal_year, prediction.get("company"), prediction.get("source_pdf_sha256"))
    report = reconcile(rows)
    metrics["consistency"] = report["consistency"]
    return {
        **prediction,
        "ok": True,
        "rows": rows,
        "metrics": metrics,
        "reconciliation": report,
        "result_table": result_table(rows),
        "evidence_table": evidence_table(rows),
    }


def _extraction_job_dir(job_id: str) -> Path:
    if not job_id or any(char not in "0123456789abcdef" for char in job_id.lower()):
        raise ValueError("Invalid extraction job id.")
    path = (EXTRACTION_JOBS_ROOT / job_id).resolve()
    if path.parent != EXTRACTION_JOBS_ROOT.resolve():
        raise ValueError("Invalid extraction job id.")
    return path


def _corpus_job_dir(job_id: str) -> Path:
    if not job_id or any(char not in "0123456789abcdef" for char in job_id.lower()):
        raise ValueError("Invalid corpus job id.")
    path = (CORPUS_JOBS_ROOT / job_id).resolve()
    if path.parent != CORPUS_JOBS_ROOT.resolve():
        raise ValueError("Invalid corpus job id.")
    return path


def _write_corpus_job_state(job_id: str, state: dict) -> None:
    job_dir = _corpus_job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = job_dir / "state.json.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(job_dir / "state.json")


def _read_corpus_job_state(job_id: str) -> dict | None:
    try:
        path = _corpus_job_dir(job_id) / "state.json"
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    owner_pid = state.get("worker_pid")
    owner_alive = False
    if isinstance(owner_pid, int) and owner_pid > 0:
        try:
            os.kill(owner_pid, 0)
            owner_alive = True
        except (OSError, ProcessLookupError):
            owner_alive = False
    # A poll can land on any Gunicorn process. A different process-local UUID
    # is not evidence that the background thread died; only a missing owner PID
    # is. This is what made valid jobs disappear after navigation/reload.
    has_owner_pid = isinstance(owner_pid, int) and owner_pid > 0
    legacy_owner_is_gone = (
        not has_owner_pid
        and bool(state.get("worker_instance_id"))
        and state.get("worker_instance_id") != CORPUS_WORKER_INSTANCE_ID
    )
    if state.get("status") in {"queued", "running"} and (
        (has_owner_pid and not owner_alive) or legacy_owner_is_gone
    ):
        state["status"] = "interrupted"
        state["error"] = "The backend restarted before this discovery job completed. Start a new discovery job to continue."
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        state["worker_instance_id"] = CORPUS_WORKER_INSTANCE_ID
        _write_corpus_job_state(job_id, state)
    return state


def _list_corpus_job_states() -> list[dict]:
    jobs: list[dict] = []
    for path in CORPUS_JOBS_ROOT.glob("*/state.json"):
        state = _read_corpus_job_state(path.parent.name)
        if state:
            jobs.append(state)
    jobs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return jobs


def _write_extraction_job_state(job_id: str, state: dict) -> None:
    job_dir = _extraction_job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    state = {**state, "updated_at": datetime.now(timezone.utc).isoformat()}
    temporary = job_dir / "state.json.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(job_dir / "state.json")


def _read_extraction_job_state(job_id: str) -> dict | None:
    try:
        path = _extraction_job_dir(job_id) / "state.json"
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    owner_pid = state.get("worker_pid")
    owner_alive = False
    if isinstance(owner_pid, int) and owner_pid > 0:
        try:
            os.kill(owner_pid, 0)
            owner_alive = True
        except (OSError, ProcessLookupError):
            owner_alive = False
    if (
        state.get("status") in {"queued", "running"}
        and isinstance(owner_pid, int)
        and owner_pid > 0
        and not owner_alive
    ):
        state["status"] = "interrupted"
        state["error"] = "The backend restarted before this extraction job completed. Start a new extraction job to continue."
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_extraction_job_state(job_id, state)
    return state


def _append_extraction_event(job_id: str, event: str, data: dict) -> None:
    record = {
        "event": event,
        "data": data,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    with EXTRACTION_JOBS_LOCK:
        job_dir = _extraction_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        with (job_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_extraction_events(job_id: str, after: int = 0) -> tuple[list[dict], int]:
    try:
        path = _extraction_job_dir(job_id) / "events.jsonl"
    except ValueError:
        return [], 0
    if not path.is_file():
        return [], 0
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    offset = max(0, min(after, len(records)))
    return records[offset:], len(records)


# --- Routes ---

@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "ledger-backend", "region": os.environ.get("AWS_REGION", "local")})


@app.route("/api/traffic", methods=["POST", "OPTIONS"])
def track_traffic():
    """Record one private visit event per browser session without exposing connector secrets."""
    if request.method == "OPTIONS":
        return "", 204
    configured_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    origin = request.headers.get("Origin", "")
    if configured_origins and not _allowed_origin(origin):
        return jsonify({"error": "Visit events are accepted only from the Ledger application."}), 403
    if request.content_length and request.content_length > 16 * 1024:
        return jsonify({"error": "Visit event is too large."}), 413
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "A JSON visit event is required."}), 400
    forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
    try:
        result = record_visit(payload, remote_ip=forwarded or request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError:
        app.logger.warning("Private visit tracking is temporarily unavailable.")
        return jsonify({"ok": False, "recorded": False}), 503
    return jsonify({"ok": True, **result}), 202


@app.route("/api/providers", methods=["GET"])
def get_providers():
    """Everything the settings UI needs to render provider and model choices."""
    return jsonify({
        "providers": [
            {
                "key": p.key,
                "label": p.label,
                "base_url": p.base_url,
                "default_model": p.default_model,
                "suggested_models": p.suggested_models,
                "reasoning_style": p.reasoning_style,
                "automatic_prompt_caching": p.automatic_prompt_caching,
                "docs": p.docs,
            }
            for p in PROVIDERS.values()
        ],
        "reasoning_efforts": REASONING_EFFORTS,
    })


@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings = current_settings()
    provider = get_provider(settings.get("provider"))
    return jsonify({
        "provider": settings.get("provider"),
        "provider_label": settings.get("provider_label"),
        "model": settings.get("model") or "",
        "base_url": settings.get("base_url") or "",
        "api_key_masked": mask_key(settings.get("api_key") or ""),
        "has_key": bool(settings.get("api_key")),
        "reasoning_effort": settings.get("reasoning_effort", "medium"),
        "reasoning_style": provider.reasoning_style,
        "prompt_caching": provider.automatic_prompt_caching,
        "enable_reasoning": settings.get("enable_reasoning", True),
        "temperature": settings.get("temperature", 0.0),
        "max_concurrency": settings.get("max_concurrency", 6),
        "auto_concurrency": settings.get("auto_concurrency", True),
        "firecrawl_key_masked": mask_key(settings.get("firecrawl_api_key") or ""),
        "has_firecrawl_key": bool(settings.get("firecrawl_api_key")),
        "firecrawl_pdf_mode": settings.get("firecrawl_pdf_mode", "auto"),
        "rate_limit": LIMITER.snapshot(),
    })


@app.route("/api/runtime-settings", methods=["POST"])
def update_runtime_settings():
    """Verify Firecrawl, then atomically save connector and scheduling settings."""
    data = request.get_json(silent=True) or {}
    current = current_settings()
    max_concurrency = max(1, min(int(parse_float(data.get("max_concurrency"), current.get("max_concurrency", 6))), 20))
    auto_concurrency = parse_bool(data.get("auto_concurrency"), current.get("auto_concurrency", True))
    firecrawl_api_key = str(data.get("firecrawl_api_key") or "").strip()
    firecrawl_pdf_mode = str(data.get("firecrawl_pdf_mode") or current.get("firecrawl_pdf_mode") or "auto").strip().lower()
    if firecrawl_pdf_mode not in {"fast", "auto", "ocr"}:
        return jsonify({"error": "Firecrawl PDF mode must be fast, auto, or ocr."}), 400
    candidate_key = firecrawl_api_key or str(current.get("firecrawl_api_key") or "")
    if not candidate_key:
        return jsonify({"error": "A Firecrawl API key is required before runtime settings can be saved."}), 400
    try:
        credit_usage = FirecrawlClient(candidate_key, timeout=20, max_attempts=1).credit_usage()
    except FirecrawlError as exc:
        return jsonify({"error": f"Firecrawl connection failed: {exc}"}), 400
    save_runtime_settings(
        max_concurrency=max_concurrency,
        auto_concurrency=auto_concurrency,
        firecrawl_api_key=firecrawl_api_key,
        keep_firecrawl_key=not bool(data.get("clear_firecrawl_key")),
        firecrawl_pdf_mode=firecrawl_pdf_mode,
    )
    LIMITER.resize(max_concurrency)
    return jsonify({
        "ok": True,
        "max_concurrency": max_concurrency,
        "auto_concurrency": auto_concurrency,
        "has_firecrawl_key": bool(current_settings().get("firecrawl_api_key")),
        "firecrawl_key_masked": mask_key(candidate_key),
        "firecrawl_credits": credit_usage,
        "firecrawl_pdf_mode": firecrawl_pdf_mode,
        "rate_limit": LIMITER.snapshot(),
    })


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json(silent=True) or {}
    provider_key = str(data.get("provider", "")).strip().lower()
    provider = get_provider(provider_key or None)

    saved = current_settings()
    api_key = str(data.get("api_key", "")).strip()
    model = str(data.get("model", "")).strip() or provider.default_model
    base_url = str(data.get("base_url", "")).strip() or provider.base_url
    temperature = max(0.0, min(parse_float(data.get("temperature"), 0.0), 1.0))

    effort = str(data.get("reasoning_effort", "")).strip().lower()
    if effort not in REASONING_EFFORTS:
        effort = "high" if parse_bool(data.get("enable_reasoning"), True) else "none"

    if not api_key:
        same_destination = (
            provider.key == saved.get("provider")
            and base_url.rstrip("/") == str(saved.get("base_url") or "").rstrip("/")
        )
        if same_destination and saved.get("api_key"):
            api_key = str(saved["api_key"])
        else:
            return jsonify({
                "error": "API key is required when changing provider or endpoint."
            }), 400
    if not model:
        return jsonify({"error": "Model ID is required."}), 400
    if not base_url:
        return jsonify({"error": "Base URL is required."}), 400

    try:
        ok, message, elapsed = test_api_key(
            api_key=api_key, model=model, base_url=base_url, provider=provider.key
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as a 500
        return jsonify({"error": str(exc)}), 500

    if not ok:
        return jsonify({"error": message}), 400

    save_verified_settings(
        api_key, model, base_url,
        enable_reasoning=effort != "none",
        temperature=temperature,
        provider=provider.key,
        reasoning_effort=effort,
    )
    return jsonify({"ok": True, "message": message, "elapsed": elapsed,
                    "provider": provider.key, "model": model})


@app.route("/api/prompt", methods=["GET"])
def get_prompt():
    return jsonify({"system_prompt": ACTIVE_PROMPT, "default_prompt": SYSTEM_PROMPT})


@app.route("/api/prompt", methods=["POST"])
def update_prompt():
    global ACTIVE_PROMPT
    data = request.get_json(silent=True) or {}
    new_prompt = str(data.get("system_prompt", "")).strip()
    if not new_prompt:
        return jsonify({"error": "System prompt cannot be empty."}), 400
    ACTIVE_PROMPT = new_prompt
    return jsonify({"ok": True, "message": "System prompt updated successfully."})


@app.route("/api/prompt", methods=["DELETE"])
def reset_prompt():
    global ACTIVE_PROMPT
    ACTIVE_PROMPT = SYSTEM_PROMPT
    return jsonify({"ok": True, "system_prompt": ACTIVE_PROMPT})


@app.route("/api/strategies", methods=["GET"])
def get_strategies():
    return jsonify({
        "strategies": [
            {
                "key": s.key,
                "label": s.label,
                "extraction": s.extraction_note,
                "parser": s.parser,
                "experiment": s.experiment,
                "ocr_enabled": s.ocr_enabled,
            }
            for s in STRATEGIES.values()
        ]
    })


@app.route("/api/extract", methods=["POST"])
def extract_pipeline():
    settings = current_settings()
    if not settings.get("api_key"):
        return jsonify({"error": "API key not configured. Please save your API key in Settings first."}), 400

    file = request.files.get("pdf")
    if file is None or not file.filename:
        return jsonify({"error": "No PDF file provided."}), 400

    options = request_run_options(settings)

    try:
        workspace_id = request_workspace_id()
        pdf_path = save_upload(file)
        prediction = run_pipeline(
            pdf_path=pdf_path,
            settings=settings,
            display_name=file.filename,
            workspace_id=workspace_id,
            **options,
        )
        return jsonify(prediction_response(prediction))
    except (GLMError, SchemaValidationError, ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected error: {exc}"}), 500


@app.route("/api/uploads", methods=["POST"])
def stage_uploads():
    """
    Stage PDFs and return a pre-flight plan.

    The browser uploads each file once here; the run endpoint then refers to the
    returned ids. The plan reports estimated input tokens and a recommended
    concurrency so the user can decide before spending anything.
    """
    files = [f for f in request.files.getlist("pdfs") if f and f.filename]
    if not files:
        return jsonify({"error": "No PDF files provided."}), 400

    settings = current_settings()
    workspace_id = request_workspace_id()
    requested_concurrency = settings.get("max_concurrency", 6)

    staged = []
    for file in files:
        try:
            path = save_upload(file)
            estimate = estimate_pdf_load(path)
        except Exception as exc:  # noqa: BLE001 - a corrupt PDF must not 500 the batch
            staged.append({"name": file.filename, "error": f"Could not read PDF: {exc}"})
            continue

        upload_id = uuid.uuid4().hex[:12]
        record = {
            "id": upload_id,
            "name": file.filename,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "pages": estimate["pages"],
            "approx_tokens": estimate["approx_tokens"],
            "estimated": True,
            "workspace_id": workspace_id,
        }
        with STAGED_LOCK:
            STAGED[upload_id] = record
        staged.append(record)

    usable = [f for f in staged if "error" not in f]
    plan = estimate_batch_plan(usable, requested_concurrency, settings.get("auto_concurrency", True))
    return jsonify({"ok": True, "files": staged, "plan": plan})


@app.route("/api/ratelimit", methods=["GET"])
def get_rate_limit():
    """What we have measured about the provider's limits this session."""
    return jsonify(LIMITER.snapshot())


@app.route("/api/corpus", methods=["GET"])
def get_corpus():
    manifest = load_manifest()
    documents = []
    workspace_id = request_workspace_id()
    for item in manifest.get("documents", []):
        company = report_identity(
            str(item.get("company") or item.get("company_slug") or "unknown"),
            item.get("fiscal_year"),
        )[0]
        fiscal_year = int(item.get("fiscal_year") or 0)
        output_directory = RUNS_DIR / company / f"FY{fiscal_year}"
        verification = verification_payload(item)
        documents.append({
            **item,
            "verification_status": verification.get("status"),
            "candidate_extracted": verification.get("candidate_extracted", False),
            "candidate_count": verification.get("extracted_row_count", 0),
            "candidate_method": verification.get("candidate_method"),
            "consensus_summary": verification.get("consensus_summary"),
            "approved_at": verification.get("approved_at"),
            "output_directory": str(output_directory),
            "output_count": _workspace_prediction_count(output_directory, workspace_id),
        })
    # Keep the library useful before every research seed has yielded a valid
    # filing. Stored reports come first; the remaining slots are filled from
    # the evidence-backed Bakuraku company registry. A seed is never presented
    # as a downloaded or verified report.
    target_by_company: dict[str, dict] = {}
    for item in documents:
        company = str(item.get("company") or "").strip()
        if company and company not in target_by_company:
            target_by_company[company] = {
                "company": company,
                "official_url": str(item.get("source_url") or ""),
                "country": "",
                "evidence_url": "",
                "status": "report_stored",
            }
    customers_path = Path("research/bakuraku/customers.csv")
    if customers_path.exists():
        with customers_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                company = str(row.get("company_name") or "").strip()
                if not company or company in target_by_company:
                    continue
                target_by_company[company] = {
                    "company": company,
                    "official_url": str(row.get("official_website") or ""),
                    "country": "JP",
                    "evidence_url": str(row.get("evidence_url") or ""),
                    "status": "research_seed",
                }
                if len(target_by_company) >= 100:
                    break
    targets = list(target_by_company.values())[:100]
    return jsonify({
        **manifest,
        "documents": documents,
        "targets": targets,
        "summary": {
            "documents": len(documents),
            "companies": len(targets),
            "companies_with_reports": len({item.get("company_slug") for item in documents}),
            "ok": sum(item.get("screened") == "ok" for item in documents),
            "review": sum(item.get("screened") == "review" for item in documents),
            "unreadable": sum(item.get("screened") == "unreadable" for item in documents),
            "verified": sum(item.get("verification_status") in {"assignment_supplied", "human_verified", "independently_verified"} for item in documents),
            "human_review_required": sum(item.get("verification_status") == "human_review_required" for item in documents),
        },
    })


@app.route("/api/corpus/<document_id>/pdf", methods=["GET"])
def get_corpus_pdf(document_id):
    """Serve a pinned source PDF for side-by-side human verification."""
    document = find_document(document_id)
    if document is None:
        return jsonify({"error": "Corpus document not found."}), 404
    path = Path(str(document.get("local_path") or "")).resolve()
    if not path.is_relative_to(CORPUS_ROOT.resolve()) or not path.is_file():
        return jsonify({"error": "The pinned PDF is missing from corpus storage."}), 404
    return send_file(path, mimetype="application/pdf", as_attachment=False, download_name=str(document.get("filename") or path.name))


@app.route("/api/corpus/<document_id>/verification", methods=["GET", "PUT"])
def corpus_verification(document_id):
    document = find_document(document_id)
    if document is None:
        return jsonify({"error": "Corpus document not found."}), 404
    if request.method == "GET":
        return jsonify(verification_payload(document))
    existing = verification_payload(document)
    if existing.get("status") in {"assignment_supplied", "independently_verified"}:
        return jsonify({"error": "This source-audited answer key is immutable."}), 409
    body = request.get_json(silent=True) or {}
    rows = body.get("rows")
    if not isinstance(rows, list):
        return jsonify({"error": "A 27-row review table is required."}), 400
    try:
        payload = approve_document_answers(document_id, rows, reviewer=str(body.get("reviewer") or "human"))
    except KeyError:
        return jsonify({"error": "Corpus document not found."}), 404
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, **payload})


@app.route("/api/corpus/<document_id>/verification/extract", methods=["POST"])
def extract_corpus_verification(document_id):
    """Create the PDF-derived prefill required before human review.

    Reviewers correct extracted values; they are never asked to author a blank
    benchmark table. The provisional rows remain non-authoritative until the
    separate approval call succeeds.
    """
    document = find_document(document_id)
    if document is None:
        return jsonify({"error": "Corpus document not found."}), 404
    existing = verification_payload(document)
    reusable_candidate = str(existing.get("candidate_method") or "").startswith("configured_llm")
    if existing.get("candidate_extracted") and (
        existing.get("status") in {"assignment_supplied", "human_verified", "independently_verified"} or reusable_candidate
    ):
        return jsonify({"ok": True, "reused": True, **existing})

    settings = current_settings()
    if not settings.get("api_key"):
        return jsonify({
            "error": "PDF answer extraction is unavailable until the model API key is configured."
        }), 400
    try:
        prediction = run_pipeline(
            pdf_path=Path(str(document.get("local_path") or "")),
            settings=settings,
            strategy_key="s2",
            system_prompt=ACTIVE_PROMPT,
            fiscal_year_hint=str(document.get("fiscal_year") or ""),
            company_hint=str(document.get("company") or ""),
            output_currency=str(document.get("currency") or "USD"),
            display_name=str(document.get("filename") or Path(str(document.get("local_path") or "")).name),
            workspace_id=request_workspace_id(),
            enable_reasoning=bool(settings.get("enable_reasoning", True)),
            reasoning_effort=str(settings.get("reasoning_effort") or ""),
            temperature=float(settings.get("temperature", 0.0)),
        )
        updated = pin_candidate_answers(
            document,
            {
                "detected_fiscal_year": prediction.get("detected_fiscal_year") or prediction.get("fiscal_year"),
                "rows": prediction.get("rows") or [],
                "mode": "semantic_mapping",
                "metadata": {
                    "run_id": prediction.get("run_id"),
                    "model": prediction.get("model"),
                    "provider": prediction.get("provider"),
                },
            },
            requested_passes=1,
            provider="configured_llm",
        )
        payload = verification_payload(updated)
    except (GLMError, SchemaValidationError, RuntimeError, ValueError, OSError) as exc:
        return jsonify({"error": f"Could not extract review answers from the PDF: {exc}"}), 502
    return jsonify({"ok": True, "reused": False, **payload}), 201


@app.route("/api/corpus/<document_id>", methods=["DELETE"])
def delete_corpus_document(document_id):
    """Remove one downloaded corpus PDF and its pinned manifest entry.

    Extraction outputs are historical run artifacts and deliberately remain in
    place, even when their source document is removed from the corpus.
    """
    try:
        deleted = delete_pinned_document(document_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        return jsonify({"error": f"Could not delete the stored PDF: {exc}"}), 500
    if deleted is None:
        return jsonify({"error": "Corpus document not found."}), 404
    return jsonify({
        "ok": True,
        "deleted": {
            "filename": deleted.get("filename"),
            "file_removed": deleted.get("file_removed", False),
        },
    })


@app.route("/api/corpus/stage", methods=["POST"])
def stage_corpus_documents():
    """Stage durable corpus PDFs through the same extraction contract as uploads."""
    body = request.get_json(silent=True) or {}
    workspace_id = request_workspace_id()
    document_ids = body.get("document_ids") or []
    if not isinstance(document_ids, list) or not document_ids:
        return jsonify({"error": "Select at least one corpus document."}), 400
    if len(document_ids) > 50:
        return jsonify({"error": "Stage at most 50 corpus documents at once."}), 400

    manifest = load_manifest()
    by_id = {str(item.get("sha256") or ""): item for item in manifest.get("documents", [])}
    corpus_root = CORPUS_ROOT.resolve()
    settings = current_settings()
    staged = []
    seen = set()
    for raw_id in document_ids:
        document_id = str(raw_id or "").strip()
        if not document_id or document_id in seen:
            continue
        seen.add(document_id)
        document = by_id.get(document_id)
        if not document:
            staged.append({"name": document_id, "error": "Corpus document not found."})
            continue
        try:
            path = Path(str(document.get("local_path") or "")).resolve()
            if not path.is_relative_to(corpus_root) or not path.is_file():
                raise ValueError("The pinned PDF is missing from corpus storage.")
            estimate = estimate_pdf_load(path)
        except Exception as exc:  # noqa: BLE001 - report an invalid manifest entry per file
            staged.append({"name": document.get("filename") or document_id, "error": str(exc)})
            continue

        upload_id = uuid.uuid4().hex[:12]
        record = {
            "id": upload_id,
            "name": document.get("filename") or path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "pages": estimate["pages"],
            "approx_tokens": estimate["approx_tokens"],
            "estimated": True,
            "source": "corpus",
            "company": document.get("company"),
            "fiscal_year": document.get("fiscal_year"),
            "currency": str(document.get("currency") or "USD").upper(),
            "source_pdf_sha256": document.get("sha256"),
            "verification_status": verification_payload(document).get("status"),
            "workspace_id": workspace_id,
        }
        with STAGED_LOCK:
            STAGED[upload_id] = record
        staged.append(record)

    usable = [item for item in staged if "error" not in item]
    plan = estimate_batch_plan(usable, settings.get("max_concurrency", 6), settings.get("auto_concurrency", True))
    advisories = [
        f"{item['name']} has not been human verified; exact accuracy will not be reported."
        for item in usable
        if item.get("verification_status") == "human_review_required"
    ]
    return jsonify({"ok": bool(usable), "files": staged, "plan": plan, "advisories": advisories})


@app.route("/api/bakuraku/customers", methods=["GET"])
def get_bakuraku_customers():
    """Return the evidence-backed customer seed list produced by research."""
    path = Path("research/bakuraku/customers.csv")
    if not path.exists():
        return jsonify({"customers": [], "count": 0})
    with path.open(encoding="utf-8", newline="") as handle:
        customers = list(csv.DictReader(handle))
    return jsonify({"customers": customers, "count": len(customers)})


@app.route("/api/corpus/jobs", methods=["POST"])
def start_corpus_job():
    data = request.get_json(silent=True) or {}
    companies = data.get("companies") or []
    if not isinstance(companies, list) or not companies:
        return jsonify({"error": "Add at least one company."}), 400
    if len(companies) > 200:
        return jsonify({"error": "Start with at most 200 companies per discovery job."}), 400
    cleaned = []
    for item in companies:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        cleaned.append({
            "name": str(item["name"]).strip(),
            "official_url": str(item.get("official_url") or "").strip(),
            "country": str(item.get("country") or "US").strip().upper(),
        })
    if not cleaned:
        return jsonify({"error": "No valid company names were supplied."}), 400
    years = sorted({int(year) for year in (data.get("years") or range(2020, 2026)) if str(year).isdigit() and 2020 <= int(year) <= 2025})
    if not years:
        return jsonify({"error": "Choose at least one year from 2020 through 2025."}), 400

    settings = current_settings()
    if not settings.get("firecrawl_api_key"):
        return jsonify({"error": "Configure the Firecrawl API key in Settings first."}), 400

    with CORPUS_JOBS_LOCK:
        active = next(
            (item for item in _list_corpus_job_states() if item.get("status") in {"queued", "running"}),
            None,
        )
    if active:
        return jsonify({
            "error": f"Corpus discovery job {active['id']} is already running.",
            "job_id": active["id"],
            "status": active["status"],
        }), 409

    job_id = uuid.uuid4().hex[:12]
    created_at = datetime.now(timezone.utc).isoformat()
    job = {
        "id": job_id,
        "status": "queued",
        "created_at": created_at,
        "updated_at": created_at,
        "worker_instance_id": CORPUS_WORKER_INSTANCE_ID,
        "worker_pid": os.getpid(),
        "companies": cleaned,
        "years": years,
        "events": [],
        "result": None,
        "error": None,
    }
    with CORPUS_JOBS_LOCK:
        CORPUS_JOBS[job_id] = job
        _write_corpus_job_state(job_id, job)

    def run_job() -> None:
        def on_event(event: dict) -> None:
            with CORPUS_JOBS_LOCK:
                job["events"] = [*job["events"][-199:], {**event, "at": datetime.now(timezone.utc).isoformat()}]
                job["status"] = "running"
                _write_corpus_job_state(job_id, job)
        with CORPUS_JOBS_LOCK:
            job["status"] = "running"
            _write_corpus_job_state(job_id, job)
        try:
            result = build_corpus(
                cleaned,
                years,
                api_key=settings["firecrawl_api_key"],
                max_downloads=min(settings.get("max_concurrency", 3), 6),
                on_event=on_event,
            )
        except Exception as exc:  # noqa: BLE001 - background failures are reported to the UI
            with CORPUS_JOBS_LOCK:
                job["status"] = "failed"
                job["error"] = str(exc)
                job["finished_at"] = datetime.now(timezone.utc).isoformat()
                _write_corpus_job_state(job_id, job)
        else:
            with CORPUS_JOBS_LOCK:
                job["status"] = "complete"
                job["result"] = result
                job["finished_at"] = datetime.now(timezone.utc).isoformat()
                _write_corpus_job_state(job_id, job)

    threading.Thread(target=run_job, daemon=True, name=f"corpus-{job_id}").start()
    return jsonify({"ok": True, "job_id": job_id, "status": "queued"}), 202


@app.route("/api/corpus/jobs", methods=["GET"])
def list_corpus_jobs():
    """Return recent durable discovery jobs so a new tab can rehydrate progress."""
    with CORPUS_JOBS_LOCK:
        jobs = _list_corpus_job_states()
    return jsonify({"jobs": jobs[:20]})


@app.route("/api/corpus/jobs/<job_id>", methods=["GET"])
def get_corpus_job(job_id):
    with CORPUS_JOBS_LOCK:
        job = CORPUS_JOBS.get(job_id) or _read_corpus_job_state(job_id)
        if job is None:
            return jsonify({"error": "Corpus job not found."}), 404
        return jsonify(json.loads(json.dumps(job)))


@app.route("/api/extraction/jobs", methods=["GET"])
def list_extraction_jobs():
    """Return recent durable extraction-job summaries for UI rehydration."""
    jobs: list[dict] = []
    workspace_id = request_workspace_id()
    for path in EXTRACTION_JOBS_ROOT.glob("*/state.json"):
        try:
            state = _read_extraction_job_state(path.parent.name)
            if _workspace_matches(state, workspace_id):
                jobs.append(state)
        except (OSError, json.JSONDecodeError):
            continue
    jobs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return jsonify({"jobs": jobs[:20]})


@app.route("/api/extraction/jobs/<job_id>", methods=["GET"])
def get_extraction_job(job_id):
    state = _read_extraction_job_state(job_id)
    if not _workspace_matches(state, request_workspace_id()):
        return jsonify({"error": "Extraction job not found."}), 404
    try:
        after = max(0, int(request.args.get("after", "0")))
    except ValueError:
        after = 0
    events, next_offset = _read_extraction_events(job_id, after)
    return jsonify({**state, "events": events, "next_offset": next_offset})


@app.route("/api/extraction/jobs", methods=["POST"])
def start_extraction_job():
    """Start a backend-owned extraction batch that survives browser navigation."""
    settings = current_settings()
    workspace_id = request_workspace_id()
    if not settings.get("api_key"):
        return jsonify({"error": "API key not configured."}), 400
    body = request.get_json(silent=True) or {}
    upload_ids = body.get("upload_ids") or []
    if not isinstance(upload_ids, list) or not upload_ids:
        return jsonify({"error": "No staged uploads referenced."}), 400
    with STAGED_LOCK:
        staged_jobs = [
            STAGED[uid] for uid in upload_ids
            if uid in STAGED and _workspace_matches(STAGED[uid], workspace_id)
        ]
    if not staged_jobs:
        return jsonify({"error": "Staged uploads expired. Please re-select the files."}), 400

    requested = body.get("strategies") or body.get("strategy") or "s1"
    if isinstance(requested, str):
        requested = [requested]
    strategy_keys = [str(key).strip().lower() for key in requested if str(key).strip()] or ["s1"]
    unknown = [key for key in strategy_keys if key not in STRATEGIES]
    if unknown:
        return jsonify({"error": f"Unknown strategy: {', '.join(unknown)}", "available": list(STRATEGIES)}), 400

    options = {
        "system_prompt": str(body.get("system_prompt") or "").strip() or ACTIVE_PROMPT,
        "fiscal_year_hint": str(body.get("fiscal_year") or "").strip(),
        "enable_reasoning": parse_bool(body.get("enable_reasoning"), settings.get("enable_reasoning", True)),
        "temperature": parse_float(body.get("temperature"), settings.get("temperature", 0.0)),
        "reasoning_effort": str(body.get("reasoning_effort") or "").strip().lower(),
    }
    plan = estimate_batch_plan(staged_jobs, settings.get("max_concurrency", 6), settings.get("auto_concurrency", True))
    concurrency = plan["recommended_concurrency"]
    job_id = uuid.uuid4().hex[:16]
    created_at = datetime.now(timezone.utc).isoformat()
    state = {
        "id": job_id, "status": "queued", "created_at": created_at, "updated_at": created_at,
        "scope": "s3" if "s3" in strategy_keys else "s2" if any(key.startswith("s2") for key in strategy_keys) else "s1",
        "strategies": strategy_keys, "files_total": len(staged_jobs),
        "passes_total": len(staged_jobs) * len(strategy_keys), "succeeded": 0, "failed": 0,
        "error": None,
        "worker_pid": os.getpid(),
        "workspace_id": workspace_id,
    }
    with EXTRACTION_JOBS_LOCK:
        _write_extraction_job_state(job_id, state)
        _append_extraction_event(job_id, "batch_start", {
            "job_id": job_id, "total": state["passes_total"], "files_total": len(staged_jobs),
            "concurrency": concurrency,
            "strategies": [{"key": key, "label": STRATEGIES[key].label} for key in strategy_keys],
            "files": [{"index": index, "name": item["name"], "pages": item["pages"], "approx_tokens": item["approx_tokens"]} for index, item in enumerate(staged_jobs)],
        })

    def append(event: str, data: dict) -> None:
        _append_extraction_event(job_id, event, data)

    def run_job() -> None:
        quota_hit: dict[str, str] = {}
        counts = {"succeeded": 0, "failed": 0}
        counts_lock = threading.Lock()
        state["status"] = "running"
        _write_extraction_job_state(job_id, state)

        def increment_count(key: str) -> None:
            with counts_lock:
                counts[key] += 1

        def run_one(index: int, staged: dict, key: str) -> None:
            strategy = STRATEGIES[key]

            def on_progress(update: dict) -> None:
                append("progress", {"index": index, "file": staged["name"], "strategy": key, **update})

            append("pass_start", {"index": index, "file": staged["name"], "strategy": key, "strategy_label": strategy.label, "pages": staged["pages"], "approx_tokens": staged["approx_tokens"]})
            try:
                job_options = {**options}
                if staged.get("source") == "corpus":
                    job_options.update({
                        "fiscal_year_hint": str(staged.get("fiscal_year") or ""),
                        "company_hint": str(staged.get("company") or ""),
                        "output_currency": str(staged.get("currency") or "USD"),
                    })
                prediction = run_pipeline(pdf_path=Path(staged["path"]), settings=settings, strategy_key=key, display_name=staged["name"], on_progress=on_progress, workspace_id=workspace_id, **job_options)
                increment_count("succeeded")
                append("file_done", {
                    "index": index, "file": staged["name"], "strategy": key, "strategy_label": strategy.label,
                    "input_tokens": prediction["approx_input_tokens"], "consistency": prediction["metrics"].get("consistency"),
                    "extract_seconds": prediction.get("extract_seconds"), "total_seconds": prediction.get("total_seconds"),
                    "ok": True, "run_id": prediction["run_id"], "fiscal_year": prediction["fiscal_year"],
                    "api_elapsed_seconds": prediction["api_elapsed_seconds"], "page_count": prediction["page_count"],
                    "approx_input_tokens": prediction["approx_input_tokens"], "metrics": prediction["metrics"],
                    "warnings": prediction["warnings"], "contract_repairs": prediction["contract_repairs"],
                })
            except QuotaExhaustedError as exc:
                quota_hit.setdefault("message", str(exc))
                increment_count("failed")
                append("quota_exhausted", {"message": str(exc)})
                append("file_done", {"index": index, "file": staged["name"], "strategy": key, "strategy_label": strategy.label, "ok": False, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                increment_count("failed")
                append("file_done", {"index": index, "file": staged["name"], "strategy": key, "strategy_label": strategy.label, "ok": False, "error": str(exc)})

        def run_file(index: int, staged: dict) -> None:
            for key in strategy_keys:
                if quota_hit:
                    increment_count("failed")
                    append("file_done", {"index": index, "file": staged["name"], "strategy": key, "strategy_label": STRATEGIES[key].label, "ok": False, "error": f"Skipped — {quota_hit['message']}"})
                else:
                    run_one(index, staged, key)
            append("file_complete", {"index": index, "file": staged["name"]})

        try:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                list(pool.map(lambda item: run_file(*item), list(enumerate(staged_jobs))))
            with STAGED_LOCK:
                for staged in staged_jobs:
                    STAGED.pop(staged["id"], None)
            state.update({"status": "complete", **counts})
            append("batch_done", {"job_id": job_id, "quota_exhausted": quota_hit.get("message"), "total": state["passes_total"], **counts, "rate_limit": LIMITER.snapshot()})
        except Exception as exc:  # noqa: BLE001
            state.update({"status": "failed", "error": str(exc), **counts})
            append("batch_failed", {"job_id": job_id, "error": str(exc)})
        finally:
            _write_extraction_job_state(job_id, state)

    threading.Thread(target=run_job, daemon=True, name=f"extract-{job_id}").start()
    return jsonify({"ok": True, "job_id": job_id, "status": "queued"}), 202


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.route("/api/extract/stream", methods=["POST"])
def extract_stream():
    """
    Run one or more staged PDFs and stream progress as Server-Sent Events.

    Files run concurrently; every pipeline step of every file is emitted as it
    happens, so the UI can animate the real execution rather than a fake
    timeline. Concurrency is a ceiling — the adaptive limiter in ratelimit.py
    lowers the effective value if the provider starts returning 429.
    """
    settings = current_settings()
    workspace_id = request_workspace_id()
    if not settings.get("api_key"):
        return jsonify({"error": "API key not configured."}), 400

    body = request.get_json(silent=True) or {}
    upload_ids = body.get("upload_ids") or []
    if not isinstance(upload_ids, list) or not upload_ids:
        return jsonify({"error": "No staged uploads referenced."}), 400

    with STAGED_LOCK:
        jobs = [
            STAGED[uid] for uid in upload_ids
            if uid in STAGED and _workspace_matches(STAGED[uid], workspace_id)
        ]
    if not jobs:
        return jsonify({"error": "Staged uploads expired. Please re-select the files."}), 400

    # One PDF can run through several selected parsers so comparison uses
    # identical input. OCR policy is defined by the strategy/parser registry.
    requested = body.get("strategies") or body.get("strategy") or "s1"
    if isinstance(requested, str):
        requested = [requested]
    strategy_keys = [str(k).strip().lower() for k in requested if str(k).strip()]
    if not strategy_keys:
        strategy_keys = ["s1"]
    unknown = [key for key in strategy_keys if key not in STRATEGIES]
    if unknown:
        return jsonify({
            "error": f"Unknown strategy: {', '.join(unknown)}",
            "available": list(STRATEGIES),
        }), 400

    options = {
        "system_prompt": str(body.get("system_prompt") or "").strip() or ACTIVE_PROMPT,
        "fiscal_year_hint": str(body.get("fiscal_year") or "").strip(),
        "enable_reasoning": parse_bool(body.get("enable_reasoning"), settings.get("enable_reasoning", True)),
        "temperature": parse_float(body.get("temperature"), settings.get("temperature", 0.0)),
        "reasoning_effort": str(body.get("reasoning_effort") or "").strip().lower(),
    }
    plan = estimate_batch_plan(jobs, settings.get("max_concurrency", 6), settings.get("auto_concurrency", True))
    concurrency = plan["recommended_concurrency"]

    events: queue.Queue = queue.Queue()
    DONE = object()

    quota_hit: dict = {}

    def worker(index: int, job: dict) -> None:
        """
        Run every requested technology for ONE file, one after another.

        Sequential within a file on purpose: the UI shows one row per file whose
        parser label changes as the passes proceed, so two passes of the same
        file must never be in flight at once. Files still run concurrently, so
        the wall clock is unchanged for a batch.
        """
        for key in strategy_keys:
            if quota_hit:
                events.put(("file_done", {
                    "index": index, "file": job["name"], "strategy": key,
                    "strategy_label": STRATEGIES[key].label, "ok": False,
                    "error": f"Skipped — {quota_hit['message']}",
                }))
                continue
            _run_one(index, job, key)
        events.put(("file_complete", {"index": index, "file": job["name"]}))

    def _run_one(index: int, job: dict, key: str) -> None:
        strategy = STRATEGIES[key]

        def on_progress(update: dict) -> None:
            events.put(("progress", {"index": index, "file": job["name"],
                                     "strategy": key, **update}))

        events.put(("pass_start", {"index": index, "file": job["name"], "strategy": key,
                                   "strategy_label": strategy.label, "pages": job["pages"],
                                   "approx_tokens": job["approx_tokens"]}))
        try:
            job_options = {**options}
            if job.get("source") == "corpus":
                job_options.update({
                    "fiscal_year_hint": str(job.get("fiscal_year") or ""),
                    "company_hint": str(job.get("company") or ""),
                    "output_currency": str(job.get("currency") or "USD"),
                })
            prediction = run_pipeline(
                pdf_path=Path(job["path"]),
                settings=settings,
                strategy_key=key,
                display_name=job["name"],
                on_progress=on_progress,
                workspace_id=workspace_id,
                **job_options,
            )
            events.put(("file_done", {
                "index": index,
                "file": job["name"],
                "strategy": key,
                "strategy_label": strategy.label,
                "input_tokens": prediction["approx_input_tokens"],
                "consistency": prediction["metrics"].get("consistency"),
                "extract_seconds": prediction.get("extract_seconds"),
                "total_seconds": prediction.get("total_seconds"),
                "ok": True,
                "run_id": prediction["run_id"],
                "fiscal_year": prediction["fiscal_year"],
                "api_elapsed_seconds": prediction["api_elapsed_seconds"],
                "page_count": prediction["page_count"],
                "approx_input_tokens": prediction["approx_input_tokens"],
                "metrics": prediction["metrics"],
                "warnings": prediction["warnings"],
                "contract_repairs": prediction["contract_repairs"],
            }))
        except QuotaExhaustedError as exc:
            # Nothing else will succeed until the window resets; stop scheduling
            # work rather than failing every remaining unit one by one.
            quota_hit.setdefault("message", str(exc))
            events.put(("quota_exhausted", {"message": str(exc)}))
            events.put(("file_done", {
                "index": index, "file": job["name"], "strategy": key,
                "strategy_label": strategy.label, "ok": False, "error": str(exc),
            }))
        except Exception as exc:  # noqa: BLE001 - one bad pass must not kill the run
            events.put(("file_done", {
                "index": index, "file": job["name"], "strategy": key,
                "strategy_label": strategy.label, "ok": False, "error": str(exc),
            }))

    def run_all() -> None:
        # The pool bounds how many files are in flight; the adaptive limiter
        # separately bounds how many API calls are in flight.
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            list(pool.map(lambda item: worker(*item), list(enumerate(jobs))))
        with STAGED_LOCK:
            for job in jobs:
                STAGED.pop(job["id"], None)
        events.put((DONE, None))

    threading.Thread(target=run_all, daemon=True).start()

    @stream_with_context
    def generate():
        yield _sse("batch_start", {
            "total": len(jobs) * len(strategy_keys),
            "files_total": len(jobs),
            "concurrency": concurrency,
            "strategies": [{"key": k, "label": STRATEGIES[k].label} for k in strategy_keys],
            "files": [{"index": i, "name": j["name"], "pages": j["pages"],
                       "approx_tokens": j["approx_tokens"]} for i, j in enumerate(jobs)],
        })
        succeeded = 0
        failed = 0
        while True:
            try:
                kind, payload = events.get(timeout=30)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if kind is DONE:
                break
            if kind == "file_done":
                succeeded += 1 if payload.get("ok") else 0
                failed += 0 if payload.get("ok") else 1
            yield _sse(kind, payload)
        yield _sse("batch_done", {
            "quota_exhausted": quota_hit.get("message"),
            "total": len(jobs) * len(strategy_keys),
            "succeeded": succeeded,
            "failed": failed,
            "rate_limit": LIMITER.snapshot(),
        })

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.route("/api/extract/batch", methods=["POST"])
def batch_extract():
    """Non-streaming multipart batch retained for scripted API clients."""
    settings = current_settings()
    workspace_id = request_workspace_id()
    if not settings.get("api_key"):
        return jsonify({"error": "API key not configured."}), 400

    files = [f for f in request.files.getlist("pdfs") if f and f.filename]
    if not files:
        return jsonify({"error": "No PDF files provided."}), 400

    options = request_run_options(settings)
    saved = [(f.filename, save_upload(f)) for f in files]
    estimates = []
    for _filename, path in saved:
        estimates.append(estimate_pdf_load(path))
    plan_files = [{"name": saved[index][0], **estimate} for index, estimate in enumerate(estimates)]
    concurrency = estimate_batch_plan(plan_files, settings.get("max_concurrency", 6), settings.get("auto_concurrency", True))["recommended_concurrency"]

    def process_single(filename: str, pdf_path):
        try:
            prediction = run_pipeline(
                pdf_path=pdf_path, settings=settings, display_name=filename, workspace_id=workspace_id, **options
            )
            return {
                "ok": True,
                "filename": filename,
                "run_id": prediction["run_id"],
                "fiscal_year": prediction["fiscal_year"],
                "api_elapsed_seconds": prediction["api_elapsed_seconds"],
                "metrics": prediction["metrics"],
                "warnings": prediction["warnings"],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "filename": filename, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(lambda item: process_single(*item), saved))

    succeeded = sum(1 for r in results if r.get("ok"))
    return jsonify({
        "ok": True,
        "results": results,
        "summary": {"total": len(results), "succeeded": succeeded, "failed": len(results) - succeeded},
        "rate_limit": LIMITER.snapshot(),
    })


@app.route("/api/runs", methods=["GET"])
def get_runs():
    return jsonify({"runs": list_runs(request_workspace_id())})


@app.route("/api/benchmark-runs", methods=["GET"])
def get_benchmark_runs():
    """Return safe summaries for source-verified corpus runs across workspaces.

    Personal history remains workspace-isolated. The dashboard may compare
    only runs whose exact source hash is bound to an audited corpus sheet.
    """
    verified_hashes = {
        str(document.get("sha256") or "")
        for document in load_manifest().get("documents", [])
        if verification_payload(document).get("status")
        in {"assignment_supplied", "human_verified", "independently_verified"}
    }
    return jsonify({
        "runs": [
            run for run in list_runs(None)
            if str(run.get("source_pdf_sha256") or "") in verified_hashes
        ]
    })


@app.route("/api/runs/all", methods=["DELETE"])
def delete_all_runs():
    workspace_id = request_workspace_id()
    owned = [
        directory for directory in iter_run_dirs()
        if _workspace_matches(load_prediction(directory.name), workspace_id)
    ]
    count = len(owned)
    for directory in owned:
        shutil.rmtree(directory)
    return jsonify({"ok": True, "deleted": count})


@app.route("/api/runs/<run_id>", methods=["GET"])
def get_run(run_id):
    prediction = load_prediction(run_id)
    if not _workspace_matches(prediction, request_workspace_id()):
        return jsonify({"error": f"Run '{run_id}' not found."}), 404
    return jsonify(prediction_response(prediction))


@app.route("/api/runs/<run_id>", methods=["DELETE"])
def delete_run(run_id):
    target_dir = find_run_dir(run_id)
    prediction = load_prediction(run_id)
    if target_dir is None or not target_dir.is_dir() or not _workspace_matches(prediction, request_workspace_id()):
        return jsonify({"error": f"Run '{run_id}' not found."}), 404
    try:
        shutil.rmtree(target_dir)
    except OSError as exc:
        return jsonify({"error": f"Failed to delete run: {exc}"}), 500
    return jsonify({"ok": True, "message": f"Run '{run_id}' deleted successfully."})


@app.route("/api/schema", methods=["GET"])
def get_schema():
    # FY2022 is the only assignment-supplied answer key. Candidate and
    # human-approved keys are reviewed per PDF SHA through the corpus API.
    return jsonify([
        {**row, "golden_answers": {"2022": row.get("golden_answers", {}).get("2022")}}
        for row in BENCHMARK_SCHEMA_METADATA
    ])


@app.route("/api/golden_answers", methods=["GET"])
def get_golden_answers():
    return jsonify({"2022": GOLDEN_ANSWERS_STORE["2022"]})


@app.route("/api/golden_answers/<fiscal_year>", methods=["POST"])
def save_golden_answers(fiscal_year):
    if str(fiscal_year) != "2022":
        return jsonify({"error": "Only the assignment-supplied FY2022 key is exposed here. Review other reports through the corpus verification workflow."}), 409
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload format. Expected an object of item -> number."}), 400

    cleaned: dict[str, float] = {}
    for item, value in data.items():
        if item not in CANONICAL_ITEMS:
            return jsonify({"error": f"Unknown schema item: {item!r}"}), 400
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, Real):
            return jsonify({"error": f"Value for {item!r} must be a number, got {value!r}"}), 400
        cleaned[item] = float(value)

    GOLDEN_ANSWERS_STORE[fiscal_year] = cleaned
    for item_meta in BENCHMARK_SCHEMA_METADATA:
        item_meta["golden_answers"][fiscal_year] = cleaned.get(item_meta["item"])
    return jsonify({"ok": True, "message": f"Golden answers for FY {fiscal_year} updated."})


@app.route("/api/evaluate/<run_id>", methods=["GET"])
def evaluate_run(run_id):
    """Re-score a stored run, optionally against a different fiscal year."""
    prediction = load_prediction(run_id)
    if not _workspace_matches(prediction, request_workspace_id()):
        return jsonify({"error": f"Run '{run_id}' not found."}), 404
    fiscal_year = request.args.get("fiscal_year") or prediction.get("fiscal_year", "")
    return jsonify({
        "run_id": prediction.get("run_id", run_id),
        "fiscal_year": fiscal_year,
        "metrics": compute_metrics(prediction.get("rows", []), fiscal_year, prediction.get("company"), prediction.get("source_pdf_sha256")),
    })


@app.after_request
def no_store(response):
    """Never let a browser hold on to the UI assets or an API reply."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    origin = _allowed_origin(request.headers.get("Origin", ""))
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Ledger-Workspace"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


@app.errorhandler(413)
def payload_too_large(_exc):
    return jsonify({"error": "Upload exceeds the 256 MB request limit."}), 413


def _free_port(preferred: int = 5000) -> int:
    """
    Return a usable port.

    macOS ships AirPlay Receiver bound to port 5000, which is the single most
    common reason this server appears to "crash" on startup here. Fall back
    rather than failing.
    """
    import socket

    for candidate in (preferred, 5001, 5050, 8000, 8080):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", candidate))
                return candidate
            except OSError:
                continue
    return 0  # let the OS choose


if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT") or _free_port())
    if port != 5000:
        print(f"  port 5000 is in use (macOS AirPlay Receiver commonly holds it)")
    print(f"  Financial Report System -> http://127.0.0.1:{port}")
    app.run(debug=True, port=port)
