from __future__ import annotations

from typing import Any

from ..schema import SearchLead, SearchProviderQuery
from .common import clamp_int, compact_text, domain_for_url, request_json, stable_lead_id


ENDPOINT = "https://api.tavily.com/search"


def build_tavily_payload(query: SearchProviderQuery) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query.query,
        "topic": "general",
        "search_depth": "basic",
        "max_results": clamp_int(query.limit, minimum=1, maximum=20),
        "time_range": "week" if query.days <= 7 else "month",
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_usage": True,
    }
    if query.include_domains:
        payload["include_domains"] = query.include_domains
    if query.exclude_domains:
        payload["exclude_domains"] = query.exclude_domains
    return payload


def search(query: SearchProviderQuery, api_key: str) -> tuple[list[SearchLead], int | None, int, str | None, dict[str, Any]]:
    data, http_status, elapsed_ms, headers = request_json(
        "POST",
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}"},
        payload=build_tavily_payload(query),
    )
    request_id = headers.get("x-request-id") or headers.get("X-Request-Id")
    return map_tavily_response(data, query), http_status, elapsed_ms, request_id, data.get("usage") or {}


def map_tavily_response(data: dict[str, Any], query: SearchProviderQuery) -> list[SearchLead]:
    results = data.get("results") or [] if isinstance(data, dict) else []
    leads: list[SearchLead] = []
    for rank, item in enumerate(results, start=1):
        url = item.get("url") or ""
        if not url:
            continue
        title = compact_text(item.get("title") or url, limit=220) or url
        leads.append(
            SearchLead(
                lead_id=stable_lead_id(query.provider, url, query.query),
                provider=query.provider,
                query=query.query,
                rank=rank,
                title=title,
                url=url,
                domain=domain_for_url(url),
                snippet=compact_text(item.get("content"), limit=700),
                published_at=item.get("published_date"),
                score=_safe_float(item.get("score")),
                raw={"favicon": item.get("favicon")},
            )
        )
    return leads


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
