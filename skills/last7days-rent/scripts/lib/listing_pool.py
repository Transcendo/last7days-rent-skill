from __future__ import annotations

import hashlib
from pathlib import Path
import re
from urllib.parse import urlparse, urlunparse
from typing import Any

from .schema import now_iso
from .store import read_json, write_json


def empty_pool(pool_id: str = "jd-hq-beijing", scenario: str = "beijing_jd_hq_anchor_example") -> dict[str, Any]:
    now = now_iso()
    return {
        "pool_meta": {"pool_id": pool_id, "scenario": scenario, "created_at": now, "updated_at": now},
        "profile_summary": {},
        "execution_summary": {},
        "source_coverage": {},
        "rejected_items": [],
        "listings": [],
    }


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
    pool["execution_summary"] = evidence.get("execution_summary", {})
    pool["source_coverage"] = _source_coverage(evidence)
    rejected = {item.get("evidence_id"): dict(item) for item in pool.get("rejected_items", []) if item.get("evidence_id")}
    listings = {item["listing_id"]: dict(item) for item in pool.get("listings", [])}
    by_weak = {_weak_key(item): item["listing_id"] for item in listings.values() if _weak_key(item)}
    for raw in evidence.get("items", []):
        if _is_rejected_evidence(raw):
            rejected[raw.get("evidence_id") or f"rejected-{len(rejected) + 1}"] = _rejected_from_evidence(raw)
            continue
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
    pool["rejected_items"] = sorted(rejected.values(), key=lambda item: item.get("observed_at") or "")
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
        "batch_id": item.get("batch_id"),
        "query_id": item.get("query_id"),
        "query": item.get("query"),
        "source_name": item.get("source_name"),
        "source_domain": source_domain,
        "source_type": item.get("source_type"),
        "source_tier": item.get("source_tier"),
        "source_url": item["source_url"],
        "canonical_url": canonical,
        "observed_at": now,
        "page_opened": bool(item.get("page_opened")),
        "url_class": item.get("url_class"),
        "listing_candidate_status": item.get("listing_candidate_status"),
        "visible_fields": visible,
        "normalized_fields": {"price_monthly": price, "area_sqm": area, "bedrooms": bedrooms},
        "contact_path": contact_path,
        "raw_excerpt": item.get("raw_excerpt"),
        "reject_reasons": item.get("reject_reasons", []),
    }
    listing_id = "listing-" + hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return {
        "listing_id": listing_id,
        "status": "new",
        "priority": "A",
        "recommendation_band": "lead_pool",
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
        "source_tiers": [item.get("source_tier") or "unknown"],
        "contact_path": contact_path,
        "risk_flags": _risk_flags(item),
        "next_actions": ["确认仍在租", "确认费用条款", "确认看房时间"],
        "first_seen_at": now,
        "last_seen_at": now,
        "last_opened_at": now if item.get("page_opened") else None,
        "evidence_count": 1,
        "match_score": 0.0,
        "risk_score": 0.0,
        "observations": [observation],
    }


def _merge_listing(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged["last_seen_at"] = incoming.get("last_seen_at") or now_iso()
    for key in ["source_names", "source_urls", "source_domains", "source_tiers", "commute_tags", "risk_flags", "next_actions"]:
        values = list(merged.get(key, []))
        for value in incoming.get(key, []):
            if value and value not in values:
                values.append(value)
        merged[key] = values
    merged.setdefault("observations", []).extend(incoming.get("observations", []))
    merged["evidence_count"] = len(merged.get("observations", []))
    if incoming.get("last_opened_at"):
        merged["last_opened_at"] = incoming["last_opened_at"]
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
    visible_count = _visible_core_field_count(item)
    if item.get("status") in {"contacted", "scheduled", "viewed"}:
        item["trust_level"] = "L3"
    elif len(independent_domains) >= 2 and visible_count >= 3:
        item["trust_level"] = "L2"
    elif opened and visible_count >= 3:
        item["trust_level"] = "L1"
    else:
        item["trust_level"] = "L0"
    item["evidence_count"] = len(observations)
    item["last_opened_at"] = max((obs.get("observed_at") for obs in observations if obs.get("page_opened") and obs.get("observed_at")), default=item.get("last_opened_at"))
    item["recommendation_band"] = "main" if _trust_order(item.get("trust_level")) >= 1 else "lead_pool"
    item["match_score"] = _match_score(item)
    item["risk_score"] = _risk_score(item)
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
    flags = list(item.get("risk_flags", []))
    if not item.get("page_opened"):
        flags.append("snippet_only")
    if item.get("listing_status_hint") in {"expired", "leased"}:
        flags.append(str(item["listing_status_hint"]))
    if not item.get("contact_path"):
        flags.append("missing_contact_path")
    visible = item.get("visible_fields") or {}
    raw = " ".join(str(value) for value in [item.get("title"), item.get("snippet"), item.get("raw_excerpt"), *visible.values()] if value)
    for needle, flag in [
        ("商水商电", "commercial_utilities"),
        ("隔断", "partition_risk"),
        ("二房东", "sublessor_authorization_needed"),
        ("服务费", "service_fee_unclear"),
        ("中介费", "agency_fee_unclear"),
        ("班车", "shuttle_needs_verification"),
    ]:
        if needle in raw and flag not in flags:
            flags.append(flag)
    return flags


def _is_rejected_evidence(item: dict[str, Any]) -> bool:
    status = str(item.get("listing_candidate_status") or "").lower()
    url_class = str(item.get("url_class") or "").lower()
    return status in {"blocked", "rejected", "blocked_page", "rejected_page"} or any(
        token in url_class for token in ["login", "captcha", "app_wall", "app-wall"]
    )


def _rejected_from_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": item.get("evidence_id"),
        "batch_id": item.get("batch_id"),
        "query_id": item.get("query_id"),
        "source_name": item.get("source_name"),
        "source_url": item.get("source_url"),
        "url_class": item.get("url_class"),
        "observed_at": item.get("observed_at") or now_iso(),
        "title": item.get("title"),
        "reject_reasons": item.get("reject_reasons") or [item.get("listing_candidate_status") or "blocked_or_rejected"],
    }


def _source_coverage(evidence: dict[str, Any]) -> dict[str, Any]:
    by_source: dict[str, dict[str, Any]] = {}
    for source_id, info in _planned_sources(evidence).items():
        entry = _coverage_entry(by_source, source_id)
        entry["planned_queries"] += int(info.get("planned_queries") or 0)
        entry["planned_batches"] = sorted(set(entry.get("planned_batches", [])) | set(info.get("planned_batches", [])))
        entry["source_tiers"] = sorted(set(entry.get("source_tiers", [])) | set(info.get("source_tiers", [])))

    _apply_source_attempts(by_source, evidence)

    for item in evidence.get("items", []):
        source = _source_key(item)
        entry = _coverage_entry(by_source, source, item.get("source_name"))
        entry["items_seen"] += 1
        if not _is_rejected_evidence(item):
            entry["accepted_items"] += 1
        if item.get("page_opened"):
            entry["detail_pages_opened"] += 1
        if _is_rejected_evidence(item):
            entry["rejected_or_blocked"] += 1
            _append_unique(entry["blocked_reasons"], *(item.get("reject_reasons") or [item.get("listing_candidate_status") or item.get("url_class") or "blocked_or_rejected"]))
        query_id = item.get("query_id")
        if query_id:
            entry.setdefault("_attempted_query_ids", set()).add(str(query_id))
        for key, field in [("domains", "source_domain"), ("source_tiers", "source_tier")]:
            value = item.get(field)
            if value and value not in entry[key]:
                entry[key].append(value)
    for entry in by_source.values():
        if entry.get("attempted_queries") is None and entry.get("_attempted_query_ids"):
            entry["attempted_queries"] = len(entry["_attempted_query_ids"])
            entry["attempt_status"] = "inferred_from_items"
        entry.pop("_attempted_query_ids", None)
        entry["blocked_reasons"] = sorted(set(str(reason) for reason in entry.get("blocked_reasons", []) if reason))
        entry["zero_yield_reasons"] = sorted(set(str(reason) for reason in entry.get("zero_yield_reasons", []) if reason))
    return {
        "source_count": len(by_source),
        "planned_source_count": sum(1 for info in by_source.values() if info.get("planned_queries", 0) > 0),
        "effective_source_count": sum(1 for info in by_source.values() if info.get("accepted_items", 0) > 0),
        "sources": by_source,
    }


SOURCE_LABELS = {
    "fang": "房天下",
    "beike_lianjia": "贝壳/链家",
    "lianjia_mobile_list": "链家移动列表",
    "wellcee": "Wellcee",
    "anjuke_58": "58/安居客",
    "douban_public_group": "豆瓣公开小组",
    "ziroom": "自如",
    "lefull": "乐乎",
    "inboyu": "泊寓",
    "brand_apartment_public": "品牌公寓",
    "official_verifier": "官方核验",
}


def _coverage_entry(by_source: dict[str, dict[str, Any]], source_id: str, source_name: Any = None) -> dict[str, Any]:
    display_name = str(source_name or SOURCE_LABELS.get(source_id) or source_id)
    return by_source.setdefault(
        source_id,
        {
            "source_id": source_id,
            "source_name": display_name,
            "planned_queries": 0,
            "planned_batches": [],
            "attempted_queries": None,
            "attempt_status": "not_logged",
            "items_seen": 0,
            "accepted_items": 0,
            "detail_pages_opened": 0,
            "rejected_or_blocked": 0,
            "blocked_reasons": [],
            "zero_yield_reasons": [],
            "domains": [],
            "source_tiers": [],
        },
    )


def _planned_sources(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    brief = evidence.get("search_brief") if isinstance(evidence.get("search_brief"), dict) else None
    if brief is None:
        brief = _load_brief_from_context(evidence.get("query_context") or {})
    planned: dict[str, dict[str, Any]] = {}
    if not isinstance(brief, dict):
        return planned
    for batch in brief.get("search_batches", []):
        if not isinstance(batch, dict):
            continue
        batch_id = str(batch.get("batch_id") or "unknown_batch")
        source_tier = str(batch.get("source_tier") or "")
        for query in batch.get("queries", []):
            if not isinstance(query, dict):
                continue
            for raw_source in query.get("sources") or batch.get("sources") or []:
                source_id = _normalize_source_id(raw_source)
                entry = planned.setdefault(source_id, {"planned_queries": 0, "planned_batches": [], "source_tiers": []})
                entry["planned_queries"] += 1
                _append_unique(entry["planned_batches"], batch_id)
                if source_tier:
                    _append_unique(entry["source_tiers"], source_tier)
    return planned


def _load_brief_from_context(query_context: dict[str, Any]) -> dict[str, Any] | None:
    brief_path = query_context.get("brief_path") if isinstance(query_context, dict) else None
    if not brief_path:
        return None
    path = Path(str(brief_path)).expanduser()
    try:
        return read_json(path)
    except (OSError, ValueError):
        return None


def _apply_source_attempts(by_source: dict[str, dict[str, Any]], evidence: dict[str, Any]) -> None:
    for attempt in evidence.get("source_attempts", []):
        if not isinstance(attempt, dict):
            continue
        sources = attempt.get("sources") or [attempt.get("source_id") or attempt.get("source_name")]
        for raw_source in [source for source in sources if source]:
            entry = _coverage_entry(by_source, _normalize_source_id(raw_source), raw_source)
            entry["attempted_queries"] = (entry.get("attempted_queries") or 0) + int(attempt.get("attempted_queries") or attempt.get("queries_attempted") or 0)
            entry["attempt_status"] = "logged"
            entry["rejected_or_blocked"] += int(attempt.get("blocked_pages") or attempt.get("blocked_attempts") or 0)
            _append_unique(entry["zero_yield_reasons"], attempt.get("zero_yield_reason"), *(attempt.get("zero_yield_reasons") or []))
            _append_unique(entry["blocked_reasons"], attempt.get("blocked_reason"), *(attempt.get("blocked_reasons") or []))
    for query in evidence.get("attempted_queries", []):
        if not isinstance(query, dict):
            continue
        sources = query.get("source_targets") or query.get("sources") or [query.get("source_id") or query.get("source_name")]
        for raw_source in [source for source in sources if source]:
            entry = _coverage_entry(by_source, _normalize_source_id(raw_source), raw_source)
            entry["attempted_queries"] = (entry.get("attempted_queries") or 0) + 1
            entry["attempt_status"] = "logged"
            entry["rejected_or_blocked"] += int(query.get("blocked_pages") or query.get("blocked_attempts") or 0)
            _append_unique(entry["zero_yield_reasons"], query.get("zero_yield_reason"), *(query.get("zero_yield_reasons") or []))
            _append_unique(entry["blocked_reasons"], query.get("blocked_reason"), *(query.get("blocked_reasons") or []))


def _source_key(item: dict[str, Any]) -> str:
    for value in [item.get("source_id"), item.get("source_name"), item.get("source_domain")]:
        source_id = _normalize_source_id(value)
        if source_id != "unknown":
            return source_id
    return "unknown"


def _normalize_source_id(value: Any) -> str:
    text = str(value or "").strip()
    lower = text.lower()
    if not text:
        return "unknown"
    if lower in SOURCE_LABELS:
        return lower
    if "fang.com" in lower or "房天下" in text:
        return "fang"
    if "m.lianjia.com" in lower or "链家移动" in text:
        return "lianjia_mobile_list"
    if "ke.com" in lower or "lianjia.com" in lower or "贝壳" in text or "链家" in text:
        return "beike_lianjia"
    if "wellcee" in lower:
        return "wellcee"
    if "58" in text or "anjuke" in lower or "安居客" in text:
        return "anjuke_58"
    if "douban" in lower or "豆瓣" in text:
        return "douban_public_group"
    if "lefull" in lower or "乐乎" in text:
        return "lefull"
    if "inboyu" in lower or "泊寓" in text:
        return "inboyu"
    if "ziroom" in lower or "自如" in text:
        return "ziroom"
    if "brand_apartment" in lower or "品牌公寓" in text or "蜂客" in text or "城家" in text or "有巢" in text:
        return "brand_apartment_public"
    return lower.replace(" ", "_")


def _append_unique(values: list[Any], *incoming: Any) -> None:
    for value in incoming:
        if not value:
            continue
        if isinstance(value, list):
            _append_unique(values, *value)
            continue
        text = str(value)
        if text not in values:
            values.append(text)


def _visible_core_field_count(item: dict[str, Any]) -> int:
    checks = [
        not _missing(item.get("price_monthly") or item.get("price_text")),
        not _missing(item.get("community") or item.get("district_hint")),
        not _missing(item.get("area_sqm") or item.get("area_text") or item.get("bedrooms") or item.get("layout_text")),
        bool(item.get("contact_path")),
        bool(item.get("last_seen_at") or item.get("first_seen_at")),
    ]
    return sum(1 for ok in checks if ok)


def _match_score(item: dict[str, Any]) -> float:
    score = 0.0
    if _trust_order(item.get("trust_level")) >= 1:
        score += 0.35
    if item.get("price_monthly"):
        score += 0.2
    if not _missing(item.get("community")):
        score += 0.15
    if item.get("contact_path"):
        score += 0.15
    if item.get("evidence_count", 0) > 1:
        score += 0.15
    return round(min(score, 1.0), 3)


def _risk_score(item: dict[str, Any]) -> float:
    risky = {"snippet_only", "missing_contact_path", "commercial_utilities", "partition_risk", "sublessor_authorization_needed", "service_fee_unclear", "agency_fee_unclear"}
    count = sum(1 for flag in item.get("risk_flags", []) if flag in risky)
    return round(min(count * 0.18, 1.0), 3)


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
