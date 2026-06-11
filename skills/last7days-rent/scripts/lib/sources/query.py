from __future__ import annotations

from urllib.parse import quote

from ..commute_plan import derive_commute_areas
from ..env import normalize_search_providers
from ..schema import RentProfile, SearchPlan, SearchProviderQuery, SearchRequest
from .registry import get_source_meta


CITY_DOMAINS = {
    "上海": {"beike_lianjia": "sh.zu.ke.com", "fang": "sh.zu.fang.com", "wellcee_city": "shanghai"},
    "北京": {"beike_lianjia": "bj.zu.ke.com", "fang": "zu.fang.com", "wellcee_city": "beijing"},
    "广州": {"beike_lianjia": "gz.zu.ke.com", "fang": "gz.zu.fang.com", "wellcee_city": "guangzhou"},
    "深圳": {"beike_lianjia": "sz.zu.ke.com", "fang": "sz.zu.fang.com", "wellcee_city": "shenzhen"},
}

DEFAULT_LISTING_SOURCES = ["beike_lianjia", "fang", "wellcee"]

SOURCE_SEARCH_DOMAINS = {
    "beike_lianjia": ["ke.com", "lianjia.com"],
    "fang": ["fang.com"],
    "wellcee": ["wellcee.com"],
}

AREA_SLUGS = {
    ("上海", "五角场"): {"beike_lianjia": "wujiaochang", "fang": "house-a026-b01647"},
    ("上海", "江湾体育场"): {"beike_lianjia": "jiangwantiyuchang", "fang": "house-a026-b01648"},
    ("上海", "控江路"): {"fang": "house-a026-b010350"},
}


def request_from_profile(
    profile: RentProfile,
    *,
    limit: int = 10,
    days: int = 7,
    sources: list[str] | None = None,
    providers: list[str] | None = None,
) -> SearchRequest:
    office = profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint")
    return SearchRequest(
        city=profile.office_anchor.get("city"),
        office_anchor=office,
        budget_min=profile.housing_constraints.get("budget_min"),
        budget_max=profile.housing_constraints.get("budget_max"),
        days=days,
        limit=limit,
        sources=sources or _profile_listing_sources(profile),
        providers=providers or ["auto"],
    )


def build_search_plan(request: SearchRequest, profile: RentProfile | None = None) -> SearchPlan:
    areas = []
    if profile:
        areas = profile.commute.get("derived_areas") or []
    areas = areas or derive_commute_areas(request.office_anchor)
    selected_sources = request.sources or DEFAULT_LISTING_SOURCES
    queries: dict[str, list[dict]] = {}
    for source_id in selected_sources:
        meta = get_source_meta(source_id)
        if not meta or not meta.enabled:
            continue
        built = _queries_for_source(source_id, request, areas)
        if built:
            queries[source_id] = built
    return SearchPlan(
        request=request,
        commute_areas=areas,
        provider_queries=_provider_queries_for_request(request, selected_sources, areas),
        source_queries=queries,
        open_questions=list(profile.open_questions if profile else []),
    )


def _profile_listing_sources(profile: RentProfile) -> list[str]:
    raw = profile.source_preferences.get("p0_order", DEFAULT_LISTING_SOURCES)
    return [source for source in raw if source in SOURCE_SEARCH_DOMAINS] or DEFAULT_LISTING_SOURCES


def _provider_queries_for_request(request: SearchRequest, selected_sources: list[str], areas: list[str]) -> list[SearchProviderQuery]:
    providers = normalize_search_providers(request.providers or ["auto"])
    include_domains = _domains_for_sources(selected_sources)
    area = next((item for item in areas if item), request.office_anchor or "")
    base_query = _base_query(request, area)
    queries: list[SearchProviderQuery] = []
    for provider in providers:
        queries.append(
            SearchProviderQuery(
                provider=provider,
                query=base_query,
                limit=request.limit,
                days=request.days,
                include_domains=include_domains,
                freshness=_freshness_for_days(request.days),
                params={"listing_sources": selected_sources, "city": request.city or "上海", "area": area},
            )
        )
    return queries


def _domains_for_sources(selected_sources: list[str]) -> list[str]:
    domains: list[str] = []
    for source_id in selected_sources:
        for domain in SOURCE_SEARCH_DOMAINS.get(source_id, []):
            if domain not in domains:
                domains.append(domain)
    return domains


def _base_query(request: SearchRequest, area: str) -> str:
    parts = [request.city or "上海", area or request.office_anchor or "", "租房"]
    if request.budget_max:
        parts.append(f"{request.budget_max}以内")
    if request.days:
        parts.append(f"近{request.days}天")
    return " ".join(part for part in parts if part)


def _freshness_for_days(days: int) -> str:
    if days <= 1:
        return "pd"
    if days <= 7:
        return "pw"
    if days <= 31:
        return "pm"
    return "py"


def _queries_for_source(source_id: str, request: SearchRequest, areas: list[str]) -> list[dict]:
    city = request.city or "上海"
    domains = CITY_DOMAINS.get(city, CITY_DOMAINS["上海"])
    primary_area = next((area for area in areas if area), request.office_anchor or "")
    if source_id == "beike_lianjia":
        domain = domains["beike_lianjia"]
        slug = _area_slug(city, primary_area, source_id)
        path = f"/zufang/{slug}/" if slug else "/zufang/"
        return [{"url": f"https://{domain}{path}", "city": city, "area": primary_area, "days": request.days, "limit": request.limit}]
    if source_id == "fang":
        domain = domains["fang"]
        slug = _area_slug(city, primary_area, source_id)
        path = f"/{slug}/" if slug else "/"
        return [{"url": f"https://{domain}{path}", "city": city, "area": primary_area, "days": request.days, "limit": request.limit}]
    if source_id == "wellcee":
        city_slug = domains["wellcee_city"]
        keyword = quote(primary_area or city)
        return [{
            "url": f"https://www.wellcee.com/rent-apartment/{city_slug}?keyword={keyword}",
            "city": city,
            "area": primary_area,
            "days": request.days,
            "limit": request.limit,
            "warning": "Wellcee 当前没有稳定公开搜索解析入口，主要支持用户显式 URL/HTML 导入。",
        }]
    return []


def _area_slug(city: str, area: str, source_id: str) -> str | None:
    for (known_city, keyword), slugs in AREA_SLUGS.items():
        if known_city == city and keyword in area:
            return slugs.get(source_id)
    return None
