from __future__ import annotations

from typing import Any

from ..schema import SearchLead, SearchProviderQuery
from .common import clamp_int, compact_text, domain_for_url, request_json, stable_lead_id


ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def build_brave_params(query: SearchProviderQuery) -> dict[str, Any]:
    q = query.query
    if query.include_domains:
        sites = " OR ".join(f"site:{domain}" for domain in query.include_domains)
        q = f"({sites}) {q}"
    params = {
        "q": q,
        "country": "CN",
        "search_lang": "zh",
        "ui_lang": "zh-CN",
        "count": clamp_int(query.limit, minimum=1, maximum=20),
        "offset": 0,
        "result_filter": "web",
        "text_decorations": "false",
        "extra_snippets": "true",
        "operators": "true",
    }
    if query.freshness:
        params["freshness"] = query.freshness
    return params


def search(query: SearchProviderQuery, api_key: str) -> tuple[list[SearchLead], int | None, int, str | None, dict[str, Any]]:
    data, http_status, elapsed_ms, headers = request_json(
        "GET",
        ENDPOINT,
        headers={"X-Subscription-Token": api_key},
        params=build_brave_params(query),
    )
    request_id = headers.get("x-request-id") or headers.get("X-Request-Id")
    return map_brave_response(data, query), http_status, elapsed_ms, request_id, {}


def map_brave_response(data: dict[str, Any], query: SearchProviderQuery) -> list[SearchLead]:
    results = ((data.get("web") or {}).get("results") or []) if isinstance(data, dict) else []
    leads: list[SearchLead] = []
    for rank, item in enumerate(results, start=1):
        url = item.get("url") or ""
        if not url:
            continue
        snippets = [item.get("description") or ""]
        snippets.extend(item.get("extra_snippets") or [])
        snippet = compact_text(" ".join(part for part in snippets if part), limit=700)
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
                snippet=snippet,
                published_at=item.get("age") or item.get("page_age"),
                score=None,
                highlights=[compact_text(part, limit=220) or "" for part in item.get("extra_snippets") or []],
                raw={"family_friendly": item.get("family_friendly"), "language": item.get("language")},
            )
        )
    return leads
