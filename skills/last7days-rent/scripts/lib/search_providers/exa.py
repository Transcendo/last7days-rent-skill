from __future__ import annotations

from typing import Any

from ..schema import SearchLead, SearchProviderQuery
from .common import clamp_int, compact_text, domain_for_url, request_json, stable_lead_id, utc_window


ENDPOINT = "https://api.exa.ai/search"


def build_exa_payload(query: SearchProviderQuery) -> dict[str, Any]:
    start, end = utc_window(query.days)
    payload: dict[str, Any] = {
        "query": query.query,
        "type": "auto",
        "numResults": clamp_int(query.limit, minimum=1, maximum=20),
        "startPublishedDate": start,
        "endPublishedDate": end,
        "contents": {
            "highlights": {
                "query": "租金 面积 小区 地址 联系方式 预约看房 发布日期",
                "numSentences": 2,
                "highlightsPerUrl": 2,
            }
        },
    }
    if query.include_domains:
        payload["includeDomains"] = query.include_domains
    if query.exclude_domains:
        payload["excludeDomains"] = query.exclude_domains
    return payload


def search(query: SearchProviderQuery, api_key: str) -> tuple[list[SearchLead], int | None, int, str | None, dict[str, Any]]:
    data, http_status, elapsed_ms, headers = request_json(
        "POST",
        ENDPOINT,
        headers={"x-api-key": api_key},
        payload=build_exa_payload(query),
    )
    request_id = headers.get("x-request-id") or headers.get("X-Request-Id")
    return map_exa_response(data, query), http_status, elapsed_ms, request_id, {}


def map_exa_response(data: dict[str, Any], query: SearchProviderQuery) -> list[SearchLead]:
    results = data.get("results") or [] if isinstance(data, dict) else []
    leads: list[SearchLead] = []
    for rank, item in enumerate(results, start=1):
        url = item.get("url") or ""
        if not url:
            continue
        highlights = [compact_text(value, limit=260) or "" for value in item.get("highlights") or []]
        text_excerpt = compact_text(item.get("text"), limit=700)
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
                snippet=text_excerpt or (highlights[0] if highlights else None),
                published_at=item.get("publishedDate"),
                score=_safe_float(item.get("score")),
                highlights=highlights,
                text_excerpt=text_excerpt,
                raw={
                    "id": item.get("id"),
                    "author": item.get("author"),
                    "highlight_scores": item.get("highlightScores"),
                },
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
