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
    enabled: bool
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


SOURCE_REGISTRY: dict[str, SourceMeta] = {
    "beike_lianjia": SourceMeta("beike_lianjia", "ke.com,lianjia.com", "P0", "A", "ListingItem[]", "L1", False, True, True, "enabled"),
    "wellcee": SourceMeta("wellcee", "wellcee.com", "P0", "A", "ListingItem[]", "L1", False, True, True, "enabled"),
    "fang": SourceMeta("fang", "fang.com", "P0", "A", "ListingItem[]", "L1", False, True, True, "enabled"),
    "official_verifier": SourceMeta("official_verifier", "official rental verifier", "P0", "B", "VerificationEvidence[]", "L1", False, False, True, "verifier_only"),
    "ziroom": SourceMeta("ziroom", "ziroom.com", "P1", "C", "disabled", "L0", True, False, False, "non_mvp"),
    "woaiwojia": SourceMeta("woaiwojia", "5i5j.com", "P1", "C", "disabled", "L0", True, False, False, "non_mvp"),
    "58": SourceMeta("58", "58.com", "P2", "D", "disabled", "L0", True, False, False, "non_mvp"),
    "anjuke": SourceMeta("anjuke", "anjuke.com", "P2", "D", "disabled", "L0", True, False, False, "non_mvp"),
    "douban": SourceMeta("douban", "douban.com", "P1/P2", "C", "disabled", "L0", True, False, False, "non_mvp"),
    "xiaohongshu": SourceMeta("xiaohongshu", "xiaohongshu.com", "P2", "D", "disabled", "L0", True, False, False, "non_mvp"),
    "weibo": SourceMeta("weibo", "weibo.com", "P2", "D", "disabled", "L0", True, False, False, "non_mvp"),
    "wechat_official": SourceMeta("wechat_official", "mp.weixin.qq.com", "P2", "C", "disabled", "L0", True, False, False, "non_mvp"),
    "wechat_group": SourceMeta("wechat_group", "private", "private", "D", "disabled", "L0", True, False, False, "non_mvp"),
    "websearch": SourceMeta("websearch", "search engine", "websearch", "C", "SourceCandidate only", "L0", False, False, False, "non_mvp"),
    "user_import": SourceMeta("user_import", "user authorized import", "private", "D", "disabled", "L0", True, False, False, "non_mvp"),
}


def source_registry() -> dict[str, dict]:
    return {key: value.to_dict() for key, value in SOURCE_REGISTRY.items()}


def get_source_meta(source_id: str) -> SourceMeta | None:
    return SOURCE_REGISTRY.get(source_id)


def is_enabled_p0_source(source_id: str) -> bool:
    meta = get_source_meta(source_id)
    return bool(meta and meta.enabled and meta.source_tier == "P0" and meta.can_promote_to_listing)
