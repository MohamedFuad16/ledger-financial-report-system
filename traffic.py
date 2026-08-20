"""Private visit telemetry persisted in Upstash and delivered through AWS SES."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


LOGGER = logging.getLogger(__name__)
UPSTASH_TIMEOUT_SECONDS = 5
VISIT_RETENTION = 2_000
SESSION_TTL_SECONDS = 6 * 60 * 60
MAX_FIELD_LENGTH = 1_000

_SES_CLIENTS: dict[str, Any] = {}
_SES_CLIENTS_LOCK = threading.Lock()


def _clean(value: Any, *, limit: int = MAX_FIELD_LENGTH) -> str:
    return " ".join(str(value or "").split())[:limit]


def _upstash_command(command: list[Any]) -> Any:
    url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if not url or not token:
        raise RuntimeError("Upstash visit tracking is not configured.")
    http_request = Request(
        url,
        data=json.dumps(command, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(http_request, timeout=UPSTASH_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("Upstash visit tracking is temporarily unavailable.") from exc
    if payload.get("error"):
        raise RuntimeError("Upstash rejected the visit event.")
    return payload.get("result")


def _upstash_pipeline(commands: list[list[Any]]) -> list[Any]:
    url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if not url or not token:
        raise RuntimeError("Upstash visit tracking is not configured.")
    http_request = Request(
        f"{url}/pipeline",
        data=json.dumps(commands, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(http_request, timeout=UPSTASH_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("Upstash visit tracking is temporarily unavailable.") from exc
    if not isinstance(payload, list) or any(item.get("error") for item in payload):
        raise RuntimeError("Upstash rejected the visit event.")
    return [item.get("result") for item in payload]


def _ses_client(region: str):
    with _SES_CLIENTS_LOCK:
        if region not in _SES_CLIENTS:
            _SES_CLIENTS[region] = boto3.client(
                "sesv2",
                region_name=region,
                config=Config(
                    retries={"total_max_attempts": 3, "mode": "adaptive"},
                    connect_timeout=4,
                    read_timeout=8,
                ),
            )
        return _SES_CLIENTS[region]


def _email_visit(event: dict[str, str]) -> bool:
    recipient = os.environ.get("TRAFFIC_NOTIFY_EMAIL", "").strip()
    sender = os.environ.get("TRAFFIC_FROM_EMAIL", "").strip() or recipient
    if not recipient or not sender:
        return False

    region = os.environ.get("AWS_REGION", "ap-northeast-1").strip()
    accessed_at = datetime.fromisoformat(event["accessed_at"]).astimezone(ZoneInfo("Asia/Tokyo"))
    subject = f"Ledger visit · {accessed_at:%Y-%m-%d %H:%M:%S JST}"
    fields = [
        ("Access time", accessed_at.strftime("%Y-%m-%d %H:%M:%S JST")),
        ("Path", event["path"]),
        ("Referrer", event["referrer"] or "Direct / unavailable"),
        ("IP", event["ip"] or "Unavailable"),
        ("Locale", event["locale"] or "Unavailable"),
        ("Time zone", event["timezone"] or "Unavailable"),
        ("Viewport", event["viewport"] or "Unavailable"),
        ("User agent", event["user_agent"] or "Unavailable"),
        ("Event ID", event["event_id"]),
    ]
    body = "A new browser session visited Ledger.\n\n" + "\n".join(
        f"{label}: {value}" for label, value in fields
    )
    try:
        _ses_client(region).send_email(
            FromEmailAddress=sender,
            Destination={"ToAddresses": [recipient]},
            Content={"Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            }},
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")
        LOGGER.warning("Visit email delivery failed with SES code %s.", error_code)
        return False
    return True


def _notify_async(event: dict[str, str]) -> None:
    threading.Thread(target=_email_visit, args=(event,), daemon=True, name="visit-email").start()


def record_visit(payload: dict[str, Any], *, remote_ip: str) -> dict[str, Any]:
    """Store one event per browser session and enqueue its private email notification."""
    session_id = _clean(payload.get("session_id"), limit=128)
    if len(session_id) < 12:
        raise ValueError("A valid browser session id is required.")

    ip = _clean(remote_ip, limit=80)
    session_digest = hashlib.sha256(f"{session_id}|{ip}".encode("utf-8")).hexdigest()
    first_seen = _upstash_command([
        "SET",
        f"ledger:traffic:session:{session_digest}",
        "1",
        "EX",
        SESSION_TTL_SECONDS,
        "NX",
    ])
    if first_seen is None:
        return {"recorded": False, "duplicate": True, "email_queued": False}

    accessed_at = datetime.now(timezone.utc).isoformat()
    event = {
        "event_id": uuid.uuid4().hex,
        "accessed_at": accessed_at,
        "path": _clean(payload.get("path"), limit=300) or "/",
        "referrer": _clean(payload.get("referrer")),
        "ip": ip,
        "locale": _clean(payload.get("locale"), limit=80),
        "timezone": _clean(payload.get("timezone"), limit=100),
        "viewport": _clean(payload.get("viewport"), limit=80),
        "user_agent": _clean(payload.get("user_agent")),
    }
    day_key = accessed_at[:10]
    _upstash_pipeline([
        ["LPUSH", "ledger:traffic:visits", json.dumps(event, ensure_ascii=False)],
        ["LTRIM", "ledger:traffic:visits", 0, VISIT_RETENTION - 1],
        ["INCR", "ledger:traffic:count"],
        ["HINCRBY", "ledger:traffic:daily", day_key, 1],
    ])
    email_queued = bool(os.environ.get("TRAFFIC_NOTIFY_EMAIL", "").strip())
    if email_queued:
        _notify_async(event)
    return {"recorded": True, "duplicate": False, "email_queued": email_queued}
