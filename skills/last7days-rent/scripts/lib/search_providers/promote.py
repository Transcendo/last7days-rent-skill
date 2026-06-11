from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

from ..contact import platform_contact
from ..schema import ListingItem, SearchLead
from .common import canonical_url, domain_for_url


P0_DOMAIN_SOURCES = {
    "ke.com": "beike_lianjia",
    "lianjia.com": "beike_lianjia",
    "fang.com": "fang",
    "wellcee.com": "wellcee",
}

RENTAL_TOKENS = [
    "租房",
    "出租",
    "转租",
    "合租",
    "整租",
    "押一付",
    "元/月",
    "月租",
    "apartment",
    "rent",
    "lease",
]


def dedupe_search_leads(leads: list[SearchLead]) -> list[SearchLead]:
    deduped: dict[str, SearchLead] = {}
    for lead in leads:
        key = canonical_url(lead.url)
        if key not in deduped:
            deduped[key] = lead
            continue
        existing = deduped[key]
        existing.highlights = list(dict.fromkeys([*existing.highlights, *lead.highlights]))
        existing.raw.setdefault("providers", [])
        existing.raw["providers"].append({"provider": lead.provider, "rank": lead.rank, "query": lead.query})
        if lead.score is not None and (existing.score is None or lead.score > existing.score):
            existing.score = lead.score
    return list(deduped.values())


def promote_search_leads(leads: list[SearchLead]) -> tuple[list[ListingItem], list[SearchLead], list[SearchLead]]:
    listings: list[ListingItem] = []
    promoted: list[SearchLead] = []
    rejected: list[SearchLead] = []
    for lead in dedupe_search_leads(leads):
        source_id = p0_source_for_domain(lead.domain or domain_for_url(lead.url))
        if not source_id:
            rejected.append(_reject(lead, "non_p0_domain"))
            continue
        if not _looks_like_open_url(lead.url):
            rejected.append(_reject(lead, "invalid_url"))
            continue
        if not has_rental_semantics(lead):
            rejected.append(_reject(lead, "no_rental_semantics"))
            continue
        lead.can_promote = True
        lead.source_id = source_id
        listings.append(_listing_from_lead(lead, source_id))
        promoted.append(lead)
    return listings, promoted, rejected


def p0_source_for_domain(domain: str) -> str | None:
    value = domain.lower().removeprefix("www.")
    for allowed, source_id in P0_DOMAIN_SOURCES.items():
        if value == allowed or value.endswith(f".{allowed}"):
            return source_id
    return None


def has_rental_semantics(lead: SearchLead) -> bool:
    text = " ".join([lead.title or "", lead.snippet or "", lead.text_excerpt or "", *lead.highlights]).lower()
    return any(token.lower() in text for token in RENTAL_TOKENS)


def _looks_like_open_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _reject(lead: SearchLead, reason: str) -> SearchLead:
    lead.can_promote = False
    lead.rejection_reason = reason
    return lead


def _listing_from_lead(lead: SearchLead, source_id: str) -> ListingItem:
    url = canonical_url(lead.url)
    excerpt = _body_from_lead(lead)
    return ListingItem(
        item_id=f"search-{lead.provider}-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]}",
        source_id=source_id,
        source_tier="P0",
        title=lead.title,
        body=excerpt or "",
        source_url=url,
        published_at=lead.published_at,
        contact_route="platform",
        contact_methods=[platform_contact(url, f"{lead.provider}.search.url")],
        trust_level="L1",
        provenance={
            "title": f"{lead.provider}.search.title",
            "body": f"{lead.provider}.search.snippet",
            "source_url": f"{lead.provider}.search.url",
            "provider": lead.provider,
            "search_lead_id": lead.lead_id,
        },
        confidence={"search_lead": 0.35, "promotion_gate": 0.55},
    )


def _body_from_lead(lead: SearchLead) -> str | None:
    parts = [lead.snippet or "", *(lead.highlights or []), lead.text_excerpt or ""]
    text = " ".join(part for part in parts if part)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:900] if text else None
