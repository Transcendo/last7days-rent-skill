from __future__ import annotations

import json
from pathlib import Path

from .privacy import assert_public_safe, redact_profile, sanitize_cluster
from .schema import ListingCluster, RentProfile, VerificationEvidence, to_plain
from .seven_day_plan import build_seven_day_plan
from .sources.registry import source_registry
from .store import write_json, write_text


def render_chat_shortlist(profile: RentProfile, clusters: list[ListingCluster]) -> str:
    city = profile.office_anchor.get("city") or "unknown"
    office = profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint") or "unknown"
    budget = profile.housing_constraints.get("budget_max") or "unknown"
    lines = [f"近 7 天候选房源：{city} / {office} / 预算 {budget}", ""]
    if not clusters:
        lines.append("未找到可进入 MVP 短名单的 P0 候选。")
    for idx, cluster in enumerate(clusters, start=1):
        item = cluster.canonical_listing
        price = f"{item.price_monthly} 元/月" if item.price_monthly is not None else "unknown"
        lines.extend(
            [
                f"{idx}. [{cluster.trust_level}] {item.title}，{price}",
                f"   匹配：{'；'.join(cluster.match_reasons)}",
                f"   风险：{', '.join(cluster.risk_flags) if cluster.risk_flags else '未发现高风险标签'}",
                f"   下一步：{cluster.next_questions[0] if cluster.next_questions else '联系前核验是否仍在租'}",
                "",
            ]
        )
    output = "\n".join(lines).rstrip() + "\n"
    assert_public_safe(output)
    return output


def render_markdown_report(
    profile: RentProfile,
    clusters: list[ListingCluster],
    evidences: list[VerificationEvidence],
    warnings: list[str],
) -> str:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    data = redact_profile(profile.to_dict())
    lines = [
        "# last7days-rent 候选短名单",
        "",
        "last7days = 帮助用户 7 天完成租房",
        "",
        "## Profile 脱敏摘要",
        "",
        f"- 办公点: {data['office_anchor'].get('office_name') or 'unknown'}",
        f"- 城市: {data['office_anchor'].get('city') or 'unknown'}",
        f"- 通勤上限: {data['commute'].get('max_minutes', 'unknown')} 分钟",
        f"- 预算: {data['housing_constraints'].get('budget_min') or 'unknown'} - {data['housing_constraints'].get('budget_max') or 'unknown'}",
        "",
        "## P0 Source Coverage",
        "",
    ]
    registry = source_registry()
    for source_id in ["beike_lianjia", "wellcee", "fang", "official_verifier"]:
        meta = registry[source_id]
        lines.append(f"- {source_id}: {meta['status']} / {meta['allowed_output_type']} / default {meta['default_trust_level']}")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(["", "## 候选房源短名单", ""])
    for idx, cluster in enumerate(safe_clusters, start=1):
        item = cluster.canonical_listing
        price = f"{item.price_monthly} 元/月" if item.price_monthly is not None else "unknown"
        lines.extend(
            [
                f"### {idx}. [{cluster.trust_level}] {item.title}",
                "",
                f"- 月租: {price}",
                f"- 来源: {item.source_id}",
                f"- URL: {item.source_url or 'unknown'}",
                f"- 匹配理由: {'；'.join(cluster.match_reasons)}",
                f"- 风险标签: {', '.join(cluster.risk_flags) if cluster.risk_flags else 'none'}",
                f"- 合并原因: {', '.join(cluster.merge_reasons) if cluster.merge_reasons else '单源结构化'}",
                f"- 字段 provenance: `{json.dumps(cluster.field_provenance, ensure_ascii=False, sort_keys=True)}`",
                "- 下一步核验问题:",
            ]
        )
        lines.extend(f"  - {question}" for question in cluster.next_questions)
        lines.append("")
    lines.extend(["## 官方核验证据", ""])
    if evidences:
        for evidence in evidences:
            lines.append(f"- {evidence.evidence_type}: {evidence.value or 'unknown'} ({evidence.url or 'unknown'})")
    else:
        lines.append("- unknown")
    lines.extend(["", "## 7 天租房行动计划", ""])
    for step in build_seven_day_plan():
        lines.append(f"- {step['day']}: {step['action']}")
    lines.extend(
        [
            "",
            "## 隐私说明",
            "",
            "公开报告已脱敏手机号、微信号、群名、真实姓名、头像或截图来源身份线索。缺失字段保持 unknown/None，不由 LLM 或代码补全。L1 不是已验真，L3 只来自用户联系确认或明确反馈。",
        ]
    )
    output = "\n".join(lines).rstrip() + "\n"
    assert_public_safe(output)
    return output


def render_evidence_package(
    profile: RentProfile,
    clusters: list[ListingCluster],
    evidences: list[VerificationEvidence],
    warnings: list[str],
) -> dict:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    package = {
        "schema_version": "0.1.0",
        "slogan": "last7days = 帮助用户 7 天完成租房",
        "profile_redacted_summary": redact_profile(profile.to_dict()),
        "source_coverage": source_registry(),
        "clusters": [cluster.to_dict() for cluster in safe_clusters],
        "verification_evidence": [to_plain(evidence) for evidence in evidences],
        "seven_day_plan": build_seven_day_plan(),
        "warnings": warnings,
        "privacy": {
            "redacted": True,
            "no_plain_phone_wechat_group_real_name": True,
            "unknown_fields_are_not_filled": True,
        },
    }
    assert_public_safe(json.dumps(package, ensure_ascii=False, sort_keys=True))
    return package


def write_outputs(
    reports_dir: Path,
    basename: str,
    markdown: str,
    evidence: dict,
) -> tuple[Path, Path]:
    markdown_path = reports_dir / f"{basename}.md"
    evidence_path = reports_dir / f"{basename}.json"
    write_text(markdown_path, markdown)
    write_json(evidence_path, evidence)
    return markdown_path, evidence_path
