from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import urljoin

from ..privacy import redact_text, sanitize_listing
from ..schema import ListingItem, now_iso


FANG_LINK_RE = re.compile(r"<a(?P<attrs>[^>]*)>(?P<text>.*?)</a>", re.S)
ATTR_RE = re.compile(r"(?P<name>[a-zA-Z_-]+)=\"(?P<value>[^\"]*)\"")
TAG_RE = re.compile(r"<[^>]+>")


def parse_fang_html(html: str, base_url: str = "https://zu.fang.com") -> list[ListingItem]:
    items: list[ListingItem] = []
    seen: set[str] = set()
    for match in FANG_LINK_RE.finditer(html):
        attrs = {m.group("name").lower(): m.group("value") for m in ATTR_RE.finditer(match.group("attrs"))}
        raw_href = attrs.get("href", "")
        if "/chuzu/" not in raw_href:
            continue
        href = urljoin(base_url, raw_href)
        if href in seen:
            continue
        seen.add(href)
        title = _clean(attrs.get("title") or match.group("text"))
        if not title:
            continue
        price = _extract_price(title)
        area = _extract_area(title)
        layout = _extract_layout(title)
        item_id = "fang-" + hashlib.sha1(href.encode()).hexdigest()[:12]
        item = ListingItem(
            item_id=item_id,
            source_id="fang",
            source_tier="P0",
            source_url=href,
            title=redact_text(title),
            body=redact_text(title),
            price_monthly=price,
            layout=layout,
            area_sqm=area,
            address_hint=_extract_address_hint(title),
            contact_route="platform",
            provenance={
                "title": "fang.link.title",
                "price_monthly": "fang.link.title",
                "area_sqm": "fang.link.title",
            },
            confidence={"source_parse": 0.65},
            collected_at=now_iso(),
        )
        items.append(sanitize_listing(item))
    return items


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return unescape(TAG_RE.sub(" ", text)).strip()


def _extract_price(text: str) -> int | None:
    found = re.search(r"(\d{3,6})\s*元/月", text)
    return int(found.group(1)) if found else None


def _extract_area(text: str) -> float | None:
    found = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|平米)", text)
    return float(found.group(1)) if found else None


def _extract_layout(text: str) -> str | None:
    found = re.search(r"(\d室\d厅|\d室\d卫|\d居室|开间|一居室|两居室)", text)
    return found.group(1) if found else None


def _extract_address_hint(text: str) -> str | None:
    found = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]+附近)", text)
    return found.group(1) if found else None
