from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .env import ensure_local_dirs, get_paths
from .listing_pool import empty_pool, load_pool, merge_items, save_pool
from .privacy import GROUP_RE, NAME_WITH_LABEL_RE, PHONE_RE, WECHAT_RE, public_text_violations
from .store import read_json


REQUIRED_ITEM_FIELDS = [
    "evidence_id",
    "batch_id",
    "query_id",
    "query",
    "collected_via",
    "source_url",
    "source_name",
    "source_type",
    "page_opened",
    "title",
    "snippet",
    "raw_excerpt",
    "observed_at",
    "visible_fields",
]


def load_evidence(path: str | Path) -> dict[str, Any]:
    data = read_json(Path(path))
    if not isinstance(data, dict):
        raise ValueError("evidence JSON must be an object")
    return data


def validate_evidence(data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(data.get("query_context"), dict):
        errors.append({"path": "query_context", "message": "required object"})
    if "runtime_meta" in data and not isinstance(data["runtime_meta"], dict):
        errors.append({"path": "runtime_meta", "message": "must be object when present"})
    if "execution_summary" in data and not isinstance(data["execution_summary"], dict):
        errors.append({"path": "execution_summary", "message": "must be object when present"})
    items = data.get("items")
    if not isinstance(items, list):
        errors.append({"path": "items", "message": "required array"})
        return errors
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append({"path": f"items[{idx}]", "message": "required object"})
            continue
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item or item[field] in (None, ""):
                errors.append({"path": f"items[{idx}].{field}", "message": "required"})
        url = item.get("source_url")
        if url and not _valid_url(str(url)):
            errors.append({"path": f"items[{idx}].source_url", "message": "invalid URL"})
        if item.get("visible_fields") is not None and not isinstance(item.get("visible_fields"), dict):
            errors.append({"path": f"items[{idx}].visible_fields", "message": "must be object"})
        if item.get("normalized_fields") is not None and not isinstance(item.get("normalized_fields"), dict):
            errors.append({"path": f"items[{idx}].normalized_fields", "message": "must be object"})
        if "contact_path" in item and item["contact_path"] is not None and not isinstance(item["contact_path"], dict):
            errors.append({"path": f"items[{idx}].contact_path", "message": "must be object when present"})
        if item.get("source_domain") and url:
            source_domain = str(item["source_domain"]).lower()
            url_domain = urlparse(str(url)).netloc.lower()
            if source_domain not in {url_domain, url_domain.removeprefix("www.")} and not url_domain.endswith(f".{source_domain}"):
                errors.append({"path": f"items[{idx}].source_domain", "message": "does not match source_url domain"})
        for violation in _privacy_violations(item):
            errors.append({"path": f"items[{idx}].privacy", "message": violation})
        if _is_candidate_l1(item):
            for message in _l1_validation_errors(item):
                errors.append({"path": f"items[{idx}].listing_candidate_status", "message": message})
    return errors


def validate_evidence_file(path: str | Path) -> list[dict[str, str]]:
    return validate_evidence(load_evidence(path))


def ingest_evidence_file(path: str | Path, pool_path: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    ensure_local_dirs()
    data = load_evidence(path)
    errors = validate_evidence(data)
    if errors:
        raise ValueError(json.dumps({"errors": errors}, ensure_ascii=False))
    output = Path(pool_path).expanduser() if pool_path else get_paths().pools_dir / "jd-hq-beijing.listing-pool.json"
    current = load_pool(output) if output.exists() else empty_pool()
    pool = merge_items(current, data)
    save_pool(output, pool)
    return pool, output


def _valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_candidate_l1(item: dict[str, Any]) -> bool:
    return item.get("listing_candidate_status") == "candidate_l1" or item.get("trust_level_hint") == "L1"


def _l1_validation_errors(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not item.get("page_opened"):
        errors.append("candidate_l1 requires page_opened=true")
    if _blocked_url_class(item):
        errors.append("candidate_l1 cannot be login/captcha/app-wall/search-result only")
    for field in ["source_url", "observed_at", "raw_excerpt"]:
        if not item.get(field):
            errors.append(f"candidate_l1 requires {field}")
    visible_count = _visible_core_field_count(item)
    if visible_count < 3:
        errors.append(f"candidate_l1 requires at least 3 visible core fields; got {visible_count}")
    return errors


def _blocked_url_class(item: dict[str, Any]) -> bool:
    url_class = str(item.get("url_class") or "").lower()
    title = str(item.get("title") or "").lower()
    return any(token in url_class for token in ["login", "captcha", "app_wall", "app-wall", "search_result"]) or any(
        token in title for token in ["验证码", "登录", "app下载", "app 下载"]
    )


def _visible_core_field_count(item: dict[str, Any]) -> int:
    visible = item.get("visible_fields") if isinstance(item.get("visible_fields"), dict) else {}
    normalized = item.get("normalized_fields") if isinstance(item.get("normalized_fields"), dict) else {}
    checks = [
        bool(normalized.get("price_monthly") or visible.get("price_text")),
        bool(visible.get("community") or visible.get("district_hint")),
        bool(normalized.get("area_sqm") or visible.get("area_text") or normalized.get("bedrooms") or visible.get("layout_text")),
        isinstance(item.get("contact_path"), dict) and bool(item["contact_path"].get("entry_url") or item["contact_path"].get("value")),
        bool(visible.get("published_at") or visible.get("updated_at") or visible.get("freshness_text")),
    ]
    return sum(1 for ok in checks if ok)


def _privacy_violations(item: dict[str, Any]) -> list[str]:
    text = json.dumps(
        {
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "raw_excerpt": item.get("raw_excerpt"),
            "visible_fields": item.get("visible_fields"),
            "contact_path": item.get("contact_path"),
        },
        ensure_ascii=False,
        default=str,
    )
    violations = [f"credential-like field: {name}" for name in public_text_violations(text)]
    if PHONE_RE.search(text):
        violations.append("raw phone number must be redacted")
    if WECHAT_RE.search(text):
        violations.append("raw wechat id must be redacted")
    if GROUP_RE.search(text):
        violations.append("private group name must be redacted")
    if NAME_WITH_LABEL_RE.search(text):
        violations.append("poster/contact name must be redacted")
    return violations
