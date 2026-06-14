from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .env import ensure_local_dirs, get_paths
from .listing_pool import empty_pool, load_pool, merge_items, save_pool
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
        if "contact_path" in item and item["contact_path"] is not None and not isinstance(item["contact_path"], dict):
            errors.append({"path": f"items[{idx}].contact_path", "message": "must be object when present"})
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
