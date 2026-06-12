from __future__ import annotations

import json
from pathlib import Path

from .acquisition import AcquisitionResult
from .contact import contact_display_text
from .privacy import assert_public_safe, redact_profile, sanitize_cluster
from .schema import ListingCluster, RentProfile, SourceFetchResult, VerificationEvidence, to_plain
from .seven_day_plan import build_seven_day_plan
from .sources.registry import source_registry
from .store import write_json, write_text


def render_chat_shortlist(profile: RentProfile, clusters: list[ListingCluster], *, acquisition: AcquisitionResult | None = None) -> str:
    city = profile.office_anchor.get("city") or "unknown"
    office = profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint") or "unknown"
    budget = profile.housing_constraints.get("budget_max") or "unknown"
    lines = [f"近 7 天候选房源：{city} / {office} / 预算 {budget}", ""]
    if acquisition and acquisition.source_candidates:
        lines.extend(["Provider acquisition:", ""])
        for candidate in acquisition.source_candidates[:8]:
            status = "P0可解析" if candidate.can_promote else candidate.reject_reason or "candidate_only"
            lines.append(
                f"- {candidate.source_id}: {candidate.title} | {candidate.source_url or 'unknown'} | "
                f"{_candidate_summary(candidate)} | {candidate.provider or 'unknown'} | {status}"
            )
        lines.append("")
    if not clusters:
        lines.append("未找到可进入 MVP 短名单的 P0 候选。")
    for idx, cluster in enumerate(clusters, start=1):
        item = cluster.canonical_listing
        price = f"{item.price_monthly} 元/月" if item.price_monthly is not None else "unknown"
        lines.extend(
            [
                f"{idx}. [{cluster.trust_level}] {item.title}，{price}",
                f"   匹配：{'；'.join(cluster.match_reasons)}",
                f"   联系：{contact_display_text(item.contact_methods)}",
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
    *,
    live: bool = False,
    source_fetches: list[SourceFetchResult] | None = None,
    acquisition: AcquisitionResult | None = None,
) -> str:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    data = redact_profile(profile.to_dict())
    lines = [
        "# last7days-rent 候选短名单",
        "",
        "last7days = 帮助用户 7 天完成租房",
        "",
        f"- 搜索模式: {'live P0 source search' if live else 'fixture test mode'}",
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
        lines.append(
            f"- {source_id}: {meta['status']} / {meta['allowed_output_type']} / contact={', '.join(meta['contact_capability'])}"
        )
    if acquisition:
        lines.extend(["", "## Provider Diagnostics", ""])
        if acquisition.provider_diagnostics:
            for diag in acquisition.provider_diagnostics:
                lines.append(
                    f"- {diag.capability}: requested={diag.requested_provider}, provider={diag.provider}, "
                    f"active={diag.active_provider or 'none'}, status={diag.status}, message={diag.message or 'none'}"
                )
        else:
            lines.append("- none")
        lines.extend(["", "## Acquisition Candidates", ""])
        if acquisition.source_candidates:
            lines.append("| 来源 | URL | 搜索摘要里能看到的信息 | provider | 状态 |")
            lines.append("| --- | --- | --- | --- | --- |")
            for candidate in acquisition.source_candidates[:30]:
                status = "P0可解析" if candidate.can_promote else candidate.reject_reason or "candidate_only"
                lines.append(
                    f"| {candidate.source_id} | {candidate.source_url or 'unknown'} | "
                    f"{_escape_table(_candidate_summary(candidate))} | {candidate.provider or 'unknown'} | {status} |"
                )
        else:
            lines.append("- none")
        if acquisition.extracted_documents:
            lines.extend(["", "## Extracted Documents", ""])
            for doc in acquisition.extracted_documents:
                lines.append(
                    f"- {doc.provider}: status={doc.status}, url={doc.final_url or doc.requested_url}, "
                    f"title={doc.title or 'unknown'}, error={doc.error or 'none'}"
                )
    if source_fetches:
        lines.extend(["", "## Live Fetch Results", ""])
        for fetch in source_fetches:
            lines.append(
                f"- {fetch.source_id}: status={fetch.status}, HTTP={fetch.http_status or 'unknown'}, "
                f"candidates={fetch.candidate_count}, url={fetch.url}, warning={fetch.warning or 'none'}"
            )
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
                f"- 抓取时间: {item.collected_at}",
                f"- 联系路径: {contact_display_text(item.contact_methods)}",
                f"- 匹配理由: {'；'.join(cluster.match_reasons)}",
                f"- 风险标签: {', '.join(cluster.risk_flags) if cluster.risk_flags else 'none'}",
                f"- 合并原因: {', '.join(cluster.merge_reasons) if cluster.merge_reasons else '单源结构化'}",
                f"- 字段 provenance: `{json.dumps(cluster.field_provenance, ensure_ascii=False, sort_keys=True)}`",
                "- 下一步核验问题:",
            ]
        )
        lines.extend(f"  - {question}" for question in cluster.next_questions)
        lines.append("")
    total_clusters = len(safe_clusters)
    contact_ready = sum(1 for cluster in safe_clusters if cluster.canonical_listing.contact_methods)
    lines.extend(
        [
            "## Contact Coverage",
            "",
            f"- 核心短名单数量: {total_clusters}",
            f"- 有可行动联系方式或平台入口: {contact_ready}",
            f"- 覆盖率: {contact_ready}/{total_clusters}" if total_clusters else "- 覆盖率: 0/0",
            "",
        ]
    )
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
            "公开报告保留公开页面或用户授权导入里的联系方式和平台联系入口，便于行动；cookie、token、secret、session、authorization 等凭证不会进入报告或 cache。缺失字段保持 unknown/None，不由 LLM 或代码补全。L1 不是已验真，L3 只来自用户联系确认或明确反馈。",
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
    *,
    live: bool = False,
    source_fetches: list[SourceFetchResult] | None = None,
    acquisition: AcquisitionResult | None = None,
) -> dict:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    package = {
        "schema_version": "0.1.0",
        "slogan": "last7days = 帮助用户 7 天完成租房",
        "mode": "live" if live else "fixture",
        "profile_redacted_summary": redact_profile(profile.to_dict()),
        "source_coverage": source_registry(),
        "source_fetches": [fetch.to_dict() for fetch in (source_fetches or [])],
        "provider_diagnostics": [diag.to_dict() for diag in (acquisition.provider_diagnostics if acquisition else [])],
        "search_queries": [query.to_dict() for query in (acquisition.search_queries if acquisition else [])],
        "source_candidates": [candidate.to_dict() for candidate in (acquisition.source_candidates if acquisition else [])],
        "extracted_documents": [doc.to_dict() for doc in (acquisition.extracted_documents if acquisition else [])],
        "structured_listings": [listing.to_dict() for listing in (acquisition.structured_listings if acquisition else [])],
        "clusters": [cluster.to_dict() for cluster in safe_clusters],
        "verification_evidence": [to_plain(evidence) for evidence in evidences],
        "seven_day_plan": build_seven_day_plan(),
        "warnings": warnings,
        "privacy": {
            "redacted_profile": True,
            "contact_methods_preserved_for_action": True,
            "secret_guard_enabled": True,
            "unknown_fields_are_not_filled": True,
        },
    }
    assert_public_safe(json.dumps(package, ensure_ascii=False, sort_keys=True))
    return package


def _candidate_summary(candidate) -> str:
    parts = [value for value in candidate.visible_fields.values() if value]
    if parts:
        return "，".join(parts)
    return (candidate.snippet or "").replace("\n", " ")[:160] or "unknown"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


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
