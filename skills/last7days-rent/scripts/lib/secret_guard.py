from __future__ import annotations

import re
from typing import Mapping


SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "authorization": re.compile(r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+"),
    "set_cookie": re.compile(r"(?i)\bSet-Cookie\s*:\s*[^;\n]+"),
    "cookie": re.compile(r"(?i)\bCookie\s*:\s*[^;\n]+"),
    "token": re.compile(r"(?i)\b(?:access[_-]?token|refresh[_-]?token|id[_-]?token|token)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}"),
    "secret": re.compile(r"(?i)\b(?:secret|client_secret|api_key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}"),
    "session": re.compile(r"(?i)\b(?:sessionid|session_id|sid)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}"),
}


def secret_violations(text: str | None) -> list[str]:
    if not text:
        return []
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def assert_no_secrets(text: str | None) -> None:
    violations = secret_violations(text)
    if violations:
        raise ValueError(f"output contains credential-like fields: {', '.join(violations)}")


def sanitize_text(text: str | None) -> str:
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS.values():
        sanitized = pattern.sub("[blocked-credential]", sanitized)
    return sanitized


def scrub_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in (headers or {}).items():
        if key.lower() in {"authorization", "cookie", "set-cookie", "x-api-key"}:
            continue
        safe[key] = sanitize_text(value)
    return safe
