from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .privacy import assert_public_safe
from .store import write_text


def render_listing_pool_html(pool: dict[str, Any]) -> str:
    meta = pool.get("pool_meta", {})
    profile = pool.get("profile_summary", {})
    listings = pool.get("listings", [])
    rejected_items = pool.get("rejected_items", [])
    source_coverage = pool.get("source_coverage", {})
    execution = pool.get("execution_summary", {})
    title = _report_title(profile)
    main_items = [item for item in listings if item.get("recommendation_band") == "main" or _trust_order(item.get("trust_level")) >= 1]
    lead_items = [item for item in listings if item not in main_items]
    payload = json.dumps(listings, ensure_ascii=False)
    main_rows = "\n".join(_render_listing_card(item, section="main") for item in main_items) or '<div class="empty">暂无 L1+ 主推荐；请查看线索池和待打开 URL 队列。</div>'
    lead_rows = "\n".join(_render_listing_card(item, section="lead") for item in lead_items) or '<div class="empty">暂无 L0 线索</div>'
    rejected_rows = "\n".join(_render_rejected_item(item) for item in rejected_items) or '<div class="empty">暂无拒收或阻断记录</div>'
    coverage_rows = _render_source_coverage(source_coverage)
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --text: #1f2328;
      --muted: #646b75;
      --line: #d8dee4;
      --panel: #ffffff;
      --accent: #0f766e;
      --warn: #b45309;
      --risk: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 24px 28px 16px; border-bottom: 1px solid var(--line); background: var(--panel); }}
    h1 {{ margin: 0 0 10px; font-size: 24px; line-height: 1.25; letter-spacing: 0; }}
    h2 {{ margin: 0 0 10px; font-size: 19px; line-height: 1.3; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 17px; line-height: 1.35; letter-spacing: 0; }}
    .meta, .summary {{ display: flex; flex-wrap: wrap; gap: 8px 16px; color: var(--muted); font-size: 14px; }}
    .meta span, .summary span {{ border: 1px solid var(--line); border-radius: 6px; padding: 6px 9px; background: var(--panel); }}
    .toolbar {{ display: grid; grid-template-columns: minmax(180px, 1fr) repeat(4, minmax(120px, 160px)); gap: 10px; padding: 14px 28px; border-bottom: 1px solid var(--line); background: var(--panel); position: sticky; top: 0; z-index: 1; }}
    input, select {{ width: 100%; min-height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; background: #fff; color: var(--text); font-size: 14px; }}
    main {{ padding: 18px 28px 32px; }}
    .section {{ margin: 0 0 22px; }}
    .section-head {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; margin: 0 0 10px; align-items: baseline; }}
    .hint {{ color: var(--muted); font-size: 14px; }}
    .listing {{ display: grid; grid-template-columns: 1fr auto; gap: 14px; padding: 16px; margin-bottom: 12px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .listing h3 {{ margin-bottom: 8px; }}
    .lead-only {{ border-style: dashed; }}
    .facts {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }}
    .chip {{ display: inline-flex; align-items: center; min-height: 26px; padding: 3px 8px; border-radius: 999px; background: #eef2f7; color: #2f3742; font-size: 13px; }}
    .trust-L2, .trust-L3 {{ background: #dcfce7; color: #166534; }}
    .trust-L1 {{ background: #e0f2fe; color: #075985; }}
    .trust-L0 {{ background: #fef3c7; color: #92400e; }}
    .risk {{ background: #fee2e2; color: var(--risk); }}
    .actions, .evidence {{ color: var(--muted); font-size: 14px; margin-top: 6px; }}
    .side {{ min-width: 170px; text-align: right; }}
    .price {{ font-size: 22px; font-weight: 700; margin-bottom: 8px; }}
    .coverage, .rejected {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    .coverage-row, .rejected-row {{ display: grid; grid-template-columns: 1.2fr .7fr .7fr .7fr .7fr 1.5fr 1fr; gap: 10px; padding: 10px 12px; border-top: 1px solid var(--line); font-size: 14px; }}
    .coverage-row:first-child, .rejected-row:first-child {{ border-top: 0; font-weight: 600; background: #f1f5f9; }}
    .rejected-row {{ grid-template-columns: 1fr 1fr 1fr 2fr; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .hidden {{ display: none; }}
    .empty {{ padding: 18px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; color: var(--muted); }}
    footer {{ padding: 18px 28px 32px; color: var(--muted); font-size: 13px; }}
    @media (max-width: 760px) {{
      .toolbar {{ grid-template-columns: 1fr 1fr; padding: 12px; }}
      main, header, footer {{ padding-left: 14px; padding-right: 14px; }}
      .listing {{ grid-template-columns: 1fr; }}
      .side {{ text-align: left; }}
      .coverage-row, .rejected-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="meta">
      <span>预算：{html.escape(str(profile.get("budget_target", "待核验")))} - {html.escape(str(profile.get("budget_max", "待核验")))}</span>
      <span>户型：{html.escape(_bedroom_meta(profile))}</span>
      <span>更新时间：{html.escape(str(meta.get("updated_at", "待核验")))}</span>
      <span>详情页打开：{html.escape(str(execution.get("detail_pages_opened", "待核验")))}</span>
    </div>
  </header>
  <section class="toolbar">
    <input id="q" placeholder="搜索小区、片区、标题">
    <select id="trust"><option value="">全部可信等级</option><option>L0</option><option>L1</option><option>L2</option><option>L3</option></select>
    <select id="status"><option value="">全部状态</option><option>new</option><option>shortlisted</option><option>contacted</option><option>scheduled</option><option>viewed</option><option>rejected</option><option>stale</option><option>leased</option></select>
    <select id="band"><option value="">全部分区</option><option value="main">主推荐</option><option value="lead_pool">线索池</option></select>
    <select id="risk"><option value="">全部风险</option><option value="snippet_only">snippet_only</option><option value="missing_contact_path">missing_contact_path</option><option value="commercial_utilities">commercial_utilities</option></select>
  </section>
  <main>
    <div class="summary" id="summary"></div>
    <section class="section">
      <div class="section-head"><h2>主推荐</h2><span class="hint">仅展示 L1+，来自打开详情页且字段足够的公开证据。</span></div>
      {main_rows}
    </section>
    <section class="section">
      <div class="section-head"><h2>线索池</h2><span class="hint">L0 只代表待核验线索，不得视为真实房源或已验证候选。</span></div>
      {lead_rows}
    </section>
    <section class="section">
      <div class="section-head"><h2>拒收 / 阻断</h2><span class="hint">登录墙、验证码、app下载墙、字段不足或隐私风险必须可审计。</span></div>
      <div class="rejected">{rejected_rows}</div>
    </section>
    <section class="section">
      <div class="section-head"><h2>来源覆盖</h2><span class="hint">区分计划覆盖、实际尝试、有效入池和阻断原因，避免把“未落盘”误判为“无房源”。</span></div>
      <div class="coverage">{coverage_rows}</div>
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
    office = profile.get("office_anchor") or "北京京东总部"
    bedrooms = profile.get("preferred_bedrooms")
    bedroom = f"{bedrooms}居室" if bedrooms else str(profile.get("bedroom_label") or "租房")
    budget = profile.get("budget_max") or "待核验"
    return f"{office} {budget} 内{bedroom}候选池"


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
    sources = " ".join(f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">来源</a>' for url in item.get("source_urls", [])[:3])
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
        <div class="actions">下一步：{html.escape("；".join(item.get("next_actions", [])) or "待核验")}</div>
        <div class="actions">来源：{sources or "待核验"}</div>
      </div>
      <aside class="side">
        <div class="price">{html.escape(str(item.get("price_text", "待核验")))}</div>
        <div class="actions">首次发现：{html.escape(str(item.get("first_seen_at", "待核验")))}</div>
      </aside>
    </article>
    """


def _render_rejected_item(item: dict[str, Any]) -> str:
    reasons = item.get("reject_reasons")
    reason_text = "；".join(str(reason) for reason in reasons) if isinstance(reasons, list) else str(reasons or "待核验")
    source = item.get("source_url")
    source_link = f'<a href="{html.escape(source)}" target="_blank" rel="noreferrer">打开</a>' if source else "无 URL"
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
        '<div class="coverage-row"><span>来源</span><span>计划</span><span>尝试</span><span>入池</span><span>详情页</span><span>阻断原因</span><span>域名</span></div>'
    ]
    for source, info in sorted(sources.items(), key=lambda row: str(row[1].get("source_name") if isinstance(row[1], dict) else row[0])):
        domains = ", ".join(info.get("domains", [])) if isinstance(info, dict) else ""
        source_name = info.get("source_name") or source
        attempted = _attempted_text(info)
        blocked = _blocked_text(info)
        rows.append(
            f'<div class="coverage-row"><span>{html.escape(str(source_name))}</span><span>{html.escape(str(info.get("planned_queries", 0)))}</span><span>{html.escape(attempted)}</span><span>{html.escape(str(info.get("accepted_items", 0)))}</span><span>{html.escape(str(info.get("detail_pages_opened", 0)))}</span><span>{html.escape(blocked)}</span><span>{html.escape(domains or "待核验")}</span></div>'
        )
    return "\n".join(rows)


def _attempted_text(info: dict[str, Any]) -> str:
    attempted = info.get("attempted_queries")
    if attempted is None:
        return "待记录"
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


def _trust_order(trust: str | None) -> int:
    return {"L3": 3, "L2": 2, "L1": 1, "L0": 0}.get(trust or "L0", 0)
