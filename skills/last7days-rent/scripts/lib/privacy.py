from __future__ import annotations

import copy
import re
from typing import Any

from .schema import ListingCluster, ListingItem
from .secret_guard import assert_no_secrets, secret_violations, sanitize_text


PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
WECHAT_RE = re.compile(r"(?i)(?:微信|wechat|weixin|wx|vx|v信)\s*[:：]?\s*[a-z][a-z0-9_-]{4,}\b")
GROUP_RE = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9_-]{2,24}(?:微信群|租房群|公司群|校友群|朋友圈群|群聊)")
NAME_WITH_LABEL_RE = re.compile(r"(?:房东|中介|联系人|发帖人|姓名|本人)\s*[:：]?\s*[\u4e00-\u9fa5]{2,4}")
AVATAR_SOURCE_RE = re.compile(r"(?:头像|截图|私聊截图|聊天截图)\s*[:：]\s*[^，。；;\n]{1,30}")


def redact_text(text: Any) -> Any:
    if text is None:
        return None
    if not isinstance(text, str):
        return text
    redacted = PHONE_RE.sub("[redacted-phone]", text)
    redacted = WECHAT_RE.sub("[redacted-wechat]", redacted)
    redacted = GROUP_RE.sub("[redacted-group]", redacted)
    redacted = NAME_WITH_LABEL_RE.sub("[redacted-name]", redacted)
    redacted = AVATAR_SOURCE_RE.sub("[redacted-source-image]", redacted)
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value


def sanitize_secret_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_secret_value(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_secret_value(item) for key, item in value.items()}
    return value


def redact_profile(profile_dict: dict[str, Any]) -> dict[str, Any]:
    redacted = redact_value(copy.deepcopy(profile_dict))
    if isinstance(redacted, dict):
        redacted.setdefault("privacy", {})["redacted"] = True
    return redacted


def sanitize_listing(item: ListingItem) -> ListingItem:
    data = item.to_dict()
    data = sanitize_secret_value(data)
    data["raw_contact_redacted"] = False
    return ListingItem.from_dict(data)


def sanitize_cluster(cluster: ListingCluster) -> ListingCluster:
    sanitized_items = [sanitize_listing(item) for item in cluster.source_items]
    canonical = sanitize_listing(cluster.canonical_listing)
    return ListingCluster(
        cluster_id=cluster.cluster_id,
        canonical_listing=canonical,
        source_items=sanitized_items,
        merge_reasons=redact_value(cluster.merge_reasons),
        trust_level=cluster.trust_level,
        match_score=cluster.match_score,
        risk_score=cluster.risk_score,
        final_score=cluster.final_score,
        risk_flags=cluster.risk_flags,
        match_reasons=sanitize_secret_value(cluster.match_reasons),
        next_questions=sanitize_secret_value(cluster.next_questions),
        field_provenance=sanitize_secret_value(cluster.field_provenance),
    )


def public_text_violations(text: str) -> list[str]:
    return secret_violations(text)


def assert_public_safe(text: str) -> None:
    assert_no_secrets(text)
