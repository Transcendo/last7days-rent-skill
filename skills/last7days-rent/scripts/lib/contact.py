from __future__ import annotations

import re
from typing import Iterable

from .schema import ContactMethod, ListingItem


PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
WECHAT_RE = re.compile(r"(?i)(?:微信|wechat|weixin|wx|vx|v信)\s*[:：]?\s*([a-z][a-z0-9_-]{4,})\b")
QQ_RE = re.compile(r"(?i)(?:QQ|qq)\s*[:：]?\s*([1-9]\d{4,11})\b")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
FEISHU_RE = re.compile(r"(?i)(?:飞书|lark|feishu)\s*[:：]?\s*([a-z0-9._-]{4,})\b")
ORIGINAL_POST_RE = re.compile(r"(?:原帖|帖子|详情页|站内|平台|私信|联系入口|在线咨询|拨打电话|预约看房)[^。；;\n]{0,40}")


def platform_contact(entry_url: str | None, source_field: str = "source_url", notes: str | None = None) -> ContactMethod:
    return ContactMethod(
        contact_type="platform",
        value=None,
        entry_url=entry_url,
        source_field=source_field,
        public_visible=True,
        notes=notes or "打开平台详情页，使用页面提供的站内联系、电话或预约看房入口。",
    )


def extract_contact_methods(text: str | None, *, entry_url: str | None = None, source_field: str = "body") -> list[ContactMethod]:
    if not text:
        return []
    methods: list[ContactMethod] = []
    for value in PHONE_RE.findall(text):
        methods.append(ContactMethod("phone", value=value, source_field=source_field, public_visible=True))
    for value in WECHAT_RE.findall(text):
        methods.append(ContactMethod("wechat", value=value, source_field=source_field, public_visible=True))
    for value in QQ_RE.findall(text):
        methods.append(ContactMethod("qq", value=value, source_field=source_field, public_visible=True))
    for value in EMAIL_RE.findall(text):
        methods.append(ContactMethod("email", value=value, source_field=source_field, public_visible=True))
    for value in FEISHU_RE.findall(text):
        methods.append(ContactMethod("feishu", value=value, source_field=source_field, public_visible=True))
    for match in ORIGINAL_POST_RE.findall(text):
        methods.append(
            ContactMethod(
                "original_post",
                value=match.strip(),
                entry_url=entry_url,
                source_field=source_field,
                public_visible=True,
                notes="原帖或公开页面联系说明。",
            )
        )
    return merge_contact_methods(methods)


def merge_contact_methods(methods: Iterable[ContactMethod]) -> list[ContactMethod]:
    merged: dict[tuple[str, str, str], ContactMethod] = {}
    for method in methods:
        key = (method.contact_type, method.value or "", method.entry_url or "")
        if key not in merged:
            merged[key] = method
            continue
        existing = merged[key]
        if not existing.notes and method.notes:
            existing.notes = method.notes
        if not existing.source_field and method.source_field:
            existing.source_field = method.source_field
    return list(merged.values())


def infer_primary_route(methods: Iterable[ContactMethod]) -> str:
    order = ["phone", "wechat", "platform", "qq", "feishu", "email", "original_post", "user_authorized"]
    method_types = {method.contact_type for method in methods}
    for route in order:
        if route in method_types:
            return route
    return "unknown"


def attach_contact_methods(item: ListingItem, methods: Iterable[ContactMethod]) -> ListingItem:
    item.contact_methods = merge_contact_methods([*item.contact_methods, *methods])
    item.contact_route = infer_primary_route(item.contact_methods)
    return item


def has_actionable_contact(item_or_methods: ListingItem | Iterable[ContactMethod]) -> bool:
    methods = item_or_methods.contact_methods if isinstance(item_or_methods, ListingItem) else list(item_or_methods)
    for method in methods:
        if method.contact_type == "platform" and method.entry_url:
            return True
        if method.contact_type in {"phone", "wechat", "qq", "feishu", "email"} and method.value:
            return True
        if method.contact_type in {"original_post", "user_authorized"} and (method.value or method.entry_url):
            return True
    return False


def contact_display_text(methods: Iterable[ContactMethod]) -> str:
    parts: list[str] = []
    for method in methods:
        if method.contact_type == "platform":
            target = method.entry_url or "unknown"
            parts.append(f"平台入口: {target}")
        elif method.value:
            parts.append(f"{method.contact_type}: {method.value}")
        elif method.entry_url:
            parts.append(f"{method.contact_type}: {method.entry_url}")
    return "；".join(parts) if parts else "unknown"
