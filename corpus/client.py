"""Small Firecrawl v2 REST client with bounded retry/backoff."""

from __future__ import annotations

import os
import random
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

import requests

try:  # Linux/macOS production and development hosts.
    import fcntl
except ImportError:  # pragma: no cover - Windows is not a supported worker host
    fcntl = None


class FirecrawlError(RuntimeError):
    pass


class FirecrawlRateGate:
    """Process-wide spacing and shared cooldown for credit-consuming calls.

    Firecrawl's Retry-After header applies to the account, not just the request
    that received the 429.  Reserving each request through one gate prevents a
    second corpus job from consuming the slot while the first job is cooling
    down.
    """

    def __init__(
        self,
        interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        state_path: Path | str | None = None,
    ) -> None:
        self.interval_seconds = max(0.0, float(interval_seconds))
        self._clock = clock
        self._sleep = sleeper
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0
        self._state_path = Path(state_path) if state_path else None
        if self._state_path:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _shared_state(self):
        """Yield the account timestamp under an inter-process file lock.

        Gunicorn runs several Python processes. A module-level lock therefore
        cannot protect an account-wide Firecrawl quota. The small state file is
        deliberately outside the corpus manifest: it is runtime coordination,
        not benchmark data.
        """
        if not self._state_path or fcntl is None:
            with self._lock:
                yield None
            return
        lock_path = self._state_path.with_suffix(self._state_path.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    next_allowed = float(self._state_path.read_text(encoding="utf-8") or 0)
                except (OSError, ValueError):
                    next_allowed = 0.0
                state = {"next_allowed_at": next_allowed}
                yield state
                temporary = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
                temporary.write_text(str(state["next_allowed_at"]), encoding="utf-8")
                temporary.replace(self._state_path)
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def wait(self) -> float:
        """Reserve the next request slot, sleeping until it is available."""
        waited = 0.0
        while True:
            with self._shared_state() as shared:
                now = self._clock()
                next_allowed = shared["next_allowed_at"] if shared is not None else self._next_allowed_at
                delay = max(0.0, next_allowed - now)
                if delay <= 0:
                    reserved = now + self.interval_seconds
                    if shared is not None:
                        shared["next_allowed_at"] = reserved
                    else:
                        self._next_allowed_at = reserved
                    return waited
            self._sleep(delay)
            waited += delay

    def defer(self, seconds: float) -> None:
        """Apply an account-wide cooldown, normally from Retry-After."""
        with self._shared_state() as shared:
            deferred = self._clock() + max(0.0, float(seconds))
            if shared is not None:
                shared["next_allowed_at"] = max(shared["next_allowed_at"], deferred)
            else:
                self._next_allowed_at = max(self._next_allowed_at, deferred)


_GLOBAL_RATE_GATE = FirecrawlRateGate(
    float(os.getenv("FIRECRAWL_REQUEST_INTERVAL_SECONDS", "12.5")),
    clock=time.time,
    state_path=Path(os.getenv("FIRECRAWL_RATE_GATE_PATH", "runs/_firecrawl_rate_gate")),
)


class FirecrawlClient:
    BASE_URL = "https://api.firecrawl.dev/v2"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 70,
        max_attempts: int = 5,
        on_retry: Callable[[int, float, str], None] | None = None,
        rate_gate: FirecrawlRateGate | None = None,
    ) -> None:
        if not api_key.strip():
            raise FirecrawlError("FIRECRAWL_API_KEY is not configured.")
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.on_retry = on_retry
        self.rate_gate = rate_gate or _GLOBAL_RATE_GATE
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "LedgerCorpusBuilder/1.0",
        })

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        last_error = "Unknown Firecrawl error"
        for attempt in range(1, self.max_attempts + 1):
            self.rate_gate.wait()
            try:
                response = self.session.post(url, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = str(exc)
                retryable = True
                retry_after = None
            else:
                body = response.json() if "json" in response.headers.get("content-type", "") else {}
                if response.ok and body.get("success", True):
                    return body
                message = body.get("error") or body.get("message") or response.text[:300]
                last_error = f"HTTP {response.status_code}: {message}"
                retryable = response.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
                retry_after = response.headers.get("Retry-After")

            if not retryable or attempt >= self.max_attempts:
                raise FirecrawlError(last_error)
            try:
                delay = float(retry_after) if retry_after else min(30.0, 2 ** attempt)
            except (TypeError, ValueError):
                delay = min(30.0, 2 ** attempt)
            delay += random.uniform(0, 0.75)
            self.rate_gate.defer(delay)
            if self.on_retry:
                self.on_retry(attempt, delay, last_error)
        raise FirecrawlError(last_error)

    def credit_usage(self) -> dict[str, Any]:
        """Validate the key without spending a crawl credit."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/team/credit-usage",
                timeout=min(self.timeout, 20),
            )
        except requests.RequestException as exc:
            raise FirecrawlError(str(exc)) from exc
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok or not body.get("success", False):
            message = body.get("error") or body.get("message") or response.text[:300]
            raise FirecrawlError(f"HTTP {response.status_code}: {message}")
        data = body.get("data") or {}
        return data if isinstance(data, dict) else {}

    def search(self, query: str, *, limit: int = 10, country: str = "US") -> list[dict[str, Any]]:
        body = self._post("search", {
            "query": query,
            "limit": max(1, min(limit, 100)),
            "sources": ["web"],
            "country": country,
            "timeout": 60000,
            "ignoreInvalidURLs": True,
        })
        data = body.get("data") or {}
        results = data.get("web") if isinstance(data, dict) else data
        return [item for item in (results or []) if isinstance(item, dict)]

    def map(self, url: str, *, search: str = "annual report", limit: int = 5000) -> list[dict[str, Any]]:
        body = self._post("map", {
            "url": url,
            "search": search,
            "sitemap": "include",
            "includeSubdomains": True,
            "ignoreQueryParameters": True,
            "limit": max(1, min(limit, 100000)),
            "timeout": 60000,
        })
        links = body.get("links") or []
        normalized = []
        for item in links:
            if isinstance(item, str):
                normalized.append({"url": item, "title": "", "description": ""})
            elif isinstance(item, dict) and item.get("url"):
                normalized.append(item)
        return normalized

    def scrape_links(self, url: str) -> list[dict[str, Any]]:
        """Read links from one official library page, preserving anchor labels.

        The links format is useful for raw destinations while markdown keeps
        the visible Japanese/English filing label that often carries the
        fiscal year even when a disclosure CDN URL does not.
        """
        body = self._post("scrape", {
            "url": url,
            "formats": ["markdown", "links"],
            "onlyMainContent": False,
            "timeout": 60000,
        })
        data = body.get("data") or {}
        if not isinstance(data, dict):
            return []

        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        markdown = str(data.get("markdown") or "")
        # URLs on Japanese IR sites often contain a parenthesized filename,
        # e.g. `report2025(print).pdf`.  Match one balanced parenthesis level
        # instead of stopping at the filename's first closing parenthesis.
        markdown_link = re.compile(
            r"\[([^\]]+)\]\((https?://(?:[^()\s]+|\([^()\s]*\))+?)\)"
        )
        for match in markdown_link.finditer(markdown):
            title, link = match.group(1).strip(), match.group(2).strip()
            # Disclosure-library links frequently use the same label (for
            # example 有価証券報告書) beneath a year heading.  Carry the nearest
            # preceding year into the candidate so discovery can assign the
            # CDN URL to the correct fiscal year.
            nearby = markdown[max(0, match.start() - 180):match.start()]
            nearby_years = re.findall(r"(?:FY\s*)?(20\d{2})(?:年|\b)", nearby, re.I)
            if nearby_years and nearby_years[-1] not in title:
                title = f"{nearby_years[-1]} {title}".strip()
            if link not in seen:
                seen.add(link)
                normalized.append({"url": link, "title": title, "description": ""})
        for item in data.get("links") or []:
            if isinstance(item, str):
                link, title = item, ""
            elif isinstance(item, dict):
                link = str(item.get("url") or "")
                title = str(item.get("text") or item.get("title") or "")
            else:
                continue
            if link and link not in seen:
                seen.add(link)
                normalized.append({"url": link, "title": title, "description": ""})
        return normalized
