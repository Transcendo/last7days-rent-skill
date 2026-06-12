from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any

from ..contact import attach_contact_methods, platform_contact
from ..providers.config import load_provider_config
from ..providers.registry import ProviderRegistry
from ..providers.web import BasicHttpExtractProvider, DDGSSearchProvider
from ..schema import ExtractedDocument, ListingItem, ProviderDiagnostic, SearchPlan, SourceCandidate, now_iso, to_plain
from ..sources.registry import is_enabled_p0_source
from ..sources.router import parse_source_fixture
from .classifier import classify_url
from .query_builder import DiscoveryQuery, build_discovery_queries


@dataclass
class AcquisitionResult:
    provider_diagnostics: list[ProviderDiagnostic] = field(default_factory=list)
    search_queries: list[DiscoveryQuery] = field(default_factory=list)
    source_candidates: list[SourceCandidate] = field(default_factory=list)
    extracted_documents: list[ExtractedDocument] = field(default_factory=list)
    structured_listings: list[ListingItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_diagnostics": [item.to_dict() for item in self.provider_diagnostics],
            "search_queries": [item.to_dict() for item in self.search_queries],
            "source_candidates": [item.to_dict() for item in self.source_candidates],
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
    result.search_queries = build_discovery_queries(plan, profile)
    hits = []
    try:
        for query in result.search_queries:
            hits.extend(resolution.search_provider.search(query.query, limit=limit))
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"{resolution.search_provider.name} search failed: {exc}; fallback to ddgs")
        fallback = DDGSSearchProvider()
        if fallback.is_available() and fallback.name != resolution.search_provider.name:
            for query in result.search_queries:
                try:
                    hits.extend(fallback.search(query.query, limit=limit))
                except Exception as fallback_exc:  # noqa: BLE001
                    result.warnings.append(f"ddgs fallback failed for {query.query}: {fallback_exc}")
        elif not fallback.is_available():
            result.warnings.append("ddgs fallback unavailable")
    result.source_candidates = _hits_to_candidates(hits)
    urls = _extractable_urls(result.source_candidates, limit)
    if urls:
        try:
            result.extracted_documents = resolution.extract_provider.extract(urls)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"{resolution.extract_provider.name} extract failed: {exc}; fallback to basic_http")
            result.extracted_documents = BasicHttpExtractProvider().extract(urls)
        result.structured_listings = _parse_documents(result.extracted_documents, result.source_candidates, result.warnings)
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


def _extractable_urls(candidates: list[SourceCandidate], limit: int) -> list[str]:
    urls: list[str] = []
    for candidate in candidates:
        if not candidate.can_promote or not candidate.source_url:
            continue
        if candidate.source_url in urls:
            continue
        urls.append(candidate.source_url)
        if len(urls) >= limit:
            break
    return urls


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
            fallback = _parse_text_listing(candidate, doc)
            if fallback:
                listings.append(fallback)
            else:
                warnings.append(f"{candidate.source_id}: parser produced no ListingItem for {doc.requested_url}")
    return listings


def _parse_text_listing(candidate: SourceCandidate, doc: ExtractedDocument) -> ListingItem | None:
    text = _clean_text(f"{doc.title} {candidate.title} {doc.content} {candidate.snippet or ''}")
    price = _extract_price(text)
    area = _extract_area(text)
    layout = _extract_layout(text)
    if not any([price, area, layout]):
        return None
    url = doc.final_url or doc.requested_url
    item = ListingItem(
        item_id=f"{candidate.source_id}-extract-{hashlib.sha1(url.encode()).hexdigest()[:12]}",
        source_id=candidate.source_id,
        source_tier="P0",
        source_url=url,
        title=doc.title or candidate.title,
        body=text[:1200],
        price_monthly=price,
        area_sqm=area,
        layout=layout,
        contact_route="platform",
        provenance={
            "title": f"{doc.provider}.extract.title",
            "price_monthly": f"{doc.provider}.extract.content",
            "area_sqm": f"{doc.provider}.extract.content",
            "layout": f"{doc.provider}.extract.content",
            "source_url": "SourceCandidate.url",
        },
        confidence={"provider_extract": 0.45},
        collected_at=now_iso(),
    )
    attach_contact_methods(item, [platform_contact(url, f"{doc.provider}.extract.url")])
    return item


def _visible_fields(text: str) -> dict[str, Any]:
    return {
        "price_text": _first_match(text, r"(\d{3,6}\s*(?:元/月|RMB/月|元))"),
        "area_text": _first_match(text, r"(\d+(?:\.\d+)?\s*(?:㎡|平米))"),
        "layout_text": _first_match(text, r"(\d室\d厅|\d室\d卫|\d居室|开间|一居室|两居室|次卧|主卧)"),
        "freshness_text": _first_match(text, r"((?:今天|\d+天前|近\d+天)[\u4e00-\u9fa5]{0,6})"),
    }


def _extract_price(text: str) -> int | None:
    found = re.search(r"(\d{3,6})\s*(?:元/月|RMB/月|元)", text)
    return int(found.group(1)) if found else None


def _extract_area(text: str) -> float | None:
    found = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|平米)", text)
    return float(found.group(1)) if found else None


def _extract_layout(text: str) -> str | None:
    found = re.search(r"(\d室\d厅|\d室\d卫|\d居室|开间|一居室|两居室|次卧|主卧)", text)
    return found.group(1) if found else None


def _first_match(text: str, pattern: str) -> str | None:
    found = re.search(pattern, text)
    return found.group(1) if found else None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
