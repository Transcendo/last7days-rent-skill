from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import urljoin

from ..contact import attach_contact_methods, extract_contact_methods, platform_contact
from ..schema import ListingItem, now_iso


CARD_RE = re.compile(r"<(?P<tag>li|div)[^>]*(?:data-house_code=\"(?P<code>[^\"]+)\")?[^>]*>(?P<body>.*?)</(?P=tag)>", re.S)
ANCHOR_RE = re.compile(r"<a[^>]+href=\"(?P<href>[^\"]+)\"[^>]*(?:title=\"(?P<title>[^\"]+)\")?[^>]*>(?P<text>.*?)</a>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return unescape(TAG_RE.sub(" ", text)).strip()


def parse_beike_lianjia_html(html: str, base_url: str = "https://sh.zu.ke.com") -> list[ListingItem]:
    items: list[ListingItem] = []
    for match in CARD_RE.finditer(html):
        body = match.group("body")
        anchor = ANCHOR_RE.search(body)
        if not anchor:
            continue
        title = _clean(anchor.group("title") or anchor.group("text"))
        if not title:
            continue
        href = urljoin(base_url, anchor.group("href"))
        code = match.group("code") or _infer_house_code(href)
        text = _clean(body)
        price = _extract_price(text)
        area = _extract_area(text)
        layout = _extract_layout(text)
        item_id = f"beike-{code or hashlib.sha1(href.encode()).hexdigest()[:12]}"
        item = ListingItem(
            item_id=item_id,
            source_id="beike_lianjia",
            source_tier="P0",
            source_url=href,
            platform_id=code,
            title=title,
            body=text,
            price_monthly=price,
            layout=layout,
            area_sqm=area,
            address_hint=_extract_address_hint(title),
            contact_route="platform",
            provenance={
                "title": "beike_lianjia.card.title",
                "price_monthly": "beike_lianjia.card.price",
                "area_sqm": "beike_lianjia.card.area",
                "platform_id": "data-house_code or url",
            },
            confidence={"source_parse": 0.78},
            collected_at=now_iso(),
        )
        attach_contact_methods(item, [platform_contact(href, "beike_lianjia.card.href"), *extract_contact_methods(text, entry_url=href, source_field="beike_lianjia.card.text")])
        items.append(item)
    return items


def _infer_house_code(url: str) -> str | None:
    found = re.search(r"/zufang/([A-Za-z0-9]+)\.html", url)
    return found.group(1) if found else None


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
