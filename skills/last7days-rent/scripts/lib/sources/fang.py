from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import urljoin

from ..contact import attach_contact_methods, extract_contact_methods, platform_contact
from ..schema import ListingItem, now_iso


DL_RE = re.compile(r"<dl[^>]*class=[\"'][^\"']*list[^\"']*[\"'][^>]*>(?P<body>.*?)</dl>", re.S)
FANG_LINK_RE = re.compile(r"<a(?P<attrs>[^>]*)>(?P<text>.*?)</a>", re.S)
ATTR_RE = re.compile(r"(?P<name>[a-zA-Z_-]+)\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)")
TAG_RE = re.compile(r"<[^>]+>")
PRICE_RE = re.compile(r"<span[^>]*class=[\"'][^\"']*price[^\"']*[\"'][^>]*>(?P<price>\d{3,6})</span>\s*元/月", re.S)
DATA_AJAX_RE = re.compile(r"&quot;HouseId&quot;:&quot;(?P<house_id>\d+)&quot;")


def parse_fang_html(html: str, base_url: str = "https://zu.fang.com") -> list[ListingItem]:
    items: list[ListingItem] = []
    seen: set[str] = set()
    blocks = [m.group("body") for m in DL_RE.finditer(html)]
    if not blocks:
        blocks = [html]
    for block in blocks:
        anchor_match = _find_listing_anchor(block)
        if not anchor_match:
            continue
        attrs = {m.group("name").lower(): m.group("value") for m in ATTR_RE.finditer(anchor_match.group("attrs"))}
        raw_href = attrs.get("href", "")
        if "/chuzu/" not in raw_href:
            continue
        href = urljoin(base_url, raw_href)
        if href in seen:
            continue
        seen.add(href)
        title = _clean(attrs.get("title") or anchor_match.group("text"))
        if not title:
            continue
        text = f"{title} {_clean(block)}".strip()
        price = _extract_price(text)
        area = _extract_area(text)
        layout = _extract_layout(text)
        platform_id = _extract_house_id(block, href)
        item_id = "fang-" + (platform_id or hashlib.sha1(href.encode()).hexdigest()[:12])
        item = ListingItem(
            item_id=item_id,
            source_id="fang",
            source_tier="P0",
            source_url=href,
            platform_id=platform_id,
            title=title,
            body=text,
            price_monthly=price,
            layout=layout,
            area_sqm=area,
            address_hint=_extract_address_hint(text),
            community_name=_extract_community(block),
            contact_route="platform",
            provenance={
                "title": "fang.card.title",
                "price_monthly": "fang.card.price",
                "area_sqm": "fang.card.layout_line",
                "platform_id": "fang.card.data_ajax or url",
                "contact_methods": "fang.card.detail_url",
            },
            confidence={"source_parse": 0.65},
            collected_at=now_iso(),
        )
        attach_contact_methods(item, [platform_contact(href, "fang.card.href"), *extract_contact_methods(text, entry_url=href, source_field="fang.card.text")])
        items.append(item)
    return items


def _find_listing_anchor(block: str) -> re.Match[str] | None:
    fallback: re.Match[str] | None = None
    for match in FANG_LINK_RE.finditer(block):
        attrs = {m.group("name").lower(): m.group("value") for m in ATTR_RE.finditer(match.group("attrs"))}
        if "/chuzu/" not in attrs.get("href", ""):
            continue
        if attrs.get("title") or _clean(match.group("text")):
            return match
        fallback = fallback or match
    return fallback


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return unescape(TAG_RE.sub(" ", text)).strip()


def _extract_price(text: str) -> int | None:
    found = PRICE_RE.search(text) or re.search(r"(\d{3,6})\s*元/月", text)
    if found and "price" in found.groupdict():
        return int(found.group("price"))
    return int(found.group(1)) if found else None


def _extract_area(text: str) -> float | None:
    found = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|平米)", text)
    return float(found.group(1)) if found else None


def _extract_layout(text: str) -> str | None:
    found = re.search(r"(\d室\d厅|\d室\d卫|\d居室|开间|一居室|两居室)", text)
    return found.group(1) if found else None


def _extract_address_hint(text: str) -> str | None:
    found = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]+附近|[\u4e00-\u9fa5A-Za-z0-9]+站约\d+米|[\u4e00-\u9fa5A-Za-z0-9]+-五角场-[\u4e00-\u9fa5A-Za-z0-9]+)", text)
    return found.group(1) if found else None


def _extract_house_id(block: str, href: str) -> str | None:
    found = DATA_AJAX_RE.search(block) or re.search(r"/chuzu/\d+_(\d+)_", href)
    return found.group("house_id") if found and "house_id" in found.groupdict() else (found.group(1) if found else None)


def _extract_community(block: str) -> str | None:
    matches = re.findall(r"<span>([\u4e00-\u9fa5A-Za-z0-9（）()·_-]{2,40})</span>", block)
    return matches[-1] if matches else None
