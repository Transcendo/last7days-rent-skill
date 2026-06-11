from __future__ import annotations

import json
from pathlib import Path

from ..schema import SearchLead, SearchProviderQuery, SearchProviderResult, now_iso
from .brave import map_brave_response
from .exa import map_exa_response
from .tavily import map_tavily_response


def load_fixture_search_leads(
    fixture_dir: Path,
    queries: list[SearchProviderQuery],
) -> tuple[list[SearchLead], list[SearchProviderResult], list[str]]:
    leads: list[SearchLead] = []
    results: list[SearchProviderResult] = []
    warnings: list[str] = []
    for query in queries:
        path = fixture_dir / f"{query.provider}_search_success.json"
        if not path.exists():
            provider_leads = _built_in_provider_leads(query)
            leads.extend(provider_leads)
            results.append(SearchProviderResult(provider=query.provider, status="fixture", query=query.query, lead_count=len(provider_leads)))
            warnings.append(f"missing provider fixture: {path.name}; used built_in_provider_fixture")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        provider_leads = _map_fixture(query, data)
        leads.extend(provider_leads)
        results.append(SearchProviderResult(provider=query.provider, status="fixture", query=query.query, lead_count=len(provider_leads)))
    return leads, results, warnings


def _map_fixture(query: SearchProviderQuery, data: dict) -> list[SearchLead]:
    if query.provider == "brave":
        return map_brave_response(data, query)
    if query.provider == "tavily":
        return map_tavily_response(data, query)
    if query.provider == "exa":
        return map_exa_response(data, query)
    return []


def _built_in_provider_leads(query: SearchProviderQuery) -> list[SearchLead]:
    now = now_iso()
    return [
        SearchLead(
            lead_id=f"fixture-{query.provider}-wellcee-001",
            provider=query.provider,
            query=query.query,
            rank=1,
            title="上海五角场 政立路附近整租一室户转租",
            url="https://www.wellcee.com/rent-apartment/fixture-001",
            domain="wellcee.com",
            snippet="五角场通勤圈租房，政立路附近整租一室户，平台内联系，价格和仍在租状态需打开详情页核验。",
            published_at=now,
            score=0.7,
            highlights=["整租一室户", "五角场租房", "平台联系入口"],
        ),
        SearchLead(
            lead_id=f"fixture-{query.provider}-fang-001",
            provider=query.provider,
            query=query.query,
            rank=2,
            title="江湾体育场附近 2室1厅 出租",
            url="https://zu.fang.com/chuzu/1_61403538_1.htm",
            domain="fang.com",
            snippet="房天下公开页面发现的出租线索，搜索摘要不能证明价格、电话或仍在租。",
            published_at=now,
            score=0.6,
            highlights=["出租", "江湾体育场", "平台详情页"],
        ),
        SearchLead(
            lead_id=f"fixture-{query.provider}-blog-001",
            provider=query.provider,
            query=query.query,
            rank=3,
            title="五角场生活指南",
            url="https://example.com/wujiaochang-guide",
            domain="example.com",
            snippet="五角场周边生活信息，不是 P0 房源域名。",
            published_at=now,
            score=0.2,
        ),
    ]
