from __future__ import annotations

import hashlib
from difflib import SequenceMatcher

from .normalize import canonical_url
from .schema import ListingCluster, ListingItem


def dedupe_key(item: ListingItem) -> str:
    if item.platform_id:
        return f"platform:{item.source_id}:{item.platform_id}"
    if item.source_url:
        return f"url:{canonical_url(item.source_url)}"
    parts = [
        item.community_name or "",
        item.layout or "",
        str(item.area_sqm or ""),
        str(item.price_monthly or ""),
    ]
    if any(parts):
        return "fields:" + "|".join(parts).lower()
    return "title:" + hashlib.sha1(item.title.encode()).hexdigest()[:12]


def maybe_same_listing(left: ListingItem, right: ListingItem) -> bool:
    if canonical_url(left.source_url) and canonical_url(left.source_url) == canonical_url(right.source_url):
        return True
    if left.platform_id and right.platform_id and left.platform_id == right.platform_id:
        return True
    shared_fields = [
        left.community_name and left.community_name == right.community_name,
        left.address_hint and left.address_hint == right.address_hint,
        left.layout and left.layout == right.layout,
        left.price_monthly is not None and left.price_monthly == right.price_monthly,
        left.area_sqm is not None and right.area_sqm is not None and abs(left.area_sqm - right.area_sqm) < 1.0,
    ]
    if sum(bool(v) for v in shared_fields) >= 3:
        return True
    if left.image_hashes and set(left.image_hashes) & set(right.image_hashes):
        return True
    left_contacts = {(m.contact_type, m.value or m.entry_url) for m in left.contact_methods if m.value or m.entry_url}
    right_contacts = {(m.contact_type, m.value or m.entry_url) for m in right.contact_methods if m.value or m.entry_url}
    if left_contacts and left_contacts & right_contacts:
        return True
    similarity = SequenceMatcher(None, left.title, right.title).ratio()
    return similarity > 0.86 and left.price_monthly == right.price_monthly


def dedupe_listings(items: list[ListingItem]) -> list[ListingCluster]:
    clusters: list[list[ListingItem]] = []
    for item in items:
        placed = False
        for group in clusters:
            if any(maybe_same_listing(item, existing) for existing in group):
                group.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    result: list[ListingCluster] = []
    for idx, group in enumerate(clusters, start=1):
        canonical = sorted(group, key=lambda x: (x.price_monthly is None, x.price_monthly or 0))[0]
        reasons = []
        if len(group) > 1:
            reasons.append("多源或重复字段命中，按 URL、平台 ID、小区/户型/面积/价格、标题相似度聚合。")
        cluster = ListingCluster(
            cluster_id=f"cluster-{idx:03d}",
            canonical_listing=canonical,
            source_items=group,
            merge_reasons=reasons,
            trust_level="L2" if len({item.source_id for item in group}) > 1 or len(group) > 1 else "L1",
        )
        result.append(cluster)
    return result
