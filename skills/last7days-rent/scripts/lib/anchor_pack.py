from __future__ import annotations

import hashlib
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
    anchor_pack = anchor_pack or load_anchor_pack(data.get("office_anchor", {}).get("anchor_id") or DEFAULT_ANCHOR_ID)
    profile_hash = hashlib.sha1(repr(sorted(data.items())).encode("utf-8")).hexdigest()[:12]
    housing = data.get("housing_constraints", {})
    commute = data.get("commute_preferences") or data.get("commute") or {}
    risk = data.get("risk_preferences", {})
    bedrooms = housing.get("preferred_bedrooms") or housing.get("min_bedrooms") or 1
    bedroom_label = _bedroom_label(bedrooms)
    budget_max = housing.get("budget_max") or housing.get("budget_target") or 5000
    budget_target = housing.get("budget_target") or budget_max
    priority_zones = list(commute.get("derived_zones_priority") or _zones(anchor_pack, ["near_office", "value_residential"]))
    backup_zones = list(commute.get("expand_zones_if_sparse") or _zones(anchor_pack, ["budget_backup"]))
    office_alias = anchor_pack.get("aliases", ["北京京东总部"])[0]
    preferred_sources = _preferred_sources(risk)
    return {
        "schema_version": "0.2.0-poc",
        "profile_id": "local-current",
        "profile_hash": profile_hash,
        "scenario": data.get("user_goal", {}).get("scenario") or "jd_hq_beijing_poc",
        "generated_at": now_iso(),
        "profile_summary": {
            "city": anchor_pack.get("city", "北京"),
            "office_anchor": office_alias,
            "bedroom_label": bedroom_label,
            "preferred_bedrooms": bedrooms,
            "budget_target": budget_target,
            "budget_max": budget_max,
            "commute_strategy": commute.get("strategy", "balanced"),
            "source_strategy": risk.get("source_strategy", "platforms_plus_personal"),
        },
        "search_batches": [
            {
                "id": "structured_platforms",
                "goal": f"获取平台型{bedroom_label}/整租线索",
                "queries": _platform_queries(office_alias, bedroom_label, budget_max, priority_zones),
                "preferred_sources": [source for source in ["58", "安居客", "贝壳", "链家", "自如", "我爱我家"] if source in preferred_sources or risk.get("source_strategy") != "personal_first"],
            },
            {
                "id": "community_posts",
                "goal": "获取个人转租/房东直租线索",
                "queries": _community_queries(office_alias, bedroom_label, priority_zones),
                "preferred_sources": ["豆瓣公开小组", "公开文章"],
            },
            {
                "id": "anchor_validation",
                "goal": "核验办公锚点和通勤圈",
                "queries": [f"{office_alias} 地址 经海路 科创十一街", f"{office_alias} 经海路 地铁 步行"],
                "preferred_sources": ["官方地图", "公开地图", "公司公开信息"],
            },
            {
                "id": "expanded_zones",
                "goal": "候选不足时扩圈",
                "queries": [f"北京 {zone} {bedroom_label} {budget_max} 租房 京东总部" for zone in backup_zones[:6]],
                "preferred_sources": ["58", "安居客", "贝壳", "链家", "公开文章"],
                "run_if": "accepted_listings_below_expand_threshold",
            },
        ],
        "run_budget": {
            "target_accepted_listings": 10,
            "max_search_batches": 4,
            "max_queries_per_batch": 6,
            "max_results_per_query": 8,
            "max_detail_pages_total": 20,
            "max_detail_pages_per_source": 5,
            "expand_if_accepted_below": 6,
            "stop_after_consecutive_empty_batches": 2,
        },
        "collection_rules": {
            "must_capture": ["source_url", "title", "snippet", "observed_at", "source_name", "batch_id", "query_id", "page_opened", "raw_excerpt"],
            "capture_when_visible": ["price_text", "area_text", "layout_text", "community", "district_hint", "contact_path"],
            "privacy": ["不公开原发帖人身份", "不保存 cookie/token/session", "公开联系方式只作为 contact_path，报告中优先展示平台入口"],
        },
    }


def _anchor_roots() -> list[Path]:
    return [
        ANCHOR_ROOT,
        Path(sys.prefix) / "share" / "last7days-rent-skill" / "anchor_packs",
    ]


def _zones(anchor_pack: dict[str, Any], zone_ids: list[str]) -> list[str]:
    zones: list[str] = []
    for zone in anchor_pack.get("commute_zones", []):
        if zone.get("zone_id") in zone_ids:
            zones.extend(zone.get("keywords", []))
    return zones


def _bedroom_label(bedrooms: Any) -> str:
    try:
        count = int(bedrooms)
    except (TypeError, ValueError):
        return "独立整租"
    return {1: "一居室", 2: "二居室", 3: "三居室"}.get(count, f"{count}居室")


def _platform_queries(office_alias: str, bedroom_label: str, budget_max: int, zones: list[str]) -> list[str]:
    queries = [f"北京 {office_alias} {bedroom_label} {budget_max}以内 租房 亦庄"]
    queries.extend(f"北京 {zone} {bedroom_label} {budget_max} 租房" for zone in zones[:5])
    return queries[:6]


def _community_queries(office_alias: str, bedroom_label: str, zones: list[str]) -> list[str]:
    terms = zones[:3] or ["经海路", "亦庄"]
    return [f"site:douban.com/group {term} 租房 {office_alias} {bedroom_label}" for term in terms]


def _preferred_sources(risk: dict[str, Any]) -> list[str]:
    raw = risk.get("preferred_sources") or []
    mapping = {
        "ke": "贝壳",
        "lianjia": "链家",
        "ziroom": "自如",
        "5i5j": "我爱我家",
        "58": "58",
        "anjuke": "安居客",
    }
    return [mapping.get(str(item), str(item)) for item in raw]
