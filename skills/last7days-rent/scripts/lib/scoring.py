from __future__ import annotations

from datetime import datetime, timezone

from .feedback import feedback_boost_for_listing, load_feedback
from .risk import risk_score
from .schema import ListingCluster, RentProfile


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def budget_score(price: int | None, profile: RentProfile) -> tuple[float, str]:
    budget_min = profile.housing_constraints.get("budget_min")
    budget_max = profile.housing_constraints.get("budget_max")
    if price is None or not budget_max:
        return 0.45, "价格缺失或预算未完整设置，保留 unknown 不补全"
    if budget_min and price < budget_min:
        return 0.78, "价格低于预算下限，需要重点核验是否低价引流"
    if price <= budget_max:
        return 1.0, "价格在预算内"
    if price <= budget_max * 1.1:
        return 0.65, "略超预算，可作为备选"
    return 0.2, "明显超预算"


def commute_score(cluster: ListingCluster, profile: RentProfile) -> tuple[float, str]:
    listing = cluster.canonical_listing
    areas = profile.commute.get("derived_areas") or []
    text = " ".join([listing.title or "", listing.body or "", listing.community_name or "", listing.address_hint or ""])
    if areas and any(area and area in text for area in areas):
        return 0.92, "命中办公点推导通勤圈"
    if listing.city and listing.city == profile.office_anchor.get("city"):
        return 0.68, "城市匹配，但通勤圈需进一步确认"
    return 0.45, "通勤信息不足，需下一步核验"


def freshness_score(published_at: str | None) -> tuple[float, str]:
    if not published_at:
        return 0.55, "发布时间缺失或仅有维护时间，按弱 freshness 处理"
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days
        if age_days <= 7:
            return 1.0, "发布时间在近 7 天内"
        if age_days <= 30:
            return 0.45, "发布时间超过 7 天，需核验是否仍在租"
    except ValueError:
        return 0.55, "发布时间格式待核验"
    return 0.2, "发布时间较旧"


def trust_score(cluster: ListingCluster) -> tuple[float, str]:
    if cluster.trust_level == "L3":
        return 0.95, "用户联系确认或明确反馈"
    if cluster.trust_level == "L2":
        return 0.78, "多源佐证或重复字段一致"
    if cluster.trust_level == "L1":
        return 0.58, "单源结构化，待核验，不能视为已验真"
    return 0.25, "原始线索"


def score_cluster(cluster: ListingCluster, profile: RentProfile) -> ListingCluster:
    listing = cluster.canonical_listing
    if _has_real_viewable_feedback(cluster):
        cluster.trust_level = "L3"
    risk_flags = sorted(set(flag for item in cluster.source_items for flag in item.risk_flags))
    cluster.risk_flags = risk_flags
    cluster.risk_score = risk_score(risk_flags)

    budget, budget_reason = budget_score(listing.price_monthly, profile)
    commute, commute_reason = commute_score(cluster, profile)
    fresh, fresh_reason = freshness_score(listing.published_at)
    trust, trust_reason = trust_score(cluster)
    weights = profile.scoring_weights
    preference = 0.65
    feedback_boost = feedback_boost_for_listing(listing.item_id, listing.source_id)
    final = (
        weights.get("commute", 0.3) * commute
        + weights.get("budget", 0.25) * budget
        + weights.get("trust", 0.2) * trust
        + weights.get("freshness", 0.15) * fresh
        + weights.get("preference", 0.1) * preference
        - weights.get("risk_penalty", 0.35) * cluster.risk_score
        + feedback_boost
    )
    cluster.match_score = _clamp((budget + commute + fresh + trust + preference) / 5)
    cluster.final_score = _clamp(final)
    cluster.match_reasons = [commute_reason, budget_reason, trust_reason, fresh_reason]
    cluster.next_questions = next_questions_for_cluster(cluster)
    cluster.field_provenance = collect_field_provenance(cluster)
    return cluster


def _has_real_viewable_feedback(cluster: ListingCluster) -> bool:
    ids = {item.item_id for item in cluster.source_items}
    source_ids = {item.source_id for item in cluster.source_items}
    for row in load_feedback():
        if row.get("event_type") != "real_viewable":
            continue
        if row.get("listing_id") in ids or row.get("source_id") in source_ids:
            return True
    return False


def score_clusters(clusters: list[ListingCluster], profile: RentProfile) -> list[ListingCluster]:
    return [score_cluster(cluster, profile) for cluster in clusters]


def next_questions_for_cluster(cluster: ListingCluster) -> list[str]:
    listing = cluster.canonical_listing
    questions = ["这套房是否仍在租，最近能否视频或实地看房？"]
    if not listing.deposit:
        questions.append("押金、付款周期、中介费、服务费和水电网费用分别是多少？")
    if not listing.address_hint and not listing.community_name:
        questions.append("具体小区、楼栋或可核验地址是什么？")
    if cluster.trust_level in {"L0", "L1"}:
        questions.append("是否有平台房源编号、官方核验码或备案链接？")
    return questions


def collect_field_provenance(cluster: ListingCluster) -> dict:
    provenance: dict[str, list[str]] = {}
    for item in cluster.source_items:
        for field, source in item.provenance.items():
            provenance.setdefault(field, []).append(source)
        if item.contact_methods:
            provenance.setdefault("contact_methods", []).extend(
                method.source_field or method.contact_type for method in item.contact_methods
            )
    return provenance
