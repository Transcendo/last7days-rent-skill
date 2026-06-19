from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .privacy import assert_public_safe
from .seven_day_plan import build_seven_day_plan
from .store import write_text


NESTHUB_GUIDE_URL = "https://nest-hub.eggcampus.com/"


def render_listing_pool_html(pool: dict[str, Any]) -> str:
    meta = pool.get("pool_meta", {})
    profile = pool.get("profile_summary", {})
    listings = pool.get("listings", [])
    rejected_items = pool.get("rejected_items", [])
    source_coverage = pool.get("source_coverage") or {}
    execution = pool.get("execution_summary", {})
    audit_warnings = list(meta.get("audit_warnings") or execution.get("audit_warnings") or [])
    title = _report_title(profile)
    new_count = sum(1 for item in listings if item.get("status", "new") == "new")
    existing_count = max(0, len(listings) - new_count)
    blocked_sources = source_coverage.get("blocked_source_count") if isinstance(source_coverage, dict) else 0
    planned_sources = source_coverage.get("planned_source_count") if isinstance(source_coverage, dict) else None
    effective_sources = source_coverage.get("effective_source_count") if isinstance(source_coverage, dict) else None
    main_items = [item for item in listings if item.get("recommendation_band") == "main" or _trust_order(item.get("trust_level")) >= 1]
    lead_items = [item for item in listings if item not in main_items]
    payload = json.dumps(listings, ensure_ascii=False)
    main_rows = "\n".join(_render_listing_card(item, section="main") for item in main_items) or '<div class="empty">暂无 L1+ 主推荐；请查看线索池和待打开 URL 队列。</div>'
    lead_rows = "\n".join(_render_listing_card(item, section="lead") for item in lead_items) or '<div class="empty">暂无 L0 线索</div>'
    rejected_rows = "\n".join(_render_rejected_item(item) for item in rejected_items) or '<div class="empty">暂无拒收或阻断记录</div>'
    coverage_rows = _render_source_coverage(source_coverage)
    strategy_html = _render_strategy_panel(listings)
    risk_html = _render_risk_panel(pool, rejected_items, source_coverage)
    audit_html = _render_audit_warnings(audit_warnings)
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --text: #1f2328;
      --muted: #626a76;
      --line: #d7dee8;
      --panel: #ffffff;
      --soft: #eef4fb;
      --accent: #0b63ce;
      --accent-dark: #084da3;
      --success: #0f7a4f;
      --warn: #b45309;
      --risk: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 24px 28px 18px; border-bottom: 1px solid var(--line); background: var(--panel); }}
    h1 {{ margin: 0 0 10px; font-size: 24px; line-height: 1.25; letter-spacing: 0; }}
    h2 {{ margin: 0 0 10px; font-size: 19px; line-height: 1.3; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 17px; line-height: 1.35; letter-spacing: 0; }}
    p {{ margin: 0 0 10px; line-height: 1.55; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .meta, .summary {{ display: flex; flex-wrap: wrap; gap: 8px 14px; color: var(--muted); font-size: 14px; }}
    .meta span, .summary span {{ border: 1px solid var(--line); border-radius: 6px; padding: 6px 9px; background: var(--panel); }}
    .guide-strip {{ margin-top: 16px; display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: center; padding: 14px; border: 1px solid #a7c7f2; border-radius: 8px; background: #eef6ff; }}
    .guide-strip strong {{ display: block; margin-bottom: 4px; }}
    .guide-strip p {{ color: #36506f; font-size: 14px; }}
    .guide-cta, .source-button {{ display: inline-flex; min-height: 34px; align-items: center; justify-content: center; border-radius: 6px; padding: 7px 12px; background: var(--accent); color: #fff; font-weight: 650; text-decoration: none; white-space: nowrap; }}
    .guide-cta:hover, .source-button:hover {{ background: var(--accent-dark); color: #fff; text-decoration: none; }}
    .audit {{ margin: 14px 0 0; padding: 10px 12px; border: 1px solid #f3c27b; border-radius: 8px; background: #fff7ed; color: #7c3f00; font-size: 14px; }}
    .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 14px 28px 0; background: var(--bg); }}
    .tab {{ min-height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 7px 13px; background: #fff; color: var(--text); cursor: pointer; font-size: 14px; }}
    .tab.active {{ border-color: var(--accent); background: var(--accent); color: #fff; }}
    .toolbar {{ display: grid; grid-template-columns: minmax(180px, 1fr) repeat(4, minmax(120px, 160px)); gap: 10px; padding: 14px 28px; background: var(--bg); }}
    input, select {{ width: 100%; min-height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; background: #fff; color: var(--text); font-size: 14px; }}
    main {{ padding: 8px 28px 32px; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .section {{ margin: 0 0 22px; }}
    .section-head {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; margin: 0 0 10px; align-items: baseline; }}
    .hint {{ color: var(--muted); font-size: 14px; }}
    .listing {{ display: grid; grid-template-columns: 1fr auto; gap: 14px; padding: 16px; margin-bottom: 12px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .listing h3 {{ margin-bottom: 8px; }}
    .lead-only {{ border-style: dashed; }}
    .facts, .sources {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }}
    .chip {{ display: inline-flex; align-items: center; min-height: 26px; padding: 3px 8px; border-radius: 999px; background: #eef2f7; color: #2f3742; font-size: 13px; }}
    .trust-L2, .trust-L3 {{ background: #dcfce7; color: #166534; }}
    .trust-L1 {{ background: #e0f2fe; color: #075985; }}
    .trust-L0 {{ background: #fef3c7; color: #92400e; }}
    .risk {{ background: #fee2e2; color: var(--risk); }}
    .status {{ font-weight: 650; }}
    .status-effective {{ color: var(--success); }}
    .status-blocked, .status-policy_disabled {{ color: var(--risk); }}
    .status-not_attempted, .status-roadmap_not_enabled, .status-user_authorized_only {{ color: var(--warn); }}
    .evidence, .small-note {{ color: var(--muted); font-size: 14px; margin-top: 6px; }}
    .side {{ min-width: 170px; text-align: right; }}
    .price {{ font-size: 22px; font-weight: 700; margin-bottom: 8px; }}
    .table {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    .coverage-row, .rejected-row {{ display: grid; gap: 10px; padding: 10px 12px; border-top: 1px solid var(--line); font-size: 14px; min-width: 0; }}
    .coverage-row {{ grid-template-columns: 1.1fr .7fr .6fr .6fr .6fr .8fr 1.2fr 1.4fr; }}
    .rejected-row {{ grid-template-columns: 1.1fr .8fr .7fr 1.8fr; }}
    .coverage-row:first-child, .rejected-row:first-child {{ border-top: 0; font-weight: 700; background: #f1f5f9; }}
    .strategy-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .strategy-card {{ padding: 15px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .strategy-card ol, .strategy-card ul {{ margin: 8px 0 0; padding-left: 20px; line-height: 1.65; }}
    .timeline {{ display: grid; gap: 10px; }}
    .timeline-item {{ padding: 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
    .timeline-item strong {{ margin-right: 8px; }}
    .risk-list {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .hidden {{ display: none; }}
    .empty {{ padding: 18px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; color: var(--muted); }}
    footer {{ padding: 18px 28px 32px; color: var(--muted); font-size: 13px; }}
    @media (max-width: 860px) {{
      .toolbar {{ grid-template-columns: 1fr 1fr; padding: 12px 14px; }}
      .tabs, main, header, footer {{ padding-left: 14px; padding-right: 14px; }}
      .listing, .guide-strip, .strategy-grid {{ grid-template-columns: 1fr; }}
      .side {{ text-align: left; }}
      .coverage-row, .rejected-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="meta">
      <span>当前 profile：{html.escape(_profile_meta(profile))}</span>
      <span>预算：{html.escape(str(profile.get("budget_target", "待核验")))} - {html.escape(str(profile.get("budget_max", "待核验")))}</span>
      <span>户型：{html.escape(_bedroom_meta(profile))}</span>
      <span>渠道覆盖：{html.escape(_coverage_meta(planned_sources, effective_sources))}</span>
      <span>新增房源：{html.escape(str(new_count))}</span>
      <span>已存在候选：{html.escape(str(existing_count))}</span>
      <span>被阻断来源：{html.escape(str(blocked_sources or 0))}</span>
      <span>更新时间：{html.escape(str(meta.get("updated_at", "待核验")))}</span>
      <span>详情页打开：{html.escape(str(execution.get("detail_pages_opened", "待核验")))}</span>
    </div>
    <div class="guide-strip">
      <div>
        <strong>租房前先看避坑指南</strong>
        <p>签约前先核验费用、合同主体、付款周期、转租授权和线下看房风险。</p>
      </div>
      <a class="guide-cta" href="{NESTHUB_GUIDE_URL}" target="_blank" rel="noreferrer">打开避坑指南</a>
    </div>
    {audit_html}
  </header>
  <nav class="tabs" aria-label="报告分区">
    <button class="tab active" data-tab="listings">房源</button>
    <button class="tab" data-tab="strategy">下一步策略</button>
    <button class="tab" data-tab="coverage">来源覆盖</button>
    <button class="tab" data-tab="risk">风险指南</button>
  </nav>
  <section class="toolbar" data-panel-control="listings">
    <input id="q" placeholder="搜索小区、片区、标题">
    <select id="trust"><option value="">全部可信等级</option><option>L0</option><option>L1</option><option>L2</option><option>L3</option></select>
    <select id="status"><option value="">全部状态</option><option>new</option><option>shortlisted</option><option>contacted</option><option>scheduled</option><option>viewed</option><option>rejected</option><option>stale</option><option>leased</option></select>
    <select id="band"><option value="">全部分区</option><option value="main">主推荐</option><option value="lead_pool">线索池</option></select>
    <select id="risk"><option value="">全部风险</option><option value="snippet_only">snippet_only</option><option value="missing_contact_path">missing_contact_path</option><option value="commercial_utilities">commercial_utilities</option></select>
  </section>
  <main>
    <section class="panel active" id="panel-listings">
      <div class="summary" id="summary"></div>
      <section class="section">
        <div class="section-head"><h2>主推荐</h2><span class="hint">仅展示 L1+，来自打开详情页且字段足够的公开证据。</span></div>
        {main_rows}
      </section>
      <section class="section">
        <div class="section-head"><h2>线索池</h2><span class="hint">L0 只代表待核验线索，不得视为真实房源或已验证候选。</span></div>
        {lead_rows}
      </section>
    </section>
    <section class="panel" id="panel-strategy">
      {strategy_html}
    </section>
    <section class="panel" id="panel-coverage">
      <section class="section">
        <div class="section-head"><h2>来源覆盖</h2><span class="hint">合并计划、尝试、入池、打开详情页、阻断和未执行渠道。</span></div>
        <div class="table">{coverage_rows}</div>
      </section>
      <section class="section">
        <div class="section-head"><h2>拒收 / 阻断</h2><span class="hint">登录墙、验证码、app下载墙、字段不足或隐私风险必须可审计。</span></div>
        <div class="table">{rejected_rows}</div>
      </section>
    </section>
    <section class="panel" id="panel-risk">
      {risk_html}
    </section>
  </main>
  <footer>来源仅为公开页面或用户授权内容。未知字段显示为待核验；不保存 cookie、token、session 或登录态；L0 不代表已验证房源。</footer>
  <script>
    const listings = {payload};
    const cards = [...document.querySelectorAll('.listing')];
    function update() {{
      const q = document.querySelector('#q').value.trim().toLowerCase();
      const trust = document.querySelector('#trust').value;
      const status = document.querySelector('#status').value;
      const band = document.querySelector('#band').value;
      const risk = document.querySelector('#risk').value;
      let visible = 0;
      cards.forEach(card => {{
        const text = card.dataset.text.toLowerCase();
        const ok = (!q || text.includes(q)) && (!trust || card.dataset.trust === trust) && (!status || card.dataset.status === status) && (!band || card.dataset.band === band) && (!risk || card.dataset.risk.includes(risk));
        card.classList.toggle('hidden', !ok);
        if (ok) visible++;
      }});
      document.querySelector('#summary').innerHTML = `<span>当前显示：${{visible}}</span><span>总候选：${{listings.length}}</span><span>主推荐：${{listings.filter(x => x.recommendation_band === 'main').length}}</span><span>L1+：${{listings.filter(x => ['L1','L2','L3'].includes(x.trust_level)).length}}</span>`;
    }}
    document.querySelectorAll('input,select').forEach(el => el.addEventListener('input', update));
    document.querySelectorAll('.tab').forEach(tab => {{
      tab.addEventListener('click', () => {{
        const target = tab.dataset.tab;
        document.querySelectorAll('.tab').forEach(item => item.classList.toggle('active', item === tab));
        document.querySelectorAll('.panel').forEach(panel => panel.classList.toggle('active', panel.id === `panel-${{target}}`));
        document.querySelectorAll('[data-panel-control]').forEach(control => control.classList.toggle('hidden', control.dataset.panelControl !== target));
      }});
    }});
    update();
  </script>
</body>
</html>
"""
    html_text = "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"
    assert_public_safe(html_text)
    return html_text


def write_html_report(reports_dir: Path, basename: str, pool: dict[str, Any]) -> Path:
    path = reports_dir / f"{basename}.html"
    write_text(path, render_listing_pool_html(pool))
    return path


def _report_title(profile: dict[str, Any]) -> str:
    office = profile.get("office_anchor") or profile.get("company") or "个人租房"
    bedrooms = profile.get("preferred_bedrooms")
    bedroom = str(profile.get("bedroom_label") or (f"{bedrooms}居室" if bedrooms else "租房"))
    budget = profile.get("budget_max") or "待核验"
    return f"{office} {budget} 内{bedroom}候选池"


def _profile_meta(profile: dict[str, Any]) -> str:
    parts = [
        profile.get("city"),
        profile.get("company"),
        profile.get("office_anchor"),
        f"{profile.get('commute_minutes')}分钟内" if profile.get("commute_minutes") else None,
    ]
    return " / ".join(str(part) for part in parts if part) or "待核验"


def _coverage_meta(planned_sources: Any, effective_sources: Any) -> str:
    planned = planned_sources if planned_sources not in (None, "") else "待核验"
    effective = effective_sources if effective_sources not in (None, "") else "待核验"
    return f"计划 {planned} / 入池 {effective}"


def _bedroom_meta(profile: dict[str, Any]) -> str:
    if profile.get("bedroom_label"):
        return str(profile["bedroom_label"])
    bedrooms = profile.get("preferred_bedrooms")
    return f"{bedrooms}居" if bedrooms else "待核验"


def _render_listing_card(item: dict[str, Any], *, section: str) -> str:
    text = " ".join(str(item.get(key, "")) for key in ["title", "community", "district_hint", "price_text", "layout_text"])
    risks = list(item.get("risk_flags", []))
    trust = str(item.get("trust_level", "L0"))
    band = str(item.get("recommendation_band") or ("main" if _trust_order(trust) >= 1 else "lead_pool"))
    chips = [
        f'<span class="chip trust-{html.escape(trust)}">{html.escape(trust)}</span>',
        f'<span class="chip">{html.escape(str(item.get("status", "new")))}</span>',
        f'<span class="chip">{html.escape(str(item.get("district_hint", "待核验")))}</span>',
        f'<span class="chip">{html.escape("主推荐" if band == "main" else "线索池")}</span>',
    ]
    chips.extend(f'<span class="chip risk">{html.escape(str(risk))}</span>' for risk in risks)
    evidence_count = item.get("evidence_count") or len(item.get("observations", []))
    opened_at = item.get("last_opened_at") or "待打开详情页"
    css = "listing" if section == "main" else "listing lead-only"
    return f"""
    <article class="{css}" data-text="{html.escape(text)}" data-trust="{html.escape(trust)}" data-status="{html.escape(str(item.get("status", "new")))}" data-band="{html.escape(band)}" data-risk="{html.escape(" ".join(risks))}">
      <div>
        <h3>{html.escape(str(item.get("title", "待核验")))}</h3>
        <div class="facts">{''.join(chips)}</div>
        <div class="facts">
          <span class="chip">{html.escape(str(item.get("community", "待核验")))}</span>
          <span class="chip">{html.escape(str(item.get("area_text", "待核验")))}</span>
          <span class="chip">{html.escape(str(item.get("layout_text", "待核验")))}</span>
        </div>
        <div class="evidence">证据：{html.escape(str(evidence_count))} 条；最后打开：{html.escape(str(opened_at))}；match/risk：{html.escape(str(item.get("match_score", "待核验")))}/{html.escape(str(item.get("risk_score", "待核验")))}</div>
        <div class="sources">{_render_source_buttons(item)}</div>
      </div>
      <aside class="side">
        <div class="price">{html.escape(str(item.get("price_text", "待核验")))}</div>
        <div class="small-note">首次发现：{html.escape(str(item.get("first_seen_at", "待核验")))}</div>
      </aside>
    </article>
    """


def _render_source_buttons(item: dict[str, Any]) -> str:
    urls = list(item.get("source_urls") or [])
    names = list(item.get("source_names") or [])
    if not urls:
        return '<span class="small-note">来源待核验</span>'
    buttons: list[str] = []
    for index, url in enumerate(urls[:2]):
        label = _source_button_label(names[index] if index < len(names) else None, url)
        buttons.append(f'<a class="source-button" href="{html.escape(str(url))}" target="_blank" rel="noreferrer">打开{html.escape(label)}来源</a>')
    if len(urls) > 2:
        buttons.append(f'<span class="chip">更多来源 {len(urls) - 2}</span>')
    return "".join(buttons)


def _source_button_label(name: Any, url: Any) -> str:
    raw = str(name or "").strip()
    if raw and raw not in {"unknown", "None"}:
        return raw
    domain = urlparse(str(url)).netloc.replace("www.", "")
    return domain or "公开"


def _render_rejected_item(item: dict[str, Any]) -> str:
    reasons = item.get("reject_reasons")
    reason_text = "；".join(str(reason) for reason in reasons) if isinstance(reasons, list) else str(reasons or "待核验")
    source = item.get("source_url")
    source_link = f'<a class="source-button" href="{html.escape(source)}" target="_blank" rel="noreferrer">打开阻断来源</a>' if source else "无 URL"
    return f"""
    <div class="rejected-row">
      <span>{html.escape(str(item.get("title") or item.get("evidence_id") or "未命名"))}</span>
      <span>{html.escape(str(item.get("source_name") or "unknown"))}</span>
      <span>{source_link}</span>
      <span>{html.escape(reason_text)}</span>
    </div>
    """


def _render_source_coverage(source_coverage: dict[str, Any]) -> str:
    sources = source_coverage.get("sources") if isinstance(source_coverage, dict) else {}
    if not sources:
        return '<div class="empty">暂无来源覆盖统计</div>'
    rows = [
        '<div class="coverage-row"><span>来源</span><span>状态</span><span>计划</span><span>尝试</span><span>入池</span><span>详情页</span><span>原因</span><span>域名/说明</span></div>'
    ]
    for source, info in sorted(sources.items(), key=lambda row: str(row[1].get("source_name") if isinstance(row[1], dict) else row[0])):
        domains = ", ".join(info.get("domains", [])) if isinstance(info, dict) else ""
        note = info.get("policy_note") if isinstance(info, dict) else None
        source_name = info.get("source_name") or source
        attempted = _attempted_text(info)
        blocked = _blocked_text(info)
        status = str(info.get("status") or "planned")
        rows.append(
            f'<div class="coverage-row"><span>{html.escape(str(source_name))}</span><span class="status status-{html.escape(status)}">{html.escape(_status_label(status))}</span><span>{html.escape(str(info.get("planned_queries", 0)))}</span><span>{html.escape(attempted)}</span><span>{html.escape(str(info.get("accepted_items", 0)))}</span><span>{html.escape(str(info.get("detail_pages_opened", 0)))}</span><span>{html.escape(blocked)}</span><span>{html.escape(str(note or domains or "待核验"))}</span></div>'
        )
    return "\n".join(rows)


def _render_strategy_panel(listings: list[dict[str, Any]]) -> str:
    today = _today_actions(listings)
    by_listing = _listing_actions(listings)
    plan_rows = "\n".join(
        f'<div class="timeline-item"><strong>{html.escape(item["day"])}</strong>{html.escape(item["action"])}</div>'
        for item in build_seven_day_plan()
    )
    listing_rows = "\n".join(by_listing) or '<li>当前没有可行动房源，先补充公开 evidence 或用户授权截图。</li>'
    today_rows = "\n".join(f"<li>{html.escape(action)}</li>" for action in today)
    return f"""
      <section class="section">
        <div class="section-head"><h2>下一步策略</h2><span class="hint">这里是 skill 给出的行动建议，不混在房源卡片里。</span></div>
        <div class="strategy-grid">
          <div class="strategy-card">
            <h3>今天先做</h3>
            <ol>{today_rows}</ol>
          </div>
          <div class="strategy-card">
            <h3>按房源行动</h3>
            <ol>{listing_rows}</ol>
          </div>
          <div class="strategy-card">
            <h3>7 天计划</h3>
            <div class="timeline">{plan_rows}</div>
          </div>
        </div>
      </section>
    """


def _today_actions(listings: list[dict[str, Any]]) -> list[str]:
    main_count = sum(1 for item in listings if item.get("recommendation_band") == "main")
    lead_count = max(0, len(listings) - main_count)
    return [
        f"先联系 L1+ 主推荐前 {min(max(main_count, 1), 5)} 套，确认是否仍在租、费用条款和可看房时间。",
        f"把 {lead_count} 条 L0 线索只当待核验 URL，优先打开详情页补价格、面积、联系方式和发布时间。",
        "对超预算、app-wall、验证码、安全页阻断来源做好标记，不把它们当作有效候选。",
    ]


def _listing_actions(listings: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(listings, key=lambda item: (-_trust_order(item.get("trust_level")), item.get("price_monthly") or 10**9))[:6]
    rows: list[str] = []
    for item in ordered:
        title = str(item.get("title") or item.get("community") or "未命名房源")
        trust = str(item.get("trust_level") or "L0")
        actions = "；".join(str(action) for action in item.get("next_actions", []) if action) or "打开来源并补齐关键字段"
        rows.append(f"<li><strong>{html.escape(title)}</strong> <span class=\"chip\">{html.escape(trust)}</span><br>{html.escape(actions)}</li>")
    return rows


def _render_risk_panel(pool: dict[str, Any], rejected_items: list[dict[str, Any]], source_coverage: dict[str, Any]) -> str:
    risk_checks = list(pool.get("risk_checks") or [])
    guide_sources = list(pool.get("guide_sources") or [])
    risk_tags = "".join(f'<span class="chip risk">{html.escape(str(item))}</span>' for item in risk_checks) or '<span class="chip">暂无 anchor 风险项</span>'
    guide_rows = "".join(
        f'<li>{html.escape(str(item.get("source_name") or "公开指南"))}：<a href="{html.escape(str(item.get("source_url")))}" target="_blank" rel="noreferrer">打开</a></li>'
        for item in guide_sources
        if isinstance(item, dict) and item.get("source_url")
    )
    blocked_rows = _blocked_source_explanations(source_coverage, rejected_items)
    return f"""
      <section class="section">
        <div class="guide-strip">
          <div>
            <strong>避坑指南</strong>
            <p>先看通用租房风险，再结合本页候选逐套核验。</p>
          </div>
          <a class="guide-cta" href="{NESTHUB_GUIDE_URL}" target="_blank" rel="noreferrer">打开避坑指南</a>
        </div>
      </section>
      <section class="section">
        <div class="section-head"><h2>Anchor 风险检查</h2><span class="hint">这些是本办公点/通勤圈需要优先核验的风险项。</span></div>
        <div class="risk-list">{risk_tags}</div>
      </section>
      <section class="section">
        <div class="section-head"><h2>阻断来源解释</h2><span class="hint">阻断不等于没有房源，只说明本轮没有获得可验证公开字段。</span></div>
        <div class="strategy-card"><ul>{blocked_rows}</ul></div>
      </section>
      <section class="section">
        <div class="section-head"><h2>参考材料</h2><span class="hint">只作为避坑/背景，不当作实时房源。</span></div>
        <div class="strategy-card"><ul>{guide_rows or "<li>暂无额外参考材料。</li>"}</ul></div>
      </section>
    """


def _blocked_source_explanations(source_coverage: dict[str, Any], rejected_items: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    sources = source_coverage.get("sources") if isinstance(source_coverage, dict) else {}
    if isinstance(sources, dict):
        for info in sources.values():
            if not isinstance(info, dict):
                continue
            if info.get("status") not in {"blocked", "policy_disabled", "roadmap_not_enabled", "user_authorized_only"}:
                continue
            name = info.get("source_name") or info.get("source_id") or "来源"
            reason = _blocked_text(info)
            note = info.get("policy_note")
            rows.append(f"<li><strong>{html.escape(str(name))}</strong>：{html.escape(str(note or reason))}</li>")
    for item in rejected_items[:5]:
        reasons = item.get("reject_reasons")
        reason = "；".join(str(value) for value in reasons) if isinstance(reasons, list) else str(reasons or "blocked")
        rows.append(f"<li><strong>{html.escape(str(item.get('source_name') or item.get('title') or '阻断页'))}</strong>：{html.escape(reason)}</li>")
    return "\n".join(rows) or "<li>暂无阻断来源。</li>"


def _render_audit_warnings(audit_warnings: list[Any]) -> str:
    if not audit_warnings:
        return ""
    labels = {
        "evidence_missing_brief_context_attached_latest": "evidence 未带 brief，本次已自动挂载本地最新 search brief。",
        "evidence_missing_brief_context_no_latest_brief": "evidence 未带 brief，且本地没有找到最新 search brief。",
        "missing_source_attempts_partial_audit": "缺少 source_attempts，来源执行状态为部分审计。",
        "missing_attempted_queries_partial_audit": "缺少 attempted_queries，query 级执行状态为部分审计。",
        "missing_execution_summary_partial_audit": "缺少 execution_summary，执行统计不完整。",
        "missing_execution_summary_detail_pages_opened": "缺少 detail_pages_opened，详情页打开数不完整。",
    }
    text = "；".join(labels.get(str(item), str(item)) for item in audit_warnings)
    return f'<div class="audit">计划未完整审计：{html.escape(text)}</div>'


def _attempted_text(info: dict[str, Any]) -> str:
    attempted = info.get("attempted_queries")
    if attempted is None:
        return "未记录"
    suffix = "估算" if info.get("attempt_status") == "inferred_from_items" else ""
    return f"{attempted}{suffix}"


def _blocked_text(info: dict[str, Any]) -> str:
    count = int(info.get("rejected_or_blocked") or 0)
    reasons = list(info.get("blocked_reasons") or []) + list(info.get("zero_yield_reasons") or [])
    reason_text = "；".join(str(reason) for reason in reasons[:3] if reason)
    if count and reason_text:
        return f"{count}：{reason_text}"
    if count:
        return str(count)
    return reason_text or "无"


def _status_label(status: str) -> str:
    return {
        "planned": "已计划",
        "attempted": "已尝试",
        "effective": "有效入池",
        "blocked": "被阻断",
        "zero_yield": "零结果",
        "not_attempted": "未执行",
        "policy_disabled": "策略禁用",
        "roadmap_not_enabled": "暂未启用",
        "user_authorized_only": "需用户授权",
    }.get(status, status)


def _trust_order(trust: str | None) -> int:
    return {"L3": 3, "L2": 2, "L1": 1, "L0": 0}.get(trust or "L0", 0)
