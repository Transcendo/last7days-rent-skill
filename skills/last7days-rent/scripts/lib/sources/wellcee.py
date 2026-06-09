from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from ..privacy import redact_text, sanitize_listing
from ..schema import ListingItem, now_iso


JSON_LD_RE = re.compile(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(?P<json>.*?)</script>", re.S)


def parse_wellcee_jsonld(html: str, fallback_url: str | None = None) -> list[ListingItem]:
    items: list[ListingItem] = []
    for match in JSON_LD_RE.finditer(html):
        raw = match.group("json").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            if node.get("@type") not in {"RealEstateListing", "Apartment", "Offer"}:
                continue
            item = _node_to_listing(node, fallback_url)
            if item:
                items.append(sanitize_listing(item))
    return items


def _node_to_listing(node: dict[str, Any], fallback_url: str | None) -> ListingItem | None:
    title = node.get("name") or node.get("headline")
    if not title:
        return None
    url = node.get("url") or fallback_url
    item_id = "wellcee-" + hashlib.sha1((url or title).encode()).hexdigest()[:12]
    offers = node.get("offers") if isinstance(node.get("offers"), dict) else {}
    address = node.get("address") if isinstance(node.get("address"), dict) else {}
    price = offers.get("price") or node.get("price")
    try:
        price_int = int(float(price)) if price is not None else None
    except (TypeError, ValueError):
        price_int = None
    body = node.get("description") or ""
    return ListingItem(
        item_id=item_id,
        source_id="wellcee",
        source_tier="P0",
        source_url=url,
        title=redact_text(str(title)),
        body=redact_text(str(body)),
        published_at=node.get("datePosted"),
        city=address.get("addressLocality"),
        district=address.get("addressRegion"),
        address_hint=address.get("streetAddress"),
        price_monthly=price_int,
        layout=_extract_layout(f"{title} {body}"),
        area_sqm=_extract_area(f"{title} {body}"),
        contact_route="platform",
        provenance={
            "title": "wellcee.jsonld.name",
            "price_monthly": "wellcee.jsonld.offers.price",
            "published_at": "wellcee.jsonld.datePosted",
        },
        confidence={"jsonld": 0.85, "date_posted_needs_verification": 1.0},
        collected_at=now_iso(),
    )


def _extract_area(text: str) -> float | None:
    found = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|平米)", text)
    return float(found.group(1)) if found else None


def _extract_layout(text: str) -> str | None:
    found = re.search(r"(\d室\d厅|\d室\d卫|\d居室|开间|一居室|两居室|一室户)", text)
    return found.group(1) if found else None
