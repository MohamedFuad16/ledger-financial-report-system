"""
Adaptive concurrency and rate-limit handling.

Some OpenAI-compatible gateways do not publish fixed RPM/TPM numbers, and
limits can change dynamically by plan tier and load. This module therefore
does not hardcode a limit. It:

  1. reads any rate-limit headers the provider actually returns and records them,
  2. caps in-flight requests with a semaphore whose size can shrink and grow,
  3. halves the permitted concurrency on an HTTP 429 and retries with
     exponential backoff + jitter,
  4. recovers one permit at a time after a run of clean responses.

The observed state is exposed to the UI so the numbers shown are measured, never
guessed.
"""

from __future__ import annotations

import random
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

# Header names different gateways use for the same information.
_LIMIT_HEADERS = {
    "requests_limit": (
        "x-ratelimit-limit-requests",
        "x-ratelimit-limit",
        "ratelimit-limit",
    ),
    "requests_remaining": (
        "x-ratelimit-remaining-requests",
        "x-ratelimit-remaining",
        "ratelimit-remaining",
    ),
    "tokens_limit": ("x-ratelimit-limit-tokens",),
    "tokens_remaining": ("x-ratelimit-remaining-tokens",),
    "reset_seconds": (
        "x-ratelimit-reset-requests",
        "x-ratelimit-reset",
        "ratelimit-reset",
        "retry-after",
    ),
}


def _parse_duration(value: str) -> float | None:
    """Parse "30", "30s", "1m30s", "500ms" into seconds."""
    text = str(value).strip().lower()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    total = 0.0
    matched = False
    for amount, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(ms|s|m|h)", text):
        matched = True
        seconds = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}[unit]
        total += float(amount) * seconds
    return total if matched else None


@dataclass
class RateLimitState:
    """What we have actually observed about the provider's limits."""

    max_concurrency: int = 6
    permitted_concurrency: int = 6
    observed_headers: dict[str, Any] = field(default_factory=dict)
    throttle_events: int = 0
    last_throttle_at: float | None = None
    last_retry_after: float | None = None
    consecutive_ok: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_concurrency": self.max_concurrency,
            "permitted_concurrency": self.permitted_concurrency,
            "observed_headers": dict(self.observed_headers),
            "throttle_events": self.throttle_events,
            "last_throttle_at": self.last_throttle_at,
            "last_retry_after": self.last_retry_after,
            "source": "measured from provider responses; no fixed provider limit configured",
        }


class AdaptiveLimiter:
    """
    A resizable concurrency gate.

    ``acquire``/``release`` behave like a semaphore, except the number of permits
    can be reduced after a 429 and restored after sustained success.
    """

    def __init__(self, concurrency: int = 6) -> None:
        self._condition = threading.Condition()
        self._in_flight = 0
        self.state = RateLimitState(max_concurrency=concurrency, permitted_concurrency=concurrency)
        self._paused_until = 0.0

    # -- gate ---------------------------------------------------------------

    def acquire(self) -> None:
        with self._condition:
            while True:
                wait_for = self._paused_until - time.monotonic()
                if wait_for <= 0 and self._in_flight < self.state.permitted_concurrency:
                    self._in_flight += 1
                    return
                self._condition.wait(timeout=max(wait_for, 0.05) if wait_for > 0 else None)

    def release(self) -> None:
        with self._condition:
            self._in_flight = max(0, self._in_flight - 1)
            self._condition.notify_all()

    # -- feedback -----------------------------------------------------------

    def note_headers(self, headers: Any) -> None:
        """Record whatever rate-limit headers the provider returned."""
        if not headers:
            return
        lowered = {str(k).lower(): v for k, v in dict(headers).items()}
        found = {}
        for label, candidates in _LIMIT_HEADERS.items():
            for name in candidates:
                if name in lowered:
                    found[label] = lowered[name]
                    break
        if found:
            with self._condition:
                self.state.observed_headers.update(found)

    def note_success(self) -> None:
        """A clean response: slowly return permits taken away by a throttle."""
        with self._condition:
            self.state.consecutive_ok += 1
            if (
                self.state.consecutive_ok >= 4
                and self.state.permitted_concurrency < self.state.max_concurrency
            ):
                self.state.permitted_concurrency += 1
                self.state.consecutive_ok = 0
                self._condition.notify_all()

    def note_throttled(self, retry_after: float | None = None) -> float:
        """
        A 429. Halve the permitted concurrency, pause new starts, and return how
        long the caller should sleep before retrying.
        """
        with self._condition:
            self.state.throttle_events += 1
            self.state.last_throttle_at = time.time()
            self.state.consecutive_ok = 0
            self.state.permitted_concurrency = max(1, self.state.permitted_concurrency // 2)

            delay = retry_after if retry_after and retry_after > 0 else 0.0
            if delay <= 0:
                # No Retry-After header: back off on the number of throttles seen.
                delay = min(60.0, 2.0 * (2 ** min(self.state.throttle_events - 1, 5)))
            delay += random.uniform(0, 1.0)  # jitter, so retries do not resynchronize

            self.state.last_retry_after = round(delay, 2)
            self._paused_until = max(self._paused_until, time.monotonic() + delay)
            self._condition.notify_all()
            return delay

    def resize(self, concurrency: int) -> None:
        with self._condition:
            concurrency = max(1, int(concurrency))
            self.state.max_concurrency = concurrency
            self.state.permitted_concurrency = concurrency
            self._condition.notify_all()

    def snapshot(self) -> dict[str, Any]:
        with self._condition:
            data = self.state.snapshot()
            data["in_flight"] = self._in_flight
            paused = self._paused_until - time.monotonic()
            data["paused_for_seconds"] = round(paused, 2) if paused > 0 else 0
            return data


# One limiter per process: every strategy and every batch shares the same quota.
LIMITER = AdaptiveLimiter()


def retry_after_seconds(headers: Any, body: Any) -> float | None:
    """Extract a retry delay from a 429 response, if it carries one."""
    if headers:
        lowered = {str(k).lower(): v for k, v in dict(headers).items()}
        for name in ("retry-after", "x-ratelimit-reset-requests", "x-ratelimit-reset"):
            if name in lowered:
                parsed = _parse_duration(lowered[name])
                if parsed is not None:
                    return parsed
    if isinstance(body, dict):
        text = str(body)
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:seconds?|s)\b", text, re.I)
        if match:
            return float(match.group(1))
    return None


def estimate_batch_plan(
    files: list[dict[str, Any]],
    concurrency: int,
    auto_adjust: bool = True,
) -> dict[str, Any]:
    """
    Pre-flight estimate for a batch, from local information only.

    ``files`` is a list of ``{"name", "pages", "approx_tokens"}``. Returns the
    projected input load and a recommended concurrency, plus any advisories to
    show before the user commits to a paid run.
    """
    total_tokens = sum(int(f.get("approx_tokens") or 0) for f in files)
    total_pages = sum(int(f.get("pages") or 0) for f in files)
    snapshot = LIMITER.snapshot()

    advisories: list[str] = []
    recommended = max(1, min(concurrency, snapshot["max_concurrency"], len(files) or 1))
    if auto_adjust and files:
        average_tokens = total_tokens / len(files)
        # Large whole-report prompts need more headroom per request. This is a
        # scheduling heuristic, not an invented provider limit; 429 feedback
        # below remains authoritative and shrinks the live gate immediately.
        load_ceiling = (
            2
            if average_tokens >= 180_000
            else 3
            if average_tokens >= 120_000
            else 4
            if average_tokens >= 80_000
            else concurrency
        )
        recommended = max(1, min(recommended, load_ceiling))
        if recommended < min(concurrency, len(files)):
            advisories.append(
                f"Adaptive scheduling reduced the initial batch width to {recommended} "
                f"for ~{average_tokens:,.0f} tokens per report."
            )

    if snapshot["throttle_events"]:
        recommended = max(1, min(recommended, snapshot["permitted_concurrency"]))
        advisories.append(
            f"This endpoint returned HTTP 429 {snapshot['throttle_events']} time(s) in this session. "
            f"Concurrency is currently held at {snapshot['permitted_concurrency']}."
        )

    tokens_limit = snapshot["observed_headers"].get("tokens_limit")
    if tokens_limit:
        try:
            if total_tokens > float(tokens_limit):
                advisories.append(
                    f"Estimated {total_tokens:,} input tokens exceeds the observed per-window "
                    f"token limit of {float(tokens_limit):,.0f}. Requests will be throttled and retried."
                )
        except (TypeError, ValueError):
            pass
    if len(files) > recommended:
        waves = -(-len(files) // recommended)
        advisories.append(f"{len(files)} files at concurrency {recommended} runs as {waves} wave(s).")

    return {
        "files": files,
        "file_count": len(files),
        "total_pages": total_pages,
        "total_approx_tokens": total_tokens,
        "requested_concurrency": concurrency,
        "recommended_concurrency": recommended,
        "auto_adjust": auto_adjust,
        "advisories": advisories,
        "rate_limit": snapshot,
    }
