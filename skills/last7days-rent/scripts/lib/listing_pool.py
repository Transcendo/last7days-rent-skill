from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse, urlunparse
from typing import Any

from .schema import now_iso
from .store import read_json, write_json


def empty_pool(pool_id: str = "jd-hq-beijing", scenario: str = "jd_hq_beijing_poc") -> dict[str, Any]:
    now = now_iso()
    return {"pool_meta": {"pool_id": pool_id, "scenario": scenario, "created_at": now, "updated_at": now}, "profile_summary": {}, "listings": []}


def load_pool(path) -> dict[str, Any]:
    return read_json(path, default=empty_pool())


def save_pool(path, pool: dict[str, Any]) -> None:
    pool.setdefault("pool_meta", {})["updated_at"] = now_iso()
    write_json(path, pool)


def merge_items(pool: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    pool = dict(pool or empty_pool())
    pool.setdefault("pool_meta", {}).setdefault("created_at", now_iso())
    pool.setdefault("pool_meta", {})["updated_at"] = now_iso()
    pool["profile_summary"] = evidence.get("query_context", {})
    listings = {item["listing_id"]: dict(item) for item in pool.get("listings", [])}
    by_weak = {_weak_key(item): item["listing_id"] for item in listings.values() if _weak_key(item)}
    for raw in evidence.get("items", []):
        listing = _listing_from_evidence(raw)
        listing_id = listing["listing_id"]
        weak = _weak_key(listing)
        existing_id = listing_id if listing_id in listings else by_weak.get(weak)
        if existing_id and existing_id in listings:
            listings[existing_id] = _merge_listing(listings[existing_id], listing)
        else:
            listings[listing_id] = listing
            if weak:
                by_weak[weak] = listing_id
    merged = list(listings.values())
    for item in merged:
        _recompute_trust(item)
    merged.sort(key=lambda item: (_priority_order(item.get("priority")), -_trust_order(item.get("trust_level")), item.get("price_monthly") or 10**9))
    pool["listings"] = merged
    return pool


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", "", ""))


def _listing_from_evidence(item: dict[str, Any]) -> dict[str, Any]:
    canonical = item.get("canonical_url") or canonicalize_url(item["source_url"])
    visible = item.get("visible_fields") or {}
    normalized = item.get("normalized_fields") or {}
    price = normalized.get("price_monthly") or _parse_int(visible.get("price_text"))
    area = normalized.get("area_sqm") or _parse_number(visible.get("area_text"))
    bedrooms = normalized.get("bedrooms") or _parse_bedrooms(visible.get("layout_text") or item.get("title", ""))
    source_domain = item.get("source_domain") or urlparse(item["source_url"]).netloc.lower()
    contact_path = item.get("contact_path") or {"type": "platform_entry", "entry_url": item["source_url"]}
    now = item.get("observed_at") or now_iso()
    observation = {
        "evidence_id": item["evidence_id"],
        "source_name": item.get("source_name"),
        "source_domain": source_domain,
        "source_url": item["source_url"],
        "canonical_url": canonical,
        "observed_at": now,
        "page_opened": bool(item.get("page_opened")),
        "visible_fields": visible,
        "normalized_fields": {"price_monthly": price, "area_sqm": area, "bedrooms": bedrooms},
        "contact_path": contact_path,
        "raw_excerpt": item.get("raw_excerpt"),
    }
    listing_id = "listing-" + hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return {
        "listing_id": listing_id,
        "status": "new",
        "priority": "A",
        "trust_level": "L0",
        "title": item.get("title") or canonical,
        "community": visible.get("community") or "待核验",
        "district_hint": visible.get("district_hint") or "待核验",
        "price_monthly": price,
        "price_text": visible.get("price_text") or "待核验",
        "area_sqm": area,
        "area_text": visible.get("area_text") or "待核验",
        "bedrooms": bedrooms,
        "layout_text": visible.get("layout_text") or "待核验",
        "commute_tags": [tag for tag in [visible.get("district_hint")] if tag],
        "source_names": [item.get("source_name") or source_domain],
        "source_urls": [item["source_url"]],
        "source_domains": [source_domain],
        "contact_path": contact_path,
        "risk_flags": _risk_flags(item),
        "next_actions": ["确认仍在租", "确认费用条款", "确认看房时间"],
        "first_seen_at": now,
        "last_seen_at": now,
        "observations": [observation],
    }


def _merge_listing(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged["last_seen_at"] = incoming.get("last_seen_at") or now_iso()
    for key in ["source_names", "source_urls", "source_domains", "commute_tags", "risk_flags", "next_actions"]:
        values = list(merged.get(key, []))
        for value in incoming.get(key, []):
            if value and value not in values:
                values.append(value)
        merged[key] = values
    merged.setdefault("observations", []).extend(incoming.get("observations", []))
    for key in ["price_monthly", "price_text", "area_sqm", "area_text", "bedrooms", "layout_text", "community", "district_hint"]:
        if _missing(merged.get(key)) and not _missing(incoming.get(key)):
            merged[key] = incoming[key]
    if merged.get("status") in {"shortlisted", "contacted", "scheduled", "viewed", "rejected", "leased"}:
        return merged
    merged["status"] = incoming.get("status", merged.get("status", "new"))
    return merged


def _recompute_trust(item: dict[str, Any]) -> None:
    observations = item.get("observations", [])
    opened = any(obs.get("page_opened") for obs in observations)
    independent_domains = {obs.get("source_domain") for obs in observations if obs.get("source_domain")}
    visible_count = sum(1 for key in ["price_monthly", "area_sqm", "bedrooms", "community"] if not _missing(item.get(key)))
    if item.get("status") in {"contacted", "scheduled", "viewed"}:
        item["trust_level"] = "L3"
    elif len(independent_domains) >= 2 and visible_count >= 3:
        item["trust_level"] = "L2"
    elif opened and visible_count >= 3:
        item["trust_level"] = "L1"
    else:
        item["trust_level"] = "L0"
    if not item.get("contact_path"):
        flags = item.setdefault("risk_flags", [])
        if "missing_contact_path" not in flags:
            flags.append("missing_contact_path")


def _weak_key(item: dict[str, Any]) -> str | None:
    community = item.get("community")
    price = item.get("price_monthly")
    bedrooms = item.get("bedrooms")
    area = item.get("area_sqm")
    if _missing(community) or price is None or bedrooms is None:
        return None
    area_bucket = int(float(area) // 5 * 5) if area else 0
    return f"{community}|{price}|{bedrooms}|{area_bucket}"


def _risk_flags(item: dict[str, Any]) -> list[str]:
    flags = []
    if not item.get("page_opened"):
        flags.append("snippet_only")
    if item.get("listing_status_hint") in {"expired", "leased"}:
        flags.append(str(item["listing_status_hint"]))
    if not item.get("contact_path"):
        flags.append("missing_contact_path")
    return flags


def _priority_order(priority: str | None) -> int:
    return {"A": 0, "B": 1, "C": 2}.get(priority or "C", 2)


def _trust_order(trust: str | None) -> int:
    return {"L3": 3, "L2": 2, "L1": 1, "L0": 0}.get(trust or "L0", 0)


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    found = re.search(r"\d{3,6}", str(value))
    return int(found.group(0)) if found else None


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    found = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(found.group(0)) if found else None


def _parse_bedrooms(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    found = re.search(r"(\d+)\s*(?:室|居)", text)
    if found:
        return int(found.group(1))
    if "一居" in text:
        return 1
    if "二居" in text or "两居" in text:
        return 2
    return None


def _missing(value: Any) -> bool:
    return value is None or value == "" or value == "待核验" or value == "unknown"
