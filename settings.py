import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv, set_key

from providers import DEFAULT_PROVIDER, REASONING_EFFORTS, get_provider, provider_for_base_url

ENV_PATH = Path(".env")

# Kept for the legacy Streamlit app, which offers these two by name.
GENERAL_BASE_URL = "https://api.z.ai/api/paas/v4"
CODING_BASE_URL = "https://api.z.ai/api/coding/paas/v4"


def load_local_env() -> None:
    load_dotenv(ENV_PATH, override=True)


def _reasoning_effort_from_env() -> str:
    """
    Read the reasoning setting, accepting the old boolean form.

    Older .env files carry LLM_ENABLE_REASONING=true|false; those map onto the
    graded scale so an existing setup keeps working.
    """
    effort = (os.getenv("LLM_REASONING_EFFORT") or "").strip().lower()
    if effort in REASONING_EFFORTS:
        return effort
    legacy = (os.getenv("GLM_ENABLE_REASONING") or os.getenv("LLM_ENABLE_REASONING") or "").strip().lower()
    if legacy in ("false", "0", "no"):
        return "none"
    if legacy in ("true", "1", "yes"):
        return "high"
    return "medium"


def current_settings() -> dict[str, Any]:
    load_local_env()

    # LLM_* is the current naming; GLM_* is still read so an existing .env keeps
    # working without being rewritten.
    api_key = os.getenv("LLM_API_KEY") or os.getenv("GLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("GLM_BASE_URL", "")
    model = os.getenv("LLM_MODEL") or os.getenv("GLM_MODEL", "")
    provider_key = os.getenv("LLM_PROVIDER", "")

    if not provider_key:
        matched = provider_for_base_url(base_url)
        provider_key = matched.key if matched else DEFAULT_PROVIDER
    provider = get_provider(provider_key)

    try:
        temp = float(os.getenv("LLM_TEMPERATURE") or os.getenv("GLM_TEMPERATURE", "0.1"))
    except ValueError:
        temp = 0.1

    effort = _reasoning_effort_from_env()
    try:
        max_concurrency = max(1, min(int(os.getenv("LLM_MAX_CONCURRENCY", "6")), 20))
    except ValueError:
        max_concurrency = 6
    auto_concurrency = (os.getenv("LLM_AUTO_CONCURRENCY", "true").strip().lower() not in ("false", "0", "no"))
    firecrawl_pdf_mode = (os.getenv("FIRECRAWL_PDF_MODE", "auto") or "auto").strip().lower()
    if firecrawl_pdf_mode not in {"fast", "auto", "ocr"}:
        firecrawl_pdf_mode = "auto"
    return {
        "provider": provider.key,
        "provider_label": provider.label,
        "model": model or provider.default_model,
        "base_url": base_url or provider.base_url,
        "api_key": api_key,
        "reasoning_effort": effort,
        # Retained so existing callers and stored runs keep their meaning.
        "enable_reasoning": effort != "none",
        "temperature": temp,
        "max_concurrency": max_concurrency,
        "auto_concurrency": auto_concurrency,
        "firecrawl_api_key": os.getenv("FIRECRAWL_API_KEY", ""),
        "firecrawl_pdf_mode": firecrawl_pdf_mode,
        # Hosted page OCR is a separate Z.AI tool endpoint. A dedicated key can
        # be supplied without exposing it to the browser; otherwise the active
        # Z.AI gateway key is reused.
        "glm_ocr_api_key": os.getenv("GLM_OCR_API_KEY", "") or api_key,
        "glm_ocr_endpoint": os.getenv(
            "GLM_OCR_ENDPOINT", "https://api.z.ai/api/paas/v4/layout_parsing"
        ),
    }


def save_verified_settings(
    api_key: str,
    model: str,
    base_url: str,
    enable_reasoning: bool = True,
    temperature: float = 0.1,
    provider: str = "",
    reasoning_effort: str = "",
) -> None:
    """
    Persist verified settings locally.

    The API key is stored only in the project's local .env file and current
    Python process environment. .env is excluded by .gitignore.
    """
    ENV_PATH.touch(exist_ok=True)

    if not reasoning_effort:
        reasoning_effort = "high" if enable_reasoning else "none"
    if not provider:
        matched = provider_for_base_url(base_url)
        provider = matched.key if matched else DEFAULT_PROVIDER

    for key, value in {
        "LLM_PROVIDER": provider,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model,
        "LLM_BASE_URL": base_url.rstrip("/"),
        "LLM_REASONING_EFFORT": reasoning_effort,
        "LLM_TEMPERATURE": str(temperature),
    }.items():
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value


def save_runtime_settings(
    *,
    max_concurrency: int,
    auto_concurrency: bool,
    firecrawl_api_key: str = "",
    keep_firecrawl_key: bool = True,
    firecrawl_pdf_mode: str = "auto",
) -> None:
    """Persist local scheduling and corpus-connector settings without an API call."""
    ENV_PATH.touch(exist_ok=True)
    values = {
        "LLM_MAX_CONCURRENCY": str(max(1, min(int(max_concurrency), 20))),
        "LLM_AUTO_CONCURRENCY": "true" if auto_concurrency else "false",
        "FIRECRAWL_PDF_MODE": firecrawl_pdf_mode if firecrawl_pdf_mode in {"fast", "auto", "ocr"} else "auto",
    }
    if firecrawl_api_key:
        values["FIRECRAWL_API_KEY"] = firecrawl_api_key.strip()
    elif not keep_firecrawl_key:
        values["FIRECRAWL_API_KEY"] = ""
    for key, value in values.items():
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value
