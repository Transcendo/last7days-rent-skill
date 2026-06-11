from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from ..env import http_timeout_seconds


class ProviderHTTPError(Exception):
    def __init__(self, status_code: int | None, body: str | None = None, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.body = body or ""
        self.headers = headers or {}
        super().__init__(f"provider HTTP error: {status_code}")


def clamp_int(value: int, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(int(value), maximum))


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")])
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def domain_for_url(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def stable_lead_id(provider: str, url: str, query: str) -> str:
    payload = f"{provider}|{canonical_url(url)}|{query}".encode("utf-8")
    return f"lead-{provider}-{hashlib.sha1(payload).hexdigest()[:12]}"


def utc_window(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=max(1, int(days)))
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int | None, int, dict[str, str]]:
    if params:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode(params, doseq=True)}"
    body = None
    request_headers = dict(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request_headers.setdefault("Accept", "application/json")
    req = Request(url, data=body, headers=request_headers, method=method.upper())
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=http_timeout_seconds()) as response:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}, response.status, elapsed_ms, dict(response.headers.items())
    except HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        body_text = exc.read().decode("utf-8", errors="replace")
        raise ProviderHTTPError(exc.code, body_text, dict(exc.headers.items())) from exc
    except URLError as exc:
        raise ProviderHTTPError(None, str(exc), {}) from exc


def compact_text(value: str | None, limit: int = 500) -> str | None:
    if not value:
        return None
    text = " ".join(str(value).split())
    return text[:limit] if len(text) > limit else text
