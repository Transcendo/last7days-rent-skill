from __future__ import annotations

import json
import html
from pathlib import Path
from typing import Any

from .privacy import assert_public_safe
from .store import write_text


def render_listing_pool_html(pool: dict[str, Any]) -> str:
    meta = pool.get("pool_meta", {})
    profile = pool.get("profile_summary", {})
    listings = pool.get("listings", [])
    title = _report_title(profile)
    payload = json.dumps(listings, ensure_ascii=False)
    rows = "\n".join(_render_listing_card(item) for item in listings) or '<section class="empty">暂无候选房源</section>'
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
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px 16px; color: var(--muted); font-size: 14px; }}
    .toolbar {{ display: grid; grid-template-columns: minmax(180px, 1fr) repeat(4, minmax(120px, 160px)); gap: 10px; padding: 14px 28px; border-bottom: 1px solid var(--line); background: var(--panel); position: sticky; top: 0; z-index: 1; }}
    input, select {{ width: 100%; min-height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; background: #fff; color: var(--text); font-size: 14px; }}
    main {{ padding: 18px 28px 32px; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; color: var(--muted); }}
    .summary span {{ border: 1px solid var(--line); border-radius: 6px; padding: 6px 9px; background: var(--panel); }}
    .listing {{ display: grid; grid-template-columns: 1fr auto; gap: 14px; padding: 16px; margin-bottom: 12px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .listing h2 {{ margin: 0 0 8px; font-size: 18px; line-height: 1.35; letter-spacing: 0; }}
    .facts {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }}
    .chip {{ display: inline-flex; align-items: center; min-height: 26px; padding: 3px 8px; border-radius: 999px; background: #eef2f7; color: #2f3742; font-size: 13px; }}
    .trust-L2, .trust-L3 {{ background: #dcfce7; color: #166534; }}
    .trust-L1 {{ background: #e0f2fe; color: #075985; }}
    .trust-L0 {{ background: #fef3c7; color: #92400e; }}
    .risk {{ background: #fee2e2; color: var(--risk); }}
    .actions {{ color: var(--muted); font-size: 14px; }}
    .side {{ min-width: 160px; text-align: right; }}
    .price {{ font-size: 22px; font-weight: 700; margin-bottom: 8px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .hidden {{ display: none; }}
    .empty {{ padding: 28px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; color: var(--muted); }}
    footer {{ padding: 18px 28px 32px; color: var(--muted); font-size: 13px; }}
    @media (max-width: 760px) {{
      .toolbar {{ grid-template-columns: 1fr 1fr; padding: 12px; }}
      main, header, footer {{ padding-left: 14px; padding-right: 14px; }}
      .listing {{ grid-template-columns: 1fr; }}
      .side {{ text-align: left; }}
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
    </div>
  </header>
  <section class="toolbar">
    <input id="q" placeholder="搜索小区、片区、标题">
    <select id="trust"><option value="">全部可信等级</option><option>L0</option><option>L1</option><option>L2</option><option>L3</option></select>
    <select id="status"><option value="">全部状态</option><option>new</option><option>shortlisted</option><option>contacted</option><option>rejected</option></select>
    <select id="risk"><option value="">全部风险</option><option value="snippet_only">snippet_only</option><option value="missing_contact_path">missing_contact_path</option></select>
    <select id="sort"><option value="priority">优先级</option><option value="price">价格从低到高</option><option value="trust">可信等级</option></select>
  </section>
  <main>
    <div class="summary" id="summary"></div>
    <div id="list">{rows}</div>
  </main>
  <footer>来源仅为公开页面或用户授权内容。未知字段显示为待核验；不保存 cookie、token、session 或登录态。</footer>
  <script>
    const listings = {payload};
    const cards = [...document.querySelectorAll('.listing')];
    function update() {{
      const q = document.querySelector('#q').value.trim().toLowerCase();
      const trust = document.querySelector('#trust').value;
      const status = document.querySelector('#status').value;
      const risk = document.querySelector('#risk').value;
      let visible = 0;
      cards.forEach(card => {{
        const text = card.dataset.text.toLowerCase();
        const ok = (!q || text.includes(q)) && (!trust || card.dataset.trust === trust) && (!status || card.dataset.status === status) && (!risk || card.dataset.risk.includes(risk));
        card.classList.toggle('hidden', !ok);
        if (ok) visible++;
      }});
      document.querySelector('#summary').innerHTML = `<span>当前显示：${{visible}}</span><span>总候选：${{listings.length}}</span><span>L2+：${{listings.filter(x => ['L2','L3'].includes(x.trust_level)).length}}</span>`;
    }}
    document.querySelectorAll('input,select').forEach(el => el.addEventListener('input', update));
    update();
  </script>
</body>
</html>
"""
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


def _render_listing_card(item: dict[str, Any]) -> str:
    text = " ".join(str(item.get(key, "")) for key in ["title", "community", "district_hint", "price_text", "layout_text"])
    risks = item.get("risk_flags", [])
    chips = [
        f'<span class="chip trust-{html.escape(str(item.get("trust_level", "L0")))}">{html.escape(str(item.get("trust_level", "L0")))}</span>',
        f'<span class="chip">{html.escape(str(item.get("status", "new")))}</span>',
        f'<span class="chip">{html.escape(str(item.get("district_hint", "待核验")))}</span>',
    ]
    chips.extend(f'<span class="chip risk">{html.escape(str(risk))}</span>' for risk in risks)
    sources = " ".join(f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">来源</a>' for url in item.get("source_urls", [])[:3])
    return f"""
    <article class="listing" data-text="{html.escape(text)}" data-trust="{html.escape(str(item.get("trust_level", "L0")))}" data-status="{html.escape(str(item.get("status", "new")))}" data-risk="{html.escape(" ".join(risks))}">
      <div>
        <h2>{html.escape(str(item.get("title", "待核验")))}</h2>
        <div class="facts">{''.join(chips)}</div>
        <div class="facts">
          <span class="chip">{html.escape(str(item.get("community", "待核验")))}</span>
          <span class="chip">{html.escape(str(item.get("area_text", "待核验")))}</span>
          <span class="chip">{html.escape(str(item.get("layout_text", "待核验")))}</span>
        </div>
        <div class="actions">下一步：{html.escape("；".join(item.get("next_actions", [])) or "待核验")}</div>
        <div class="actions">来源：{sources or "待核验"}</div>
      </div>
      <aside class="side">
        <div class="price">{html.escape(str(item.get("price_text", "待核验")))}</div>
        <div class="actions">首次发现：{html.escape(str(item.get("first_seen_at", "待核验")))}</div>
      </aside>
    </article>
    """
