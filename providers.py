"""
Provider definitions.

Every provider here speaks the OpenAI chat-completions shape, but compatible
gateways can differ in two places that matter to this project:

  * how reasoning is switched on — some use ``thinking`` while OpenRouter and
    OpenAI-compatible endpoints use ``reasoning``;
  * how prompt caching is reported back in ``usage``.

Adding a provider means adding an entry here, not editing the client.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

# OpenRouter's unified reasoning levels, in the order a UI should offer them.
# "none" disables reasoning entirely; "off" is our own label for that.
REASONING_EFFORTS = ["none", "minimal", "low", "medium", "high", "xhigh", "max"]


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    base_url: str
    #: "thinking" or "reasoning" (OpenAI-compatible / OpenRouter)
    reasoning_style: str
    default_model: str
    #: Models worth offering in the UI. Free-text entry is always allowed too.
    suggested_models: list[str] = field(default_factory=list)
    #: Extra headers some gateways want for attribution.
    extra_headers: dict[str, str] = field(default_factory=dict)
    #: Caching is automatic on these providers; no cache_control breakpoints.
    automatic_prompt_caching: bool = False
    docs: str = ""


PROVIDERS: dict[str, Provider] = {
    "openrouter": Provider(
        key="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        reasoning_style="reasoning",
        # Pin the GA snapshot for benchmark reproducibility. Mutable "latest"
        # aliases can silently change accuracy between otherwise identical runs.
        default_model="google/gemini-3.7-flash",
        suggested_models=[
            "google/gemini-3.7-flash",
            "openai/gpt-5-mini",
            "deepseek/deepseek-v4-flash-0731",
            "openai/gpt-5.4-nano",
            "mistralai/mistral-small-2603",
            "qwen/qwen3.7-plus",
            "z-ai/glm-5.3",
        ],
        extra_headers={
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Annual Report Balance Sheet Extraction",
        },
        automatic_prompt_caching=True,
        docs="https://openrouter.ai/docs",
    ),
    "openai": Provider(
        key="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        reasoning_style="reasoning",
        default_model="gpt-5.6-sol",
        suggested_models=["gpt-5.6-sol"],
        automatic_prompt_caching=True,
        docs="https://platform.openai.com/docs",
    ),
    "custom": Provider(
        key="custom",
        label="Custom OpenAI-compatible endpoint",
        base_url="",
        reasoning_style="reasoning",
        default_model="",
        docs="",
    ),
}

DEFAULT_PROVIDER = "openrouter"


def get_provider(key: str | None) -> Provider:
    return PROVIDERS.get((key or "").strip().lower(), PROVIDERS[DEFAULT_PROVIDER])


def provider_for_base_url(base_url: str) -> Provider | None:
    """Best-effort match of a saved base URL back onto a known provider."""
    url = (base_url or "").rstrip("/").lower()
    for provider in PROVIDERS.values():
        if provider.base_url and provider.base_url.rstrip("/").lower() == url:
            return provider
    return None


def reasoning_payload(provider: Provider, effort: str) -> dict[str, Any]:
    """
    Translate one reasoning setting into whatever the provider expects.

    ``effort`` is an entry from REASONING_EFFORTS. "none" means off.
    """
    effort = (effort or "medium").strip().lower()
    if effort not in REASONING_EFFORTS:
        effort = "medium"

    if provider.reasoning_style == "thinking":
        # Thinking-style gateways commonly expose an on/off switch.
        return {"thinking": {"type": "disabled" if effort == "none" else "enabled"}}

    if effort == "none":
        return {"reasoning": {"effort": "none"}}
    return {"reasoning": {"effort": effort}}


def cache_usage(usage: dict[str, Any] | None) -> dict[str, Any]:
    """
    Pull cache accounting out of a response's ``usage`` block.

    OpenRouter, OpenAI and DeepSeek report it under
    ``prompt_tokens_details``. Gateways that do not report caching simply leave
    every cache field absent.
    """
    if not isinstance(usage, dict):
        return {}
    details = usage.get("prompt_tokens_details") or {}
    out: dict[str, Any] = {}
    prompt_tokens = usage.get("prompt_tokens")
    if prompt_tokens is not None:
        out["prompt_tokens"] = prompt_tokens
    if usage.get("completion_tokens") is not None:
        out["completion_tokens"] = usage["completion_tokens"]
    if isinstance(details, dict):
        if details.get("cached_tokens") is not None:
            out["cached_tokens"] = details["cached_tokens"]
        if details.get("cache_write_tokens") is not None:
            out["cache_write_tokens"] = details["cache_write_tokens"]
    # `is not None`, not truthiness: a real cached_tokens of 0 is a measured
    # cache miss and must be reported as 0.0%, not silently omitted as though
    # the provider reported nothing. The try/except keeps an accounting helper
    # from discarding an already-paid-for extraction when a gateway sends the
    # token counts as strings.
    if out.get("cached_tokens") is not None and prompt_tokens:
        with suppress(TypeError, ValueError, ZeroDivisionError):
            out["cache_hit_rate"] = round(float(out["cached_tokens"]) / float(prompt_tokens) * 100, 1)
    if usage.get("cost") is not None:
        out["cost_usd"] = usage["cost"]
    return out
