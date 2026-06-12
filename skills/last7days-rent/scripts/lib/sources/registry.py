from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal


AccessLevel = Literal["A", "B", "C", "D"]


@dataclass(frozen=True)
class SourceMeta:
    source_id: str
    domain: str
    source_tier: str
    access_level: AccessLevel
    allowed_output_type: str
    default_trust_level: str
    requires_authorization: bool
    can_promote_to_listing: bool
    live_enabled: bool
    contact_capability: list[str]
    live_smoke_url_template: str | None
    enabled: bool
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


SOURCE_REGISTRY: dict[str, SourceMeta] = {
    "beike_lianjia": SourceMeta("beike_lianjia", "ke.com,lianjia.com", "P0", "A", "ListingItem[]", "L1", False, True, True, ["platform"], "https://sh.zu.ke.com/zufang/wujiaochang/", True, "enabled"),
    "wellcee": SourceMeta("wellcee", "wellcee.com", "P0", "A", "ListingItem[]", "L1", False, True, False, ["platform", "original_post", "phone", "wechat", "email"], None, True, "url_import_limited"),
    "fang": SourceMeta("fang", "fang.com", "P0", "A", "ListingItem[]", "L1", False, True, True, ["platform", "phone"], "https://sh.zu.fang.com/house-a026-b01647/", True, "enabled"),
    "official_verifier": SourceMeta("official_verifier", "official rental verifier", "P0", "B", "VerificationEvidence[]", "L1", False, False, False, ["official_verifier"], None, True, "verifier_only"),
    "ziroom": SourceMeta("ziroom", "ziroom.com", "P1", "C", "candidate_only", "L0", True, False, False, ["unknown"], None, False, "roadmap_p1"),
    "woaiwojia": SourceMeta("woaiwojia", "5i5j.com", "P1", "C", "candidate_only", "L0", True, False, False, ["unknown"], None, False, "roadmap_p1"),
    "58": SourceMeta("58", "58.com", "P1", "C", "candidate_only", "L0", True, False, False, ["unknown"], None, False, "roadmap_p1"),
    "anjuke": SourceMeta("anjuke", "anjuke.com", "P1", "C", "candidate_only", "L0", True, False, False, ["unknown"], None, False, "roadmap_p1"),
    "douban": SourceMeta("douban", "douban.com", "P1", "C", "candidate_only", "L0", True, False, False, ["unknown"], None, False, "roadmap_p1"),
    "xiaohongshu": SourceMeta("xiaohongshu", "xiaohongshu.com", "P2", "D", "disabled", "L0", True, False, False, ["unknown"], None, False, "non_mvp"),
    "weibo": SourceMeta("weibo", "weibo.com", "P2", "D", "disabled", "L0", True, False, False, ["unknown"], None, False, "non_mvp"),
    "wechat_official": SourceMeta("wechat_official", "mp.weixin.qq.com", "P1", "C", "candidate_only", "L0", True, False, False, ["unknown"], None, False, "roadmap_p1"),
    "wechat_group": SourceMeta("wechat_group", "private", "private", "D", "disabled", "L0", True, False, False, ["unknown"], None, False, "non_mvp"),
    "websearch": SourceMeta("websearch", "search engine", "websearch", "C", "SourceCandidate only", "L0", False, False, False, ["unknown"], None, False, "non_mvp"),
    "user_import": SourceMeta("user_import", "user authorized import", "private", "D", "authorized ListingItem[]", "L1", True, False, False, ["phone", "wechat", "email", "original_post", "user_authorized"], None, False, "non_mvp"),
}


def source_registry() -> dict[str, dict]:
    return {key: value.to_dict() for key, value in SOURCE_REGISTRY.items()}


def get_source_meta(source_id: str) -> SourceMeta | None:
    return SOURCE_REGISTRY.get(source_id)


def is_enabled_p0_source(source_id: str) -> bool:
    meta = get_source_meta(source_id)
    return bool(meta and meta.enabled and meta.source_tier == "P0" and meta.can_promote_to_listing)
