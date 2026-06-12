from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ..commute_plan import derive_commute_areas
from ..schema import RentProfile, SearchPlan


@dataclass(frozen=True)
class DiscoveryQuery:
    query: str
    source_hint: str
    source_tier: str = "websearch"

    def to_dict(self) -> dict[str, str]:
        return {"query": self.query, "source_hint": self.source_hint, "source_tier": self.source_tier}


def build_discovery_queries(plan: SearchPlan, profile: RentProfile) -> list[DiscoveryQuery]:
    request = plan.request
    city = request.city or profile.office_anchor.get("city") or ""
    office = request.office_anchor or profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint") or city
    areas = plan.commute_areas or profile.commute.get("derived_areas") or derive_commute_areas(str(office))
    keywords = _keywords(city, str(office), areas)
    constraints = _constraint_terms(request)
    queries: list[DiscoveryQuery] = []
    for source_id, source_queries in plan.source_queries.items():
        for source_query in source_queries:
            scope = _site_scope(str(source_query.get("url", "")))
            if not scope:
                continue
            for keyword in keywords:
                queries.append(DiscoveryQuery(_clean_keyword(f"site:{scope} {keyword} 租房 {constraints}"), source_id))
    if office:
        queries.append(DiscoveryQuery(_clean_keyword(f"{city} {office} 附近 租房 近7天 {constraints}"), "broad"))
    return _dedupe_queries(queries)


def _site_scope(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    root_segments = {"zufang", "chuzu", "rent-apartment"}
    for index, segment in enumerate(segments):
        if segment in root_segments:
            return "/".join([parsed.netloc, *segments[: index + 1]])
    return parsed.netloc


def _keywords(city: str, office: str, areas: list[str]) -> list[str]:
    base = [_with_city(city, office)]
    for area in areas[:4]:
        if area and area not in office:
            base.append(_with_city(city, area))
    return [_clean_keyword(item) for item in base if item.strip()]


def _constraint_terms(request) -> str:
    terms: list[str] = []
    if request.budget_max:
        terms.append(f"{request.budget_max}元以内")
    min_bedrooms = request.min_bedrooms
    if min_bedrooms == 1:
        terms.append("一居室")
    elif min_bedrooms == 2:
        terms.append("两居室")
    elif min_bedrooms and min_bedrooms > 2:
        terms.append(f"{min_bedrooms}居室")
    if request.days:
        terms.append(f"近{request.days}天")
    return " ".join(terms)


def _with_city(city: str, phrase: str) -> str:
    if city and city not in phrase:
        return f"{city} {phrase}"
    return phrase


def _clean_keyword(value: str) -> str:
    return " ".join(value.split())


def _dedupe_queries(queries: list[DiscoveryQuery]) -> list[DiscoveryQuery]:
    seen: set[str] = set()
    result: list[DiscoveryQuery] = []
    for query in queries:
        if query.query in seen:
            continue
        seen.add(query.query)
        result.append(query)
    return result
