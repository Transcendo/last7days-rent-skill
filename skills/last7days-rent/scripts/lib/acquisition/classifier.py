from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ClassifiedUrl:
    source_id: str
    source_tier: str
    can_promote: bool
    reject_reason: str | None = None


def classify_url(url: str) -> ClassifiedUrl:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if _host_matches(host, "lianjia.com") or _host_matches(host, "ke.com"):
        return ClassifiedUrl("beike_lianjia", "P0", True)
    if _host_matches(host, "wellcee.com"):
        return ClassifiedUrl("wellcee", "P0", True)
    if _host_matches(host, "fang.com"):
        return ClassifiedUrl("fang", "P0", True)
    if _host_matches(host, "ziroom.com"):
        return ClassifiedUrl("ziroom", "P1", False, "roadmap_p1_candidate_only")
    if _host_matches(host, "5i5j.com"):
        return ClassifiedUrl("woaiwojia", "P1", False, "roadmap_p1_candidate_only")
    if _host_matches(host, "58.com"):
        return ClassifiedUrl("58", "P1", False, "roadmap_p1_candidate_only")
    if _host_matches(host, "anjuke.com"):
        return ClassifiedUrl("anjuke", "P1", False, "roadmap_p1_candidate_only")
    if _host_matches(host, "douban.com"):
        return ClassifiedUrl("douban", "P1", False, "roadmap_p1_candidate_only")
    if _host_matches(host, "mp.weixin.qq.com"):
        return ClassifiedUrl("wechat_official", "P1", False, "roadmap_p1_candidate_only")
    if _host_matches(host, "xiaohongshu.com"):
        return ClassifiedUrl("xiaohongshu", "P2", False, "roadmap_p2_user_authorized_only")
    if _host_matches(host, "weibo.com"):
        return ClassifiedUrl("weibo", "P2", False, "roadmap_p2_user_authorized_only")
    return ClassifiedUrl("websearch", "websearch", False, "unknown_or_unsupported_domain")


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")
