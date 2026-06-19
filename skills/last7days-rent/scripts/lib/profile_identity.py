from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .env import LocalPaths


def profile_hash(profile: dict[str, Any]) -> str:
    payload = json.dumps(profile, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def profile_slug(profile: dict[str, Any]) -> str:
    office = profile.get("office_anchor") if isinstance(profile.get("office_anchor"), dict) else {}
    raw = (
        office.get("anchor_id")
        or " ".join(
            str(value)
            for value in [
                office.get("city"),
                office.get("company"),
                office.get("campus_name") or office.get("office_name"),
            ]
            if value
        )
        or "profile"
    )
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(raw).strip().lower()).strip("-")
    return f"{slug or 'profile'}-{profile_hash(profile)[:8]}"


def default_brief_path(paths: LocalPaths, profile: dict[str, Any]) -> Path:
    return paths.state_dir / "refresh" / f"{profile_slug(profile)}.search-brief.json"


def default_pool_path(paths: LocalPaths, profile: dict[str, Any]) -> Path:
    return paths.pools_dir / f"{profile_slug(profile)}.listing-pool.json"


def default_report_path(paths: LocalPaths, profile: dict[str, Any]) -> Path:
    return paths.reports_dir / f"{profile_slug(profile)}-rentals.html"


def profile_summary_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    office = profile.get("office_anchor") if isinstance(profile.get("office_anchor"), dict) else {}
    housing = profile.get("housing_constraints") if isinstance(profile.get("housing_constraints"), dict) else {}
    commute = profile.get("commute_preferences") if isinstance(profile.get("commute_preferences"), dict) else {}
    risk = profile.get("risk_preferences") if isinstance(profile.get("risk_preferences"), dict) else {}
    bedrooms = housing.get("preferred_bedrooms") or housing.get("min_bedrooms")
    return {
        "profile_hash": profile_hash(profile),
        "profile_slug": profile_slug(profile),
        "city": office.get("city"),
        "company": office.get("company"),
        "office_anchor": office.get("campus_name") or office.get("office_name") or office.get("anchor_id"),
        "office_anchor_id": office.get("anchor_id"),
        "nearest_metro": office.get("nearest_metro", []),
        "budget_target": housing.get("budget_target"),
        "budget_max": housing.get("budget_max") or housing.get("budget_hard_max"),
        "preferred_bedrooms": bedrooms,
        "bedroom_label": _bedroom_label(bedrooms),
        "commute_minutes": commute.get("max_minutes"),
        "commute_strategy": commute.get("strategy"),
        "source_strategy": risk.get("source_strategy"),
        "risk_filter": risk.get("risk_filter"),
    }


def attach_profile_to_pool(pool: dict[str, Any], profile: dict[str, Any], *, brief_path: str | Path | None = None) -> dict[str, Any]:
    summary = dict(pool.get("profile_summary") or {})
    summary.update({key: value for key, value in profile_summary_from_profile(profile).items() if value not in (None, "", [])})
    if brief_path:
        summary["brief_path"] = str(brief_path)
    meta = pool.setdefault("pool_meta", {})
    meta["profile_hash"] = profile_hash(profile)
    meta["profile_slug"] = profile_slug(profile)
    meta["pool_id"] = meta.get("pool_id") or profile_slug(profile)
    pool["profile_summary"] = summary
    return pool


def all_channel_matrix() -> list[dict[str, Any]]:
    return [
        {
            "channel": "公开租房平台",
            "examples": ["贝壳/链家", "58/安居客", "房天下", "自如/我爱我家等公开入口"],
            "discovery": "Agent runtime 可用公开 web search/browser 自动发现和打开公开页面",
            "allowed": True,
        },
        {
            "channel": "品牌公寓公开页",
            "examples": ["乐乎", "泊寓", "城家", "有巢等公开页面"],
            "discovery": "Agent runtime 可自动发现公开入口，登录、预约、验证码流程留给用户",
            "allowed": True,
        },
        {
            "channel": "公开转租社区",
            "examples": ["豆瓣公开小组", "Wellcee", "公开帖子/文章"],
            "discovery": "仅采集公开可见正文和平台联系入口，默认更严格标风险",
            "allowed": True,
        },
        {
            "channel": "用户授权导入",
            "examples": ["用户给的链接", "截图", "复制文本", "本地整理材料"],
            "discovery": "只能由用户显式提供或授权导入，不自动读取私域内容",
            "allowed": True,
        },
        {
            "channel": "私域或登录后内容",
            "examples": ["微信群", "公司群", "朋友圈", "登录后页面", "验证码后内容"],
            "discovery": "不自动采集，不绕登录，不保存 cookie/token",
            "allowed": False,
        },
    ]


def source_policy_matrix() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "public_platforms",
            "source_name": "公开租房平台",
            "status": "planned",
            "policy_note": "贝壳/链家、58/安居客、房天下、自如等公开入口可由 Agent runtime 自动发现公开页面。",
        },
        {
            "source_id": "brand_apartment_public",
            "source_name": "品牌公寓公开页",
            "status": "planned",
            "policy_note": "乐乎、泊寓、城家、有巢等公开页可搜索；登录、预约、验证码不自动绕过。",
        },
        {
            "source_id": "douban_wellcee_public",
            "source_name": "公开转租社区",
            "status": "planned",
            "policy_note": "豆瓣公开小组、Wellcee 等公开正文可整理为 evidence，默认更严格标风险。",
        },
        {
            "source_id": "user_authorized_import",
            "source_name": "用户授权导入",
            "status": "user_authorized_only",
            "policy_note": "用户给的链接、截图、复制文本或本地材料可以导入；不会主动读取私域内容。",
        },
        {
            "source_id": "xiaohongshu",
            "source_name": "小红书",
            "status": "roadmap_not_enabled",
            "policy_note": "当前不自动抓取；后续如支持也只接受公开可访问或用户授权输入。",
        },
        {
            "source_id": "wechat_public",
            "source_name": "公众号/微信公开内容",
            "status": "user_authorized_only",
            "policy_note": "只处理用户提供的公开文章链接、截图或复制文本，不自动读取微信内容。",
        },
        {
            "source_id": "weibo",
            "source_name": "微博",
            "status": "roadmap_not_enabled",
            "policy_note": "当前不纳入自动公开发现，避免高噪声和登录态依赖。",
        },
        {
            "source_id": "private_groups",
            "source_name": "微信群/公司群/朋友圈",
            "status": "policy_disabled",
            "policy_note": "私域内容不自动采集，不保存或公开原发帖人真实身份。",
        },
    ]


def _bedroom_label(bedrooms: Any) -> str | None:
    if bedrooms in (None, ""):
        return None
    try:
        count = int(bedrooms)
    except (TypeError, ValueError):
        return str(bedrooms)
    return {1: "一居室", 2: "二居室", 3: "三居室"}.get(count, f"{count}居室")
