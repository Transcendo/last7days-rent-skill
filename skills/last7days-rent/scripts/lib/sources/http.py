from __future__ import annotations

import hashlib
import gzip
import zlib
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..env import ensure_local_dirs, http_timeout_seconds, should_cache_raw
from ..schema import SourceFetchResult, now_iso
from ..secret_guard import sanitize_text
from ..store import write_text


USER_AGENT = "last7days-rent-skill/0.1 public-source-smoke; no-cookie; no-login"


def fetch_public_url(source_id: str, url: str) -> tuple[str, SourceFetchResult]:
    started = time.monotonic()
    result = SourceFetchResult(source_id=source_id, url=url, status="failed", fetched_at=now_iso())
    try:
        request = Request(
            _request_safe_url(url),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
            },
            method="GET",
        )
        with _urlopen_no_redirect(request, timeout=http_timeout_seconds()) as response:
            raw = response.read(2_000_000)
            raw = _decode_content(raw, response.headers.get("Content-Encoding"))
            text = raw.decode(_charset(response.headers.get_content_charset()), errors="replace")
            result.http_status = response.status
            result.url = response.geturl()
            result.status = "ok"
            result.warning = _detect_blocking(result.url, text, response.status)
    except HTTPError as exc:
        text = exc.read(200_000).decode("utf-8", errors="replace")
        result.http_status = exc.code
        result.url = exc.geturl()
        result.warning = _detect_blocking(result.url, text, exc.code) or f"http_{exc.code}"
        result.status = "blocked" if exc.code in {403, 429} else "failed"
    except URLError as exc:
        text = ""
        result.warning = f"network_error: {exc.reason}"
        result.status = "failed"
    except TimeoutError:
        text = ""
        result.warning = "timeout"
        result.status = "failed"
    except (UnicodeError, ValueError) as exc:
        text = ""
        result.warning = f"invalid_url: {exc}"
        result.status = "failed"
    result.elapsed_ms = int((time.monotonic() - started) * 1000)
    if result.warning and any(token in result.warning for token in ["captcha", "login", "http_403", "http_429"]):
        result.status = "blocked"
    if should_cache_raw() and text:
        paths = ensure_local_dirs()
        name = hashlib.sha1(f"{source_id}:{url}".encode()).hexdigest()[:16]
        raw_path = paths.cache_dir / f"{source_id}-{name}.html"
        write_text(raw_path, sanitize_text(text))
        result.raw_path = str(raw_path)
    return text, result


def _request_safe_url(url: str) -> str:
    parts = urlsplit(url)
    netloc = parts.netloc.encode("idna").decode("ascii") if parts.netloc else ""
    path = quote(parts.path, safe="/%:@")
    query = quote(parts.query, safe="=&%/:+?,")
    fragment = quote(parts.fragment, safe="%/:+?,")
    return urlunsplit((parts.scheme, netloc, path, query, fragment))


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, ANN001
        return None


def _urlopen_no_redirect(request: Request, timeout: float):
    opener = build_opener(_NoRedirectHandler)
    return opener.open(request, timeout=timeout)


def _charset(charset: str | None) -> str:
    return charset or "utf-8"


def _decode_content(raw: bytes, encoding: str | None) -> bytes:
    if not encoding:
        return raw
    lowered = encoding.lower()
    if "gzip" in lowered:
        return gzip.decompress(raw)
    if "deflate" in lowered:
        return zlib.decompress(raw)
    return raw


def _detect_blocking(url: str, text: str, status: int | None) -> str | None:
    lowered_url = url.lower()
    lowered = text.lower()
    if status == 403:
        return "http_403_blocked"
    if status == 429:
        return "http_429_rate_limited"
    if "captcha" in lowered_url or "captcha" in lowered or "验证码" in text or "安全验证" in text:
        return "captcha_detected"
    if "login" in lowered_url or "登录" in text and "租房" not in text[:500]:
        return "login_wall_detected"
    if status and status >= 500:
        return f"http_{status}"
    return None
