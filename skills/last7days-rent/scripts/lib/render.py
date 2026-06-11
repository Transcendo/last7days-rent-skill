from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ModuleNotFoundError:
    Environment = None  # type: ignore[assignment]
    FileSystemLoader = None  # type: ignore[assignment]
    select_autoescape = None  # type: ignore[assignment]

from .contact import contact_display_text
from .privacy import assert_public_safe, redact_profile, sanitize_cluster
from .schema import ListingCluster, RentProfile, SearchLead, SearchProviderResult, SourceFetchResult, VerificationEvidence, now_iso, to_plain
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
    search_provider_results: list[SearchProviderResult] | None = None,
    search_leads: list[SearchLead] | None = None,
    promoted_leads: list[SearchLead] | None = None,
    rejected_leads: list[SearchLead] | None = None,
) -> str:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    data = redact_profile(profile.to_dict())
    lines = [
        "# last7days-rent 候选短名单",
        "",
        "last7days = 帮助用户 7 天完成租房",
        "",
        f"- 搜索模式: {'live web search provider discovery' if live else 'fixture provider test mode'}",
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
    if source_fetches:
        lines.extend(["", "## Live Fetch Results", ""])
        for fetch in source_fetches:
            lines.append(
                f"- {fetch.source_id}: status={fetch.status}, HTTP={fetch.http_status or 'unknown'}, "
                f"candidates={fetch.candidate_count}, url={fetch.url}, warning={fetch.warning or 'none'}"
            )
    if search_provider_results:
        lines.extend(["", "## Search Provider Coverage", ""])
        for result in search_provider_results:
            lines.append(
                f"- {result.provider}: status={result.status}, HTTP={result.http_status or 'unknown'}, "
                f"leads={result.lead_count}, warning={result.warning or 'none'}"
            )
    if search_leads:
        promoted_ids = {lead.lead_id for lead in promoted_leads or []}
        rejected_reasons = {lead.lead_id: lead.rejection_reason for lead in rejected_leads or []}
        lines.extend(["", "## 搜索发现线索", ""])
        lines.append("SearchLead 只是搜索发现层，不能直接证明价格、发布时间、联系方式或仍在租。")
        lines.append("")
        for lead in sorted(search_leads, key=lambda item: (item.provider, item.rank))[:20]:
            status = "promoted" if lead.lead_id in promoted_ids else f"rejected:{rejected_reasons.get(lead.lead_id) or 'not_promoted'}"
            snippet = (lead.snippet or lead.text_excerpt or "").replace("\n", " ")[:180]
            lines.append(
                f"- [{lead.provider} #{lead.rank}] {lead.title} | {lead.domain} | {status} | {lead.url}"
                + (f" | {snippet}" if snippet else "")
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
    search_provider_results: list[SearchProviderResult] | None = None,
    search_leads: list[SearchLead] | None = None,
    promoted_leads: list[SearchLead] | None = None,
    rejected_leads: list[SearchLead] | None = None,
) -> dict:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    package = {
        "schema_version": "0.1.0",
        "slogan": "last7days = 帮助用户 7 天完成租房",
        "mode": "live" if live else "fixture",
        "profile_redacted_summary": redact_profile(profile.to_dict()),
        "source_coverage": source_registry(),
        "source_fetches": [fetch.to_dict() for fetch in (source_fetches or [])],
        "search_provider_coverage": [result.to_dict() for result in (search_provider_results or [])],
        "search_leads": [lead.to_dict() for lead in (search_leads or [])],
        "promoted_leads": [lead.to_dict() for lead in (promoted_leads or [])],
        "rejected_leads": [lead.to_dict() for lead in (rejected_leads or [])],
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


def render_html_report(
    profile: RentProfile,
    clusters: list[ListingCluster],
    evidences: list[VerificationEvidence],
    warnings: list[str],
    *,
    live: bool = False,
    source_fetches: list[SourceFetchResult] | None = None,
    search_provider_results: list[SearchProviderResult] | None = None,
    search_leads: list[SearchLead] | None = None,
    promoted_leads: list[SearchLead] | None = None,
    rejected_leads: list[SearchLead] | None = None,
) -> str:
    context = _html_context(
        profile,
        clusters,
        evidences,
        warnings,
        live=live,
        source_fetches=source_fetches,
        search_provider_results=search_provider_results,
        search_leads=search_leads,
        promoted_leads=promoted_leads,
        rejected_leads=rejected_leads,
    )
    if Environment is None:
        output = _render_html_fallback(context)
    else:
        template = _jinja_env().get_template("report.html.j2")
        output = template.render(**context).rstrip() + "\n"
    assert_public_safe(output)
    return output


def write_outputs(
    reports_dir: Path,
    basename: str,
    html: str,
    evidence: dict,
) -> tuple[Path, Path]:
    html_path = reports_dir / f"{basename}.html"
    evidence_path = reports_dir / f"{basename}.json"
    write_text(html_path, html)
    write_json(evidence_path, evidence)
    return html_path, evidence_path


def _jinja_env() -> Any:
    if Environment is None or FileSystemLoader is None or select_autoescape is None:
        raise RuntimeError("jinja2 is not available")
    template_dir = Path(__file__).resolve().parents[2] / "templates"
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _html_context(
    profile: RentProfile,
    clusters: list[ListingCluster],
    evidences: list[VerificationEvidence],
    warnings: list[str],
    *,
    live: bool,
    source_fetches: list[SourceFetchResult] | None,
    search_provider_results: list[SearchProviderResult] | None,
    search_leads: list[SearchLead] | None,
    promoted_leads: list[SearchLead] | None,
    rejected_leads: list[SearchLead] | None,
) -> dict:
    safe_clusters = [sanitize_cluster(cluster) for cluster in clusters]
    redacted_profile = redact_profile(profile.to_dict())
    rendered_clusters = [_render_cluster(cluster) for cluster in safe_clusters]
    fetches = [fetch.to_dict() for fetch in (source_fetches or [])]
    provider_results = [result.to_dict() for result in (search_provider_results or [])]
    leads = [lead.to_dict() for lead in (search_leads or [])]
    promoted_ids = {lead.lead_id for lead in promoted_leads or []}
    rejected_reasons = {lead.lead_id: lead.rejection_reason for lead in rejected_leads or []}
    total_clusters = len(rendered_clusters)
    contact_ready = sum(1 for cluster in rendered_clusters if cluster["canonical_listing"]["has_contact"])
    source_count = len(fetches) if fetches else len(source_registry())
    blocked_count = (
        sum(1 for fetch in fetches if _blocked_payload(fetch))
        + sum(1 for result in provider_results if _blocked_payload(result))
        + sum(1 for warning in warnings if _blocked_warning(warning))
    )
    enriched_leads = [_render_search_lead(lead, promoted_ids, rejected_reasons) for lead in leads[:20]]
    context = {
        "title": "last7days-rent 候选短名单",
        "summary": {
            "mode_label": "live web search provider discovery" if live else "fixture provider test mode",
            "city": redacted_profile["office_anchor"].get("city") or "unknown",
            "office": redacted_profile["office_anchor"].get("office_name")
            or redacted_profile["office_anchor"].get("address_hint")
            or "unknown",
            "budget_label": _budget_label(redacted_profile),
            "commute_label": _commute_label(redacted_profile),
            "generated_at": now_iso(),
            "total_clusters": total_clusters,
            "contact_ready": contact_ready,
            "source_count": source_count,
            "warning_count": len(warnings),
            "blocked_count": blocked_count,
        },
        "action_items": rendered_clusters[:5],
        "clusters": rendered_clusters,
        "source_coverage": source_registry(),
        "source_fetches": fetches,
        "search_provider_results": provider_results,
        "search_leads": enriched_leads,
        "warnings": warnings,
        "verification_evidence": [to_plain(evidence) for evidence in evidences],
        "seven_day_plan": build_seven_day_plan(),
        "profile": redacted_profile,
    }
    assert_public_safe(json.dumps(context, ensure_ascii=False, sort_keys=True))
    return context


def _render_cluster(cluster: ListingCluster) -> dict:
    data = cluster.to_dict()
    item = data["canonical_listing"]
    item["price_label"] = f"{item['price_monthly']} 元/月" if item.get("price_monthly") is not None else "unknown"
    item["location_label"] = _join_known([item.get("district"), item.get("community_name"), item.get("address_hint")])
    item["layout_area_label"] = _join_known([item.get("layout"), _area_label(item.get("area_sqm"))])
    item["contact_text"] = contact_display_text(cluster.canonical_listing.contact_methods)
    item["has_contact"] = bool(cluster.canonical_listing.contact_methods)
    data["match_label"] = "；".join(cluster.match_reasons) if cluster.match_reasons else "none"
    data["risk_label"] = ", ".join(cluster.risk_flags) if cluster.risk_flags else "none"
    data["merge_label"] = ", ".join(cluster.merge_reasons) if cluster.merge_reasons else "单源结构化"
    data["primary_question"] = cluster.next_questions[0] if cluster.next_questions else "联系前核验是否仍在租"
    data["field_provenance_json"] = json.dumps(cluster.field_provenance, ensure_ascii=False, indent=2, sort_keys=True)
    data["final_score"] = f"{cluster.final_score:.1f}"
    return data


def _render_search_lead(lead: dict, promoted_ids: set[str], rejected_reasons: dict[str, str | None]) -> dict:
    lead_id = lead.get("lead_id")
    status = "promoted" if lead_id in promoted_ids else f"rejected:{rejected_reasons.get(lead_id) or 'not_promoted'}"
    lead["status_label"] = status
    lead["snippet_label"] = _join_known([lead.get("snippet"), lead.get("text_excerpt")])
    return lead


def _budget_label(profile_data: dict) -> str:
    constraints = profile_data.get("housing_constraints") or {}
    budget_min = constraints.get("budget_min") or "unknown"
    budget_max = constraints.get("budget_max") or "unknown"
    return f"{budget_min} - {budget_max}"


def _commute_label(profile_data: dict) -> str:
    value = (profile_data.get("commute") or {}).get("max_minutes")
    return f"{value} 分钟" if value is not None else "unknown"


def _area_label(value: float | int | None) -> str | None:
    if value is None:
        return None
    return f"{value:g}㎡"


def _join_known(parts: list[str | None]) -> str:
    known = [str(part) for part in parts if part not in {None, "", "unknown"}]
    return " / ".join(known) if known else "unknown"


def _blocked_payload(payload: dict) -> bool:
    text = " ".join(str(payload.get(key) or "") for key in ["status", "warning"]).lower()
    return any(token in text for token in ["blocked", "captcha", "403", "429", "login"])


def _blocked_warning(warning: str) -> bool:
    text = warning.lower()
    return any(token in text for token in ["blocked", "captcha", "403", "429", "login"])


def _render_html_fallback(context: dict) -> str:
    summary = context["summary"]
    clusters = context["clusters"]
    source_coverage = context["source_coverage"]
    provider_results = context["search_provider_results"]
    search_leads = context["search_leads"]
    warnings = context["warnings"]
    seven_day_plan = context["seven_day_plan"]

    def row(cells: list[str]) -> str:
        return "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells) + "</tr>"

    html: list[str] = [
        "<!doctype html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(context['title'])}</title>",
        "<style>",
        "body{margin:0;background:#f7f5ef;color:#17211c;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;line-height:1.6}",
        ".shell{width:min(1120px,calc(100% - 32px));margin:0 auto;padding:28px 0 54px}",
        ".hero,.card,.table-wrap,.note{background:#fffdf8;border:1px solid #d8ded2;border-radius:8px;padding:18px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.metric{border:1px solid #d8ded2;border-radius:8px;padding:12px;background:#f8fbf8}",
        "table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid #d8ded2;padding:9px;text-align:left;vertical-align:top}th{color:#66736c}",
        "a{color:#0b4f4a;overflow-wrap:anywhere}.muted{color:#66736c}.warn{background:#fff4df;border-color:#f1c16f}",
        "</style>",
        "</head>",
        "<body><main class=\"shell\">",
        '<section class="hero">',
        f"<p class=\"muted\">last7days = 帮助用户 7 天完成租房</p><h1>{escape(context['title'])}</h1>",
        f"<p>{escape(summary['mode_label'])} · {escape(summary['city'])} / {escape(summary['office'])} · 预算 {escape(summary['budget_label'])}</p>",
        '<div class="grid">',
        f"<div class=\"metric\"><strong>候选短名单</strong><br>{summary['total_clusters']}</div>",
        f"<div class=\"metric\"><strong>Contact Coverage</strong><br>{summary['contact_ready']}/{summary['total_clusters']}</div>",
        f"<div class=\"metric\"><strong>Source Coverage</strong><br>{summary['source_count']}</div>",
        f"<div class=\"metric\"><strong>Warnings</strong><br>{summary['warning_count']}</div>",
        "</div></section>",
        "<h2>候选房源短名单</h2>",
    ]
    if clusters:
        html.append('<div class="grid">')
        for idx, cluster in enumerate(clusters, start=1):
            item = cluster["canonical_listing"]
            html.extend(
                [
                    '<article class="card">',
                    f"<h3>#{idx} {escape(item['title'])}</h3>",
                    f"<p>{escape(cluster['trust_level'])} · {escape(item['price_label'])} · {escape(item['source_id'])}</p>",
                    f"<p><strong>联系路径</strong><br>{escape(item['contact_text'])}</p>",
                    f"<p><strong>匹配理由</strong><br>{escape(cluster['match_label'])}</p>",
                    f"<p><strong>风险</strong><br>{escape(cluster['risk_label'])}</p>",
                    "</article>",
                ]
            )
        html.append("</div>")
    else:
        html.append('<div class="card">未找到可进入 MVP 短名单的 P0 候选。</div>')

    html.extend(["<h2>Source Coverage</h2>", '<div class="table-wrap"><table><thead><tr><th>Source</th><th>Status</th><th>Output</th></tr></thead><tbody>'])
    for source_id, meta in source_coverage.items():
        html.append(row([source_id, meta.get("status", "unknown"), meta.get("allowed_output_type", "unknown")]))
    html.extend(["</tbody></table></div>", "<h2>Search Provider Coverage</h2>"])
    if provider_results:
        html.append('<div class="table-wrap"><table><thead><tr><th>Provider</th><th>Status</th><th>HTTP</th><th>Leads</th><th>Warning</th></tr></thead><tbody>')
        for result in provider_results:
            html.append(row([result.get("provider"), result.get("status"), result.get("http_status") or "unknown", result.get("lead_count"), result.get("warning") or "none"]))
        html.append("</tbody></table></div>")
    else:
        html.append('<div class="card">未运行 search provider discovery。</div>')

    html.extend(["<h2>搜索发现线索</h2>", '<div class="card warn">SearchLead 只是搜索发现层，不能直接证明价格、发布时间、联系方式或仍在租。</div>'])
    if search_leads:
        html.append('<div class="table-wrap"><table><thead><tr><th>Provider</th><th>Rank</th><th>标题</th><th>Domain</th><th>Status</th><th>URL</th></tr></thead><tbody>')
        for lead in search_leads:
            html.append(row([lead.get("provider"), lead.get("rank"), lead.get("title"), lead.get("domain"), lead.get("status_label"), lead.get("url")]))
        html.append("</tbody></table></div>")

    html.extend(["<h2>Warnings</h2>"])
    if warnings:
        html.append("<ul>" + "".join(f"<li>{escape(str(warning))}</li>" for warning in warnings) + "</ul>")
    else:
        html.append('<div class="card">none</div>')

    html.extend(["<h2>Contact Coverage</h2>", f"<p>{summary['contact_ready']}/{summary['total_clusters']}</p>", "<h2>7 天租房行动计划</h2>", "<ol>"])
    for step in seven_day_plan:
        html.append(f"<li><strong>{escape(str(step['day']))}</strong>: {escape(str(step['action']))}</li>")
    html.extend(
        [
            "</ol>",
            '<section class="note">L1 不是已验真，L3 只来自用户联系确认或明确反馈。公开报告只保留可行动联系路径和平台入口，缺失字段保持 unknown/None。</section>',
            "</main></body></html>",
        ]
    )
    return "\n".join(html).rstrip() + "\n"
