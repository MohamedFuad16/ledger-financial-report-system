"""
Provider definitions.

Every provider here speaks the OpenAI chat-completions shape, but they differ in
two places that matter to this project:

  * how reasoning is switched on — Z.AI uses ``thinking``, OpenRouter and
    OpenAI-compatible endpoints use ``reasoning``;
  * how prompt caching is reported back in ``usage``.

Adding a provider means adding an entry here, not editing the client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# OpenRouter's unified reasoning levels, in the order a UI should offer them.
# "none" disables reasoning entirely; "off" is our own label for that.
REASONING_EFFORTS = ["none", "minimal", "low", "medium", "high", "xhigh", "max"]


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    base_url: str
    #: "thinking" (Z.AI) or "reasoning" (OpenAI-compatible / OpenRouter)
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
    "zai": Provider(
        key="zai",
        label="Z.AI (GLM)",
        base_url="https://api.z.ai/api/paas/v4",
        reasoning_style="thinking",
        default_model="glm-5.3",
        suggested_models=["glm-5.3", "glm-5.2"],
        docs="https://docs.z.ai",
    ),
    "zai-coding": Provider(
        key="zai-coding",
        label="Z.AI Coding Plan endpoint",
        base_url="https://api.z.ai/api/coding/paas/v4",
        reasoning_style="thinking",
        default_model="glm-5.3",
        suggested_models=["glm-5.3"],
        docs="https://docs.z.ai",
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


def provider_for_base_url(base_url: str) -> Optional[Provider]:
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
        # Z.AI only has on/off.
        return {"thinking": {"type": "disabled" if effort == "none" else "enabled"}}

    if effort == "none":
        return {"reasoning": {"effort": "none"}}
    return {"reasoning": {"effort": effort}}


def cache_usage(usage: dict[str, Any] | None) -> dict[str, Any]:
    """
    Pull cache accounting out of a response's ``usage`` block.

    OpenRouter, OpenAI and DeepSeek all report it under
    ``prompt_tokens_details``; Z.AI does not report it at all, in which case
    every field is simply absent.
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
    if out.get("cached_tokens") and prompt_tokens:
        out["cache_hit_rate"] = round(out["cached_tokens"] / prompt_tokens * 100, 1)
    if usage.get("cost") is not None:
        out["cost_usd"] = usage["cost"]
    return out
