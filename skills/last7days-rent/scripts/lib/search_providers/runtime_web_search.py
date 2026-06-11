from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schema import SearchLead, SearchProviderResult
from .common import compact_text, domain_for_url, stable_lead_id


RUNTIME_PROVIDER = "runtime_web_search"


class RuntimeWebSearchError(ValueError):
    pass


def load_runtime_web_search(
    path: str | Path,
    *,
    runtime_query: str | None = None,
) -> tuple[list[SearchLead], list[SearchProviderResult], list[str]]:
    file_path = Path(path).expanduser()
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeWebSearchError(f"runtime websearch JSON not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeWebSearchError(f"runtime websearch JSON is invalid: {file_path}: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise RuntimeWebSearchError("runtime websearch JSON must be an object")

    leads: list[SearchLead] = []
    results: list[SearchProviderResult] = []
    warnings: list[str] = []
    for index, entry in enumerate(_query_entries(data), start=1):
        entry_leads, provider_result, entry_warnings = map_runtime_web_search_entry(
            entry,
            runtime_query=runtime_query,
            query_index=index,
        )
        leads.extend(entry_leads)
        results.append(provider_result)
        warnings.extend(entry_warnings)
    return leads, results, _dedupe_warnings(warnings)


def map_runtime_web_search_entry(
    payload: dict[str, Any],
    *,
    runtime_query: str | None = None,
    query_index: int = 1,
) -> tuple[list[SearchLead], SearchProviderResult, list[str]]:
    if not isinstance(payload, dict):
        raise RuntimeWebSearchError("runtime websearch query entry must be an object")

    query = _first_text(payload, ("query",)) or runtime_query
    if not query:
        raise RuntimeWebSearchError("runtime websearch JSON requires query; pass --runtime-query or include query")

    runtime_provider = _first_text(payload, ("provider", "runtime_provider")) or RUNTIME_PROVIDER
    result_payload = _result_payload(payload)
    success = result_payload.get("success")
    usage = {
        "runtime_provider": runtime_provider,
        "source_shape": _source_shape(payload),
        "query_index": query_index,
    }
    if success is False:
        warning = "runtime_web_search_failed"
        return (
            [],
            SearchProviderResult(provider=RUNTIME_PROVIDER, status="failed", query=query, warning=warning, usage=usage),
            [warning],
        )

    web_results = _web_results(result_payload)
    leads: list[SearchLead] = []
    warnings: list[str] = []
    for rank, item in enumerate(web_results, start=1):
        if not isinstance(item, dict):
            warnings.append("runtime_web_search_invalid_item")
            continue
        url = _first_text(item, ("url", "link", "href"))
        if not url:
            warnings.append("runtime_web_search_missing_url")
            continue
        position = _as_int(item.get("position") or item.get("rank"), default=rank)
        title = _first_text(item, ("title", "name")) or url
        snippet = compact_text(_first_text(item, ("description", "snippet", "text")), limit=500)
        text_excerpt = compact_text(_first_text(item, ("text_excerpt", "content", "raw_content")), limit=900)
        leads.append(
            SearchLead(
                lead_id=stable_lead_id(RUNTIME_PROVIDER, url, query),
                provider=RUNTIME_PROVIDER,
                query=query,
                rank=position,
                title=title,
                url=url,
                domain=domain_for_url(url),
                snippet=snippet,
                published_at=_first_text(item, ("published_at", "publishedAt", "published_date", "date")),
                score=_as_float(item.get("score")),
                highlights=_text_list(item.get("highlights")),
                text_excerpt=text_excerpt,
                raw={
                    "source_shape": "runtime_web_search",
                    "runtime_provider": runtime_provider,
                    "position": position,
                    "query_index": query_index,
                    "original_result": item,
                },
            )
        )

    if not leads:
        warnings.append("runtime_web_search_empty")
    provider_result = SearchProviderResult(
        provider=RUNTIME_PROVIDER,
        status="ok",
        query=query,
        warning=_warning_summary(warnings),
        lead_count=len(leads),
        usage=usage,
    )
    return leads, provider_result, _dedupe_warnings(warnings)


def _query_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    queries = data.get("queries")
    if queries is None:
        return [data]
    if not isinstance(queries, list):
        raise RuntimeWebSearchError("runtime websearch JSON field queries must be a list")
    if not all(isinstance(item, dict) for item in queries):
        raise RuntimeWebSearchError("runtime websearch JSON field queries must contain objects")
    return queries


def _result_payload(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("results")
    if isinstance(nested, dict):
        return nested
    if isinstance(nested, list):
        return {"success": True, "data": {"web": nested}}
    return payload


def _web_results(payload: dict[str, Any]) -> list[Any]:
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("web"), list):
        return data["web"]
    if isinstance(payload.get("web"), list):
        return payload["web"]
    if isinstance(payload.get("results"), list):
        return payload["results"]
    return []


def _source_shape(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("results"), dict):
        return "wrapped_results"
    if isinstance(payload.get("results"), list):
        return "results_list"
    if "success" in payload and isinstance(payload.get("data"), dict):
        return "direct_success_data"
    if isinstance(payload.get("web"), list):
        return "direct_web"
    return "unknown"


def _first_text(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _warning_summary(warnings: list[str]) -> str | None:
    unique = _dedupe_warnings(warnings)
    return ",".join(unique) if unique else None


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    return list(dict.fromkeys(warnings))
