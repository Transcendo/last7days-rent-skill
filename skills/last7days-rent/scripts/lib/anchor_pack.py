from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .schema import RentProfile, now_iso
from .store import read_json


ANCHOR_ROOT = Path(__file__).resolve().parents[2] / "anchor_packs"
DEFAULT_ANCHOR_ID = "beijing-jd-hq-yizhuang"


def load_anchor_pack(anchor_id: str = DEFAULT_ANCHOR_ID) -> dict[str, Any]:
    checked: list[Path] = []
    for root in _anchor_roots():
        path = root / f"{anchor_id}.json"
        checked.append(path)
        data = read_json(path)
        if data:
            return data
    raise FileNotFoundError(f"missing anchor pack: {', '.join(str(path) for path in checked)}")


def build_search_brief(profile: RentProfile | dict[str, Any], anchor_pack: dict[str, Any] | None = None) -> dict[str, Any]:
    data = profile.to_dict() if isinstance(profile, RentProfile) else dict(profile)
    anchor_id = data.get("office_anchor", {}).get("anchor_id") or DEFAULT_ANCHOR_ID
    anchor_pack = anchor_pack or load_anchor_pack(anchor_id)
    profile_constraints = _profile_constraints(data, anchor_pack)
    zones = _zone_map(anchor_pack)
    search_batches = _search_batches(anchor_pack, profile_constraints, zones)
    runtime_budget = _runtime_budget(anchor_pack)
    return {
        "schema_version": "0.3.0",
        "anchor_id": anchor_pack.get("anchor_id", anchor_id),
        "profile_id": "local-current",
        "profile_hash": _profile_hash(data),
        "scenario": data.get("user_goal", {}).get("scenario") or "beijing_jd_hq_anchor_example",
        "generated_at": now_iso(),
        "guide_sources": anchor_pack.get("guide_sources", []),
        "risk_checks": anchor_pack.get("risk_checks", []),
        "profile_summary": _profile_summary(profile_constraints),
        "profile_constraints": profile_constraints,
        "search_batches": search_batches,
        "run_budget": {
            **runtime_budget,
            "target_accepted_listings": runtime_budget["target_main_recommendations"],
            "max_search_batches": len(search_batches),
            "max_queries_per_batch": max((len(batch.get("queries", [])) for batch in search_batches), default=0),
            "expand_if_accepted_below": runtime_budget["expand_if_l1_below"],
        },
        "collection_rules": _collection_rules(anchor_pack),
        "execution_contract": {
            "input": "Agent runtime reads this search brief and executes public web_search/browser_open only.",
            "output": "Agent runtime writes evidence JSON, then CLI validates with ingest --validate.",
            "blocked_policy": "Record login/captcha/app-wall pages in rejected or item.reject_reasons; do not bypass.",
        },
    }


def _anchor_roots() -> list[Path]:
    return [
        ANCHOR_ROOT,
        Path(sys.prefix) / "share" / "last7days-rent-skill" / "anchor_packs",
    ]


def _profile_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def _profile_constraints(data: dict[str, Any], anchor_pack: dict[str, Any]) -> dict[str, Any]:
    housing = data.get("housing_constraints", {})
    commute = data.get("commute_preferences") or data.get("commute") or {}
    risk = data.get("risk_preferences", {})
    anchor = anchor_pack.get("anchor", {})
    bedrooms = housing.get("preferred_bedrooms") or housing.get("min_bedrooms") or 1
    budget_max = housing.get("budget_max") or housing.get("budget_hard_max") or _budget_default(anchor_pack, "max_6000") or 6000
    budget_target = housing.get("budget_target") or _budget_default(anchor_pack, "target_5000") or budget_max
    office_aliases = anchor.get("office_aliases") or anchor_pack.get("aliases") or ["北京京东总部"]
    return {
        "city": anchor_pack.get("city", data.get("office_anchor", {}).get("city") or "北京"),
        "company": anchor_pack.get("company", data.get("office_anchor", {}).get("company") or "京东"),
        "office_anchor": office_aliases[0],
        "office_aliases": office_aliases,
        "address_keywords": anchor.get("address_keywords") or anchor_pack.get("office_keywords", []),
        "needs_confirmation": anchor.get("needs_confirmation", []),
        "budget_target": int(budget_target),
        "budget_max": int(budget_max),
        "preferred_bedrooms": int(bedrooms),
        "bedroom_label": _bedroom_label(bedrooms),
        "commute_minutes": int(commute.get("max_minutes") or commute.get("commute_minutes") or 30),
        "commute_strategy": commute.get("strategy", "near_first"),
        "source_strategy": risk.get("source_strategy", "public_all_channels"),
        "risk_filter": risk.get("risk_filter", "collect_then_user_screen"),
    }


def _profile_summary(profile_constraints: dict[str, Any]) -> dict[str, Any]:
    return {
        "city": profile_constraints["city"],
        "office_anchor": profile_constraints["office_anchor"],
        "bedroom_label": profile_constraints["bedroom_label"],
        "preferred_bedrooms": profile_constraints["preferred_bedrooms"],
        "budget_target": profile_constraints["budget_target"],
        "budget_max": profile_constraints["budget_max"],
        "commute_strategy": profile_constraints["commute_strategy"],
        "source_strategy": profile_constraints["source_strategy"],
        "needs_confirmation": profile_constraints.get("needs_confirmation", []),
    }


def _budget_default(anchor_pack: dict[str, Any], band_id: str) -> int | None:
    for band in anchor_pack.get("budget_bands", []):
        if band.get("band_id") == band_id and band.get("max") is not None:
            return int(band["max"])
    return None


def _zone_map(anchor_pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(zone.get("zone_id")): dict(zone) for zone in anchor_pack.get("commute_zones", []) if zone.get("zone_id")}


def _runtime_budget(anchor_pack: dict[str, Any]) -> dict[str, int]:
    raw = anchor_pack.get("runtime_budget", {})
    return {
        "target_candidates_total": int(raw.get("target_candidates_total", 30)),
        "target_main_recommendations": int(raw.get("target_main_recommendations", 5)),
        "target_l1_or_better": int(raw.get("target_l1_or_better", 8)),
        "max_search_queries": int(raw.get("max_search_queries", 36)),
        "max_results_per_query": int(raw.get("max_results_per_query", 8)),
        "max_detail_pages_total": int(raw.get("max_detail_pages_total", 40)),
        "max_detail_pages_per_source": int(raw.get("max_detail_pages_per_source", 8)),
        "expand_if_l1_below": int(raw.get("expand_if_l1_below", 5)),
        "stop_after_consecutive_empty_batches": int(raw.get("stop_after_consecutive_empty_batches", 2)),
    }


def _collection_rules(anchor_pack: dict[str, Any]) -> dict[str, Any]:
    entry_policy = anchor_pack.get("entry_policy", {})
    l1_required = entry_policy.get("l1_required", {})
    return {
        "l0_policy": entry_policy.get("l0_policy", "lead_pool_only"),
        "main_recommendation_min_trust": entry_policy.get("main_recommendation_min_trust", "L1"),
        "l1_requires_page_opened": bool(l1_required.get("page_opened", True)),
        "min_visible_core_fields_for_l1": int(l1_required.get("min_visible_core_fields", 3)),
        "required_fields_for_l1": l1_required.get("required_fields", ["source_url", "observed_at", "raw_excerpt"]),
        "must_capture": [
            "evidence_id",
            "batch_id",
            "query_id",
            "query",
            "source_url",
            "source_name",
            "source_type",
            "page_opened",
            "raw_excerpt",
            "observed_at",
        ],
        "capture_when_visible": ["price_text", "area_text", "layout_text", "community", "district_hint", "contact_path", "published_at"],
        "privacy": [
            "不公开原发帖人身份",
            "不保存 cookie/token/session",
            "不自动读取微信群/公司群/校友群",
            "公开联系方式优先展示平台入口或 contact_path",
        ],
    }


def _search_batches(anchor_pack: dict[str, Any], profile_constraints: dict[str, Any], zones: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    budget = _runtime_budget(anchor_pack)
    for index, source_group in enumerate(anchor_pack.get("source_matrix", []), start=1):
        queries = _queries_for_source_group(source_group, profile_constraints, zones, budget["max_results_per_query"])
        if not queries:
            continue
        batches.append(
            {
                "batch_id": source_group.get("batch_id") or f"batch_{index}",
                "intent": _primary_intent(source_group),
                "intents": source_group.get("intents", []),
                "priority": index,
                "source_tier": source_group.get("source_tier", "P1"),
                "sources": source_group.get("sources") or [source_group.get("source_name")],
                "source_name": source_group.get("source_name"),
                "zone_ids": source_group.get("zone_ids", []),
                "goal": _batch_goal(source_group),
                "queries": queries,
                "max_results_per_query": budget["max_results_per_query"],
                "max_detail_pages": int(source_group.get("max_detail_pages") or budget["max_detail_pages_per_source"]),
                "detail_open_policy": source_group.get("detail_open_policy", "open_detail_or_list_items_first"),
                "expected_output": {
                    "url_classes": source_group.get("expected_url_classes", []),
                    "candidate_policy": "L1 only after page_opened and enough visible fields; otherwise L0 lead pool.",
                },
            }
        )
    return batches


def _queries_for_source_group(
    source_group: dict[str, Any],
    profile_constraints: dict[str, Any],
    zones: dict[str, dict[str, Any]],
    max_results_per_query: int,
) -> list[dict[str, Any]]:
    query_templates = source_group.get("query_templates", [])
    zone_ids = source_group.get("zone_ids") or list(zones.keys())
    target_count = int(source_group.get("target_query_count") or len(query_templates) or max_results_per_query)
    queries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for zone_id in zone_ids:
        zone = zones.get(zone_id)
        if not zone:
            continue
        keywords = list(zone.get("keywords", [])) or [zone.get("label") or zone_id]
        for keyword in keywords:
            for template in query_templates:
                query_text = _format_query(template, profile_constraints, zone=zone, keyword=keyword)
                if query_text in seen:
                    continue
                seen.add(query_text)
                queries.append(
                    {
                        "query_id": f"{source_group.get('batch_id', 'batch')}-q{len(queries) + 1:02d}",
                        "query": query_text,
                        "zone_id": zone_id,
                        "zone_label": zone.get("label", zone_id),
                        "community": keyword,
                        "intent": _primary_intent(source_group),
                        "sources": _sources_for_query(template, source_group.get("sources", [])),
                        "expected_url_classes": source_group.get("expected_url_classes", []),
                    }
                )
                if len(queries) >= target_count:
                    return queries
    return queries


def _format_query(template: str, profile_constraints: dict[str, Any], *, zone: dict[str, Any], keyword: str) -> str:
    replacements = {
        "city": profile_constraints["city"],
        "office_alias": profile_constraints["office_anchor"],
        "bedroom_label": profile_constraints["bedroom_label"],
        "budget_max": profile_constraints["budget_max"],
        "zone": keyword,
        "community": keyword,
    }
    return template.format(**replacements)


def _sources_for_query(template: str, fallback_sources: list[str]) -> list[str]:
    text = template.lower()
    if "fang.com" in text or "房天下" in template:
        return ["fang"]
    if "m.lianjia.com" in text:
        return ["lianjia_mobile_list"]
    if "m.ke.com" in text or "lianjia.com" in text:
        return ["beike_lianjia"]
    if "wellcee" in text:
        return ["wellcee"]
    if "anjuke" in text or "58.com" in text:
        return ["anjuke_58"]
    if "douban" in text:
        return ["douban_public_group"]
    if "lefull" in text or "乐乎" in template:
        return ["lefull"]
    if "inboyu" in text or "泊寓" in template:
        return ["inboyu"]
    if any(token in template for token in ["蜂客", "城家", "有巢", "品牌公寓"]):
        return ["brand_apartment_public"]
    if "自如" in template or "ziroom" in text:
        return ["ziroom"]
    return list(fallback_sources)


def _primary_intent(source_group: dict[str, Any]) -> str:
    intents = source_group.get("intents") or ["specific_listing"]
    return str(intents[0])


def _batch_goal(source_group: dict[str, Any]) -> str:
    labels = {
        "p0_price_anchor": "建立平台价格锚点并发现可打开详情页",
        "near_office": "获取经海路/近场公开房源线索",
        "main_residential": "获取次渠/次渠南主力住宅圈公开房源",
        "space_budget_backup": "候选不足时扩展马驹桥等面积/预算备选圈",
        "transfer_personal": "发现公开转租/个人房源帖子并打开正文核验",
        "brand_apartment": "发现品牌公寓和短期过渡选项",
    }
    batch_id = source_group.get("batch_id")
    return labels.get(batch_id, str(source_group.get("source_name") or batch_id or "公开获源"))


def _bedroom_label(bedrooms: Any) -> str:
    try:
        count = int(bedrooms)
    except (TypeError, ValueError):
        return "独立整租"
    return {1: "一居室", 2: "二居室", 3: "三居室"}.get(count, f"{count}居室")
