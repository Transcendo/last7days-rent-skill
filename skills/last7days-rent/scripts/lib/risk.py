from __future__ import annotations

from .contact import has_actionable_contact
from .schema import ListingItem, MVP_SOURCE_IDS, RentProfile


NON_MVP_SOURCE_IDS = {
    "ziroom",
    "woaiwojia",
    "anjuke",
    "58",
    "douban",
    "xiaohongshu",
    "weibo",
    "wechat_official",
    "wechat_group",
    "moments",
    "company_group",
    "alumni_group",
    "private_import",
    "websearch",
    "user_import",
}

PRIVATE_SOURCE_IDS = {"wechat_group", "moments", "company_group", "alumni_group", "private_import", "user_import"}
P1_P2_SOURCE_IDS = NON_MVP_SOURCE_IDS - PRIVATE_SOURCE_IDS - {"websearch"}


def is_mvp_listing_source(source_id: str) -> bool:
    return source_id in MVP_SOURCE_IDS - {"official_verifier"}


def source_scope_risk(source_id: str) -> list[str]:
    if source_id == "user_authorized":
        return []
    if source_id == "websearch":
        return ["websearch_not_allowed"]
    if source_id in PRIVATE_SOURCE_IDS:
        return ["private_source_not_allowed"]
    if source_id in P1_P2_SOURCE_IDS:
        return ["p1_p2_source_not_allowed"]
    if source_id not in MVP_SOURCE_IDS:
        return ["unknown_source_not_allowed"]
    if source_id == "official_verifier":
        return ["official_verifier_not_recall_source"]
    return []


def should_reject_listing(item: ListingItem) -> bool:
    if source_scope_risk(item.source_id):
        return True
    return not has_actionable_contact(item)


def risk_flags_for_listing(item: ListingItem, profile: RentProfile | None = None) -> list[str]:
    flags = list(dict.fromkeys(item.risk_flags + source_scope_risk(item.source_id)))
    budget_min = None
    budget_max = None
    if profile:
        budget_min = profile.housing_constraints.get("budget_min")
        budget_max = profile.housing_constraints.get("budget_max")
    if item.price_monthly is not None and budget_min and item.price_monthly < float(budget_min) * 0.55:
        flags.append("low_price_anomaly")
    if item.price_monthly is not None and budget_max and item.price_monthly > float(budget_max) * 1.2:
        flags.append("over_budget")
        flags.append("hard_filter_over_budget")
    if not item.deposit:
        flags.append("fee_terms_missing")
    if not item.community_name and not item.address_hint:
        flags.append("vague_location")
    if not has_actionable_contact(item):
        flags.append("no_actionable_contact")
    contact = (item.contact_route or "").lower()
    if any(token in contact for token in ["wechat", "phone", "wx", "vx"]):
        flags.append("contact_only_phone_or_wechat")
    text = f"{item.title} {item.body}"
    if any(token in text for token in ["拒绝看房", "不能看房", "不看房"]):
        flags.append("refuses_viewing")
    if any(token in text for token in ["先交定金", "定金留房", "看房费", "资料费"]):
        flags.append("deposit_pressure")
    return list(dict.fromkeys(flags))


def risk_score(flags: list[str]) -> float:
    weights = {
        "private_source_not_allowed": 1.0,
        "p1_p2_source_not_allowed": 1.0,
        "websearch_not_allowed": 1.0,
        "low_price_anomaly": 0.35,
        "fee_terms_missing": 0.15,
        "contact_only_phone_or_wechat": 0.3,
        "vague_location": 0.2,
        "refuses_viewing": 0.5,
        "deposit_pressure": 0.55,
        "over_budget": 0.2,
        "hard_filter_over_budget": 0.6,
        "official_verifier_not_recall_source": 0.4,
        "no_actionable_contact": 0.8,
    }
    return min(1.0, sum(weights.get(flag, 0.1) for flag in set(flags)))
