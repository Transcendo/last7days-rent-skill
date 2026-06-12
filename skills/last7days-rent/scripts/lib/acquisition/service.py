from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any

from ..leads import build_candidate_leads
from ..providers.config import load_provider_config
from ..providers.registry import ProviderRegistry
from ..providers.web import DDGSSearchProvider
from ..schema import CandidateLead, ExtractedDocument, ListingItem, ProviderDiagnostic, SearchPlan, SourceCandidate, to_plain
from ..sources.registry import is_enabled_p0_source
from ..sources.router import parse_source_fixture
from .classifier import classify_url
from .query_builder import DiscoveryQuery, build_discovery_queries


@dataclass
class AcquisitionResult:
    provider_diagnostics: list[ProviderDiagnostic] = field(default_factory=list)
    search_queries: list[DiscoveryQuery] = field(default_factory=list)
    source_candidates: list[SourceCandidate] = field(default_factory=list)
    actionable_leads: list[CandidateLead] = field(default_factory=list)
    blocked_sources: list[dict[str, Any]] = field(default_factory=list)
    extracted_documents: list[ExtractedDocument] = field(default_factory=list)
    structured_listings: list[ListingItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_diagnostics": [item.to_dict() for item in self.provider_diagnostics],
            "search_queries": [item.to_dict() for item in self.search_queries],
            "source_candidates": [item.to_dict() for item in self.source_candidates],
            "actionable_leads": [item.to_dict() for item in self.actionable_leads],
            "blocked_sources": [dict(item) for item in self.blocked_sources],
            "extracted_documents": [item.to_dict() for item in self.extracted_documents],
            "structured_listings": [item.to_dict() for item in self.structured_listings],
            "warnings": list(self.warnings),
        }


def run_acquisition(
    plan: SearchPlan,
    profile,
    *,
    search_provider: str = "auto",
    extract_provider: str = "auto",
    limit: int = 10,
) -> AcquisitionResult:
    config = load_provider_config(search_override=search_provider, extract_override=extract_provider)
    registry = ProviderRegistry(config)
    resolution = registry.resolve()
    result = AcquisitionResult(provider_diagnostics=resolution.diagnostics)
    result.search_queries = _limit_discovery_queries(build_discovery_queries(plan, profile), limit)
    hits = []
    if not resolution.search_provider.is_available():
        result.warnings.append(
            "no available search provider; configure BRAVE_SEARCH_API_KEY, EXA_API_KEY, TAVILY_API_KEY, or install ddgs"
        )
    else:
        per_query_limit = _per_query_limit(limit)
        for query in result.search_queries:
            try:
                hits.extend(resolution.search_provider.search(query.query, limit=per_query_limit))
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"{resolution.search_provider.name} search failed for {query.query}: {exc}")
    if not hits and resolution.search_provider.name != "ddgs":
        result.warnings.append(f"{resolution.search_provider.name} search produced no hits; fallback to ddgs")
        fallback = DDGSSearchProvider()
        if fallback.is_available():
            per_query_limit = _per_query_limit(limit)
            for query in result.search_queries:
                try:
                    hits.extend(fallback.search(query.query, limit=per_query_limit))
                except Exception as fallback_exc:  # noqa: BLE001
                    result.warnings.append(f"ddgs fallback failed for {query.query}: {fallback_exc}")
        elif not fallback.is_available():
            result.warnings.append("ddgs fallback unavailable")
    result.source_candidates = _hits_to_candidates(hits)
    result.actionable_leads = build_candidate_leads(profile, result.source_candidates, limit=limit)
    urls = _lead_urls(result.actionable_leads, limit)
    if urls and _should_extract_details(resolution.extract_provider.name, extract_provider):
        try:
            result.extracted_documents = resolution.extract_provider.extract(urls)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"{resolution.extract_provider.name} extract failed: {exc}; keeping L0 leads")
            result.blocked_sources.extend(
                {"url": url, "provider": resolution.extract_provider.name, "status": "failed", "error": str(exc)}
                for url in urls
            )
            return result
        result.blocked_sources = _blocked_sources(result.extracted_documents)
        result.structured_listings = _parse_documents(result.extracted_documents, result.source_candidates, result.warnings)
    elif urls:
        result.warnings.append("detail enhancement skipped: no Exa/Tavily extract key; returning L0 actionable leads")
    return result


def _hits_to_candidates(hits) -> list[SourceCandidate]:
    candidates: list[SourceCandidate] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.url in seen:
            continue
        seen.add(hit.url)
        classified = classify_url(hit.url)
        candidate = SourceCandidate(
            candidate_id="candidate-" + hashlib.sha1(f"{hit.provider}:{hit.query}:{hit.url}".encode()).hexdigest()[:16],
            source_id=classified.source_id,
            source_tier=classified.source_tier,  # type: ignore[arg-type]
            source_url=hit.url,
            title=hit.title or hit.url,
            snippet=hit.description,
            provider=hit.provider,
            query=hit.query,
            position=hit.position,
            ddgs_description=hit.description if hit.provider == "ddgs" else None,
            visible_fields=_visible_fields(f"{hit.title} {hit.description}"),
            can_promote=classified.can_promote,
            reject_reason=classified.reject_reason,
            raw=hit.to_dict(),
            warnings=[] if classified.can_promote else [classified.reject_reason or "candidate_only"],
        )
        candidates.append(candidate)
    return candidates


def _lead_urls(leads: list[CandidateLead], limit: int) -> list[str]:
    urls: list[str] = []
    for lead in leads:
        if lead.url in urls:
            continue
        urls.append(lead.url)
        if len(urls) >= limit:
            break
    return urls


def _should_extract_details(active_provider: str, requested_provider: str) -> bool:
    if active_provider != "basic_http":
        return True
    return requested_provider == "basic_http"


def _limit_discovery_queries(queries: list[DiscoveryQuery], limit: int) -> list[DiscoveryQuery]:
    max_queries = max(3, min(8, int(limit) * 2))
    return queries[:max_queries]


def _per_query_limit(limit: int) -> int:
    return max(1, min(4, int(limit)))


def _blocked_sources(docs: list[ExtractedDocument]) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    for doc in docs:
        if doc.status == "ok":
            continue
        blocked.append(
            {
                "url": doc.final_url or doc.requested_url,
                "provider": doc.provider,
                "status": doc.status,
                "error": doc.error or doc.status,
            }
        )
    return blocked


def _parse_documents(docs: list[ExtractedDocument], candidates: list[SourceCandidate], warnings: list[str]) -> list[ListingItem]:
    candidate_by_url = {candidate.source_url: candidate for candidate in candidates}
    listings: list[ListingItem] = []
    for doc in docs:
        candidate = candidate_by_url.get(doc.requested_url) or candidate_by_url.get(doc.final_url)
        if not candidate or not is_enabled_p0_source(candidate.source_id):
            continue
        if doc.status != "ok":
            warnings.append(f"{candidate.source_id}: extract failed for {doc.requested_url}: {doc.error or doc.status}")
            continue
        text = doc.raw_content or doc.content
        parsed, _, parsed_warnings = parse_source_fixture(candidate.source_id, text, base_url=doc.final_url or doc.requested_url)
        listings.extend(parsed)
        warnings.extend(f"{candidate.source_id}: {warning}" for warning in parsed_warnings)
        if not parsed:
            warnings.append(f"{candidate.source_id}: parser produced no ListingItem for {doc.requested_url}; provider extract kept as evidence only")
    return listings


def _visible_fields(text: str) -> dict[str, Any]:
    return {
        "price_text": _first_match(text, r"(\d{3,6}\s*(?:元/月|RMB/月|元))"),
        "area_text": _first_match(text, r"(\d+(?:\.\d+)?\s*(?:㎡|平米))"),
        "layout_text": _first_match(text, r"(\d室\d厅|\d室\d卫|\d居室|开间|一居室|两居室|次卧|主卧)"),
        "freshness_text": _first_match(text, r"((?:今天|\d+天前|近\d+天)[\u4e00-\u9fa5]{0,6})"),
    }


def _first_match(text: str, pattern: str) -> str | None:
    found = re.search(pattern, text)
    return found.group(1) if found else None
