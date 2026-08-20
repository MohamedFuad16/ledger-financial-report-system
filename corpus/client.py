"""Small Firecrawl v2 REST client with bounded retry/backoff."""

from __future__ import annotations

import random
import time
from typing import Any, Callable

import requests


class FirecrawlError(RuntimeError):
    pass


class FirecrawlClient:
    BASE_URL = "https://api.firecrawl.dev/v2"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 70,
        max_attempts: int = 5,
        on_retry: Callable[[int, float, str], None] | None = None,
    ) -> None:
        if not api_key.strip():
            raise FirecrawlError("FIRECRAWL_API_KEY is not configured.")
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.on_retry = on_retry
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
            if self.on_retry:
                self.on_retry(attempt, delay, last_error)
            time.sleep(delay)
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
