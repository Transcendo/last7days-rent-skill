from __future__ import annotations

from typing import Callable

from ..env import provider_api_key
from ..schema import SearchLead, SearchPlan, SearchProviderQuery, SearchProviderResult
from . import brave, exa, tavily
from .common import ProviderHTTPError


ProviderFn = Callable[[SearchProviderQuery, str], tuple[list[SearchLead], int | None, int, str | None, dict]]

PROVIDER_CALLS: dict[str, ProviderFn] = {
    "brave": brave.search,
    "tavily": tavily.search,
    "exa": exa.search,
}


def fetch_search_leads(plan: SearchPlan) -> tuple[list[SearchLead], list[SearchProviderResult], list[str]]:
    leads: list[SearchLead] = []
    results: list[SearchProviderResult] = []
    warnings: list[str] = []
    if not plan.provider_queries:
        warnings.append("no_search_provider_queries")
        return leads, results, warnings

    for query in plan.provider_queries:
        key = provider_api_key(query.provider)
        if not key:
            warning = f"{query.provider}_missing_api_key"
            warnings.append(warning)
            results.append(SearchProviderResult(provider=query.provider, status="skipped", query=query.query, warning=warning))
            continue
        call = PROVIDER_CALLS.get(query.provider)
        if not call:
            warning = f"{query.provider}_unknown_provider"
            warnings.append(warning)
            results.append(SearchProviderResult(provider=query.provider, status="failed", query=query.query, warning=warning))
            continue
        try:
            provider_leads, http_status, elapsed_ms, request_id, usage = call(query, key)
        except ProviderHTTPError as exc:
            warning = _warning_for_status(query.provider, exc.status_code)
            warnings.append(warning)
            results.append(
                SearchProviderResult(
                    provider=query.provider,
                    status="failed",
                    query=query.query,
                    http_status=exc.status_code,
                    warning=warning,
                )
            )
            continue
        except Exception as exc:
            warning = f"{query.provider}_provider_error:{type(exc).__name__}"
            warnings.append(warning)
            results.append(SearchProviderResult(provider=query.provider, status="failed", query=query.query, warning=warning))
            continue
        leads.extend(provider_leads)
        results.append(
            SearchProviderResult(
                provider=query.provider,
                status="ok",
                query=query.query,
                http_status=http_status,
                elapsed_ms=elapsed_ms,
                lead_count=len(provider_leads),
                request_id=request_id,
                usage=usage,
            )
        )
    if not any(result.status == "ok" for result in results):
        warnings.append("no_search_provider_available")
    return leads, results, warnings


def _warning_for_status(provider: str, status_code: int | None) -> str:
    if status_code is None:
        return f"{provider}_network_error"
    if status_code in {400, 422}:
        return f"{provider}_invalid_request"
    if status_code in {401, 403}:
        return f"{provider}_auth_failed"
    if status_code in {402, 432, 433}:
        return f"{provider}_quota_limited"
    if status_code == 429:
        return f"{provider}_rate_limited"
    if status_code >= 500:
        return f"{provider}_provider_error"
    return f"{provider}_http_{status_code}"
