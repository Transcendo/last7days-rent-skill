from __future__ import annotations

from dataclasses import dataclass

from ..commute_plan import derive_commute_areas
from ..schema import RentProfile, SearchPlan


@dataclass(frozen=True)
class DiscoveryQuery:
    query: str
    source_hint: str
    source_tier: str = "websearch"

    def to_dict(self) -> dict[str, str]:
        return {"query": self.query, "source_hint": self.source_hint, "source_tier": self.source_tier}


CITY_HOSTS = {
    "北京": {
        "lianjia": "bj.lianjia.com/zufang",
        "ke": "bj.zu.ke.com/zufang",
        "fang": "zu.fang.com/chuzu",
        "wellcee": "www.wellcee.com/rent-apartment",
    },
    "上海": {
        "lianjia": "sh.lianjia.com/zufang",
        "ke": "sh.zu.ke.com/zufang",
        "fang": "sh.zu.fang.com",
        "wellcee": "www.wellcee.com/rent-apartment",
    },
}

ANCHOR_AREAS = {
    "北京亦庄办公点": ["亦庄", "经海路", "经海二路", "次渠", "台湖", "荣昌东街", "大族广场"],
    "亦庄办公点": ["亦庄", "经海路", "经海二路", "次渠", "台湖", "荣昌东街", "大族广场"],
}


def build_discovery_queries(plan: SearchPlan, profile: RentProfile) -> list[DiscoveryQuery]:
    request = plan.request
    city = request.city or profile.office_anchor.get("city") or "北京"
    office = request.office_anchor or profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint") or city
    areas = _areas_for_anchor(str(office), plan.commute_areas or profile.commute.get("derived_areas") or [])
    hosts = CITY_HOSTS.get(city, CITY_HOSTS["北京"])
    keywords = _keywords(city, str(office), areas)
    queries: list[DiscoveryQuery] = []
    for keyword in keywords:
        queries.extend(
            [
                DiscoveryQuery(f"site:{hosts['lianjia']} {keyword} 租房", "beike_lianjia"),
                DiscoveryQuery(f"site:{hosts['ke']} {keyword} 租房", "beike_lianjia"),
                DiscoveryQuery(f"site:{hosts['wellcee']} {keyword} 租房", "wellcee"),
                DiscoveryQuery(f"site:{hosts['fang']} {keyword} 租房", "fang"),
            ]
        )
    queries.append(DiscoveryQuery(f"{city} {office} 附近 租房 近7天", "broad"))
    return _dedupe_queries(queries)


def _areas_for_anchor(office: str, existing: list[str]) -> list[str]:
    for keyword, areas in ANCHOR_AREAS.items():
        if keyword in office:
            return areas
    return existing or derive_commute_areas(office)


def _keywords(city: str, office: str, areas: list[str]) -> list[str]:
    base = [f"{city} {office}"]
    for area in areas[:4]:
        if area and area not in office:
            base.append(f"{city} {office} {area}")
    return base


def _dedupe_queries(queries: list[DiscoveryQuery]) -> list[DiscoveryQuery]:
    seen: set[str] = set()
    result: list[DiscoveryQuery] = []
    for query in queries:
        if query.query in seen:
            continue
        seen.add(query.query)
        result.append(query)
    return result
