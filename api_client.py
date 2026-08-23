import json
import time
from pathlib import Path
from typing import Any

import requests

from providers import cache_usage, get_provider, reasoning_payload
from ratelimit import LIMITER, retry_after_seconds


class GLMError(RuntimeError):
    pass


class RateLimitedError(GLMError):
    """HTTP 429 from the provider, after retries were exhausted."""


class RequestTimedOut(GLMError):
    """The provider produced no response within the client timeout."""


class QuotaExhaustedError(GLMError):
    """
    The account's usage allowance is spent, not merely throttled.

    Z.AI returns this as an HTTP 429 like any other rate limit, but retrying is
    pointless: nothing succeeds until the window resets. It is raised
    immediately, without retries, so a batch stops instead of grinding every
    remaining file through four useless attempts.
    """


# Provider codes / phrases that mean "allowance spent", not "slow down".
_QUOTA_MARKERS = ("1308", "usage limit reached", "quota", "insufficient balance", "credit")


def _quota_message(body: Any) -> str | None:
    """Return the provider's quota message if this 429 is an exhausted allowance."""
    if not isinstance(body, dict):
        return None
    error = body.get("error", body)
    text = json.dumps(error) if isinstance(error, dict) else str(error)
    lowered = text.lower()
    if any(marker in lowered for marker in _QUOTA_MARKERS):
        if isinstance(error, dict):
            return str(error.get("message") or text)
        return text
    return None


def _send_once(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int,
    extra_headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], float, int, Any]:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    started = time.perf_counter()

    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Language": "en-US,en",
                **(extra_headers or {}),
            },
            json=payload,
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise RequestTimedOut(f"Request timed out after {timeout} seconds.") from exc
    except requests.RequestException as exc:
        raise GLMError(f"Network error: {exc}") from exc

    elapsed = time.perf_counter() - started

    try:
        body = response.json()
    except ValueError:
        body = {"_raw_text": response.text}

    return body, elapsed, response.status_code, response.headers


def _post_json(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int,
    max_retries: int = 4,
    on_retry=None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], float, int]:
    """
    Send one chat completion, honouring the shared adaptive concurrency gate.

    A 429 is not an error the caller has to handle: the limiter halves the
    permitted concurrency, we wait the provider's Retry-After (or a backoff with
    jitter), and try again. Only when the retries run out does it surface.
    """
    attempt = 0
    timeout_attempts = 0
    total_elapsed = 0.0

    while True:
        LIMITER.acquire()
        attempt_started = time.perf_counter()
        try:
            body, elapsed, status, headers = _send_once(
                api_key=api_key, base_url=base_url, payload=payload,
                timeout=timeout, extra_headers=extra_headers,
            )
        except RequestTimedOut:
            # Congested reasoning endpoints occasionally sit on one request
            # far beyond their normal latency; one fresh attempt usually
            # succeeds. A second timeout is surfaced — each one already cost
            # the full client timeout, so looping would multiply the stall.
            timeout_attempts += 1
            total_elapsed += time.perf_counter() - attempt_started
            if timeout_attempts > 1:
                raise
            if on_retry:
                on_retry(timeout_attempts, 1.0)
            continue
        finally:
            LIMITER.release()

        total_elapsed += elapsed
        LIMITER.note_headers(headers)

        if status == 429:
            quota = _quota_message(body)
            if quota:
                # Allowance spent: retrying cannot help.
                raise QuotaExhaustedError(quota)
            attempt += 1
            delay = LIMITER.note_throttled(retry_after_seconds(headers, body))
            if attempt > max_retries:
                raise RateLimitedError(
                    f"HTTP 429 after {max_retries} retries: {body.get('error', body) if isinstance(body, dict) else body}"
                )
            if on_retry:
                on_retry(attempt, delay)
            time.sleep(delay)
            total_elapsed += delay
            continue

        if status >= 500 and attempt < max_retries:
            attempt += 1
            delay = min(30.0, 2.0 * (2 ** (attempt - 1)))
            if on_retry:
                on_retry(attempt, delay)
            time.sleep(delay)
            total_elapsed += delay
            continue

        if status < 200 or status >= 300:
            message = body.get("error", body) if isinstance(body, dict) else body
            raise GLMError(f"HTTP {status}: {message}")

        LIMITER.note_success()
        return body, total_elapsed, status


def test_api_key(
    *,
    api_key: str,
    model: str,
    base_url: str,
    timeout: int = 30,
    provider: str = "",
) -> tuple[bool, str, float]:
    """
    Short authentication/model test.

    Nothing is persisted until this call succeeds.
    """
    if not api_key.strip():
        return False, "API key is empty.", 0.0

    prov = get_provider(provider or None)
    payload = {
        "model": model.strip(),
        "messages": [
            {
                "role": "user",
                "content": "API connection test. Reply with exactly: OK",
            }
        ],
        "stream": False,
        "max_tokens": 16,
        "temperature": 0,
        # Reasoning off for the probe: it only needs to prove auth and model id.
        **reasoning_payload(prov, "none"),
    }

    try:
        body, elapsed, _ = _post_json(
            api_key=api_key.strip(),
            base_url=base_url.strip(),
            payload=payload,
            timeout=timeout,
            max_retries=1,
            extra_headers=prov.extra_headers,
        )
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            return False, "API responded but returned empty assistant content.", elapsed
        return True, content.strip(), elapsed
    except (KeyError, IndexError, TypeError):
        return False, "API responded, but the response shape was unexpected.", 0.0
    except GLMError as exc:
        return False, str(exc), 0.0


def run_extraction(
    *,
    api_key: str,
    model: str,
    base_url: str,
    system_prompt: str,
    user_prompt: str,
    run_dir: Path,
    enable_reasoning: bool = True,
    temperature: float = 0.0,
    timeout: int = 600,
    on_retry=None,
    provider: str = "",
    reasoning_effort: str = "",
    messages: list[dict[str, str]] | None = None,
    artifact_suffix: str = "",
    session_id: str = "",
) -> tuple[dict[str, Any], float]:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    prov = get_provider(provider or None)
    effort = reasoning_effort or ("high" if enable_reasoning else "none")

    payload = {
        "model": model,
        "messages": messages or [
            # System first, then user. Both begin with content identical on every
            # request, which is what a prefix cache can reuse.
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": float(temperature),
        "response_format": {"type": "json_object"},
        **reasoning_payload(prov, effort),
    }
    if prov.automatic_prompt_caching:
        # OpenRouter returns per-request cost and cache accounting when asked.
        payload["usage"] = {"include": True}
    if session_id and prov.key == "openrouter":
        # Sticky routing: follow-up calls of one run (repair, evidence retry)
        # should land on the provider endpoint that already holds the warm
        # prefix cache.
        payload["session_id"] = session_id

    # Save request details without any Authorization header or API key.
    request_record = {
        "endpoint": endpoint,
        "provider": prov.key,
        "model": model,
        "reasoning_effort": effort,
        "temperature": float(temperature),
        "payload": payload,
    }
    suffix = artifact_suffix if artifact_suffix.startswith("_") or not artifact_suffix else f"_{artifact_suffix}"
    (run_dir / f"request{suffix}.json").write_text(
        json.dumps(request_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        body, elapsed, _ = _post_json(
            api_key=api_key,
            base_url=base_url,
            payload=payload,
            timeout=timeout,
            on_retry=on_retry,
            extra_headers=prov.extra_headers,
        )
    except GLMError as exc:
        # Keep a record of the failure next to the request that caused it.
        (run_dir / f"raw_response{suffix}.json").write_text(
            json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        raise

    (run_dir / f"raw_response{suffix}.json").write_text(
        json.dumps(body, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return body, elapsed


def response_usage(raw_response: dict[str, Any]) -> dict[str, Any]:
    """Token and prompt-cache accounting from a completed response."""
    return cache_usage((raw_response or {}).get("usage"))


def parse_assistant_json(raw_response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = raw_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GLMError(
            "Response did not contain choices[0].message.content."
        ) from exc

    if isinstance(content, dict):
        return content

    if not isinstance(content, str) or not content.strip():
        raise GLMError("Model returned empty assistant content.")

    text = content.strip()

    # Deterministic clean-up only. Never issue an automatic repair LLM call.
    text = _strip_code_fence(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Some models prepend a sentence before the object despite the contract.
    # Recovering the outermost JSON value is still deterministic.
    salvaged = _first_json_value(text)
    if salvaged is not None:
        return salvaged

    raise GLMError(
        "Model output was not valid JSON. The original provider response "
        "is preserved in raw_response.json."
    )


def _strip_code_fence(text: str) -> str:
    """Remove a surrounding ```/```json fence if the model added one."""
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _first_json_value(text: str) -> Any:
    """
    Return the first balanced JSON object or array embedded in ``text``.

    Every candidate opening bracket is tried, not just the first one, so a stray
    brace in a prose preamble does not hide the real payload behind it.
    """
    for opener, closer in (("{", "}"), ("[", "]")):
        for start in (i for i, ch in enumerate(text) if ch == opener):
            value = _balanced_slice(text, start, opener, closer)
            if value is not None:
                return value
    return None


def _balanced_slice(text: str, start: int, opener: str, closer: str) -> Any:
    """Parse the bracket-balanced slice beginning at ``start``, or return None."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:index + 1])
                except json.JSONDecodeError:
                    return None
    return None
