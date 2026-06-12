from __future__ import annotations

from .schema import RentProfile


AREA_HINTS = {
    "五角场": ["五角场", "政立路", "江湾体育场", "国定路", "三门路"],
    "张江": ["张江", "广兰路", "金科路", "中科路"],
    "亦庄": ["亦庄", "经海路", "荣昌东街", "大族广场", "经海二路", "次渠", "台湖"],
    "西二旗": ["西二旗", "上地", "清河", "后厂村", "龙泽"],
    "后厂村": ["西二旗", "上地", "清河", "后厂村", "龙泽"],
    "南山": ["南山", "科技园", "后海", "高新园"],
}


def derive_commute_areas(anchor: str | None) -> list[str]:
    if not anchor:
        return []
    for keyword, areas in AREA_HINTS.items():
        if keyword in anchor:
            return areas
    return [anchor]


def profile_to_search_plan(profile: RentProfile) -> dict:
    office_name = profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint")
    areas = profile.commute.get("derived_areas") or derive_commute_areas(office_name)
    return {
        "city": profile.office_anchor.get("city"),
        "office_anchor": profile.office_anchor,
        "commute_areas": areas,
        "max_commute_minutes": profile.commute.get("max_minutes", 35),
        "budget_min": profile.housing_constraints.get("budget_min"),
        "budget_max": profile.housing_constraints.get("budget_max"),
        "rental_mode": profile.housing_constraints.get("rental_mode", "either"),
        "min_bedrooms": profile.housing_constraints.get("min_bedrooms"),
        "source_priority": profile.source_preferences.get("p0_order", ["beike_lianjia", "wellcee", "fang", "official_verifier"]),
        "risk_filter": ["p1_p2_source_not_allowed", "private_source_not_allowed", "websearch_not_allowed"],
        "open_questions": profile.open_questions,
    }
