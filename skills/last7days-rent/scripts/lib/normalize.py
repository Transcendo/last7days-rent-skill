from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .privacy import sanitize_listing
from .risk import risk_flags_for_listing, should_reject_listing
from .schema import ListingItem, RentProfile


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    query = urlencode(
        [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")]
    )
    path = re.sub(r"/+$", "", parts.path)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def normalize_listing(item: ListingItem, profile: RentProfile | None = None) -> ListingItem | None:
    if should_reject_listing(item):
        item.risk_flags = risk_flags_for_listing(item, profile)
        return None
    sanitized = sanitize_listing(item)
    sanitized.source_url = canonical_url(sanitized.source_url)
    if sanitized.title:
        sanitized.title = " ".join(sanitized.title.split())
    if sanitized.body:
        sanitized.body = " ".join(sanitized.body.split())
    sanitized.risk_flags = risk_flags_for_listing(sanitized, profile)
    return sanitized


def normalize_listings(items: list[ListingItem], profile: RentProfile | None = None) -> tuple[list[ListingItem], list[ListingItem]]:
    accepted: list[ListingItem] = []
    rejected: list[ListingItem] = []
    for item in items:
        normalized = normalize_listing(item, profile)
        if normalized is None:
            rejected.append(item)
        else:
            accepted.append(normalized)
    return accepted, rejected
