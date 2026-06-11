import json

from lib.schema import SearchLead, SearchPlan, SearchProviderQuery, SearchRequest
from lib.search_providers.brave import build_brave_params, map_brave_response
from lib.search_providers.exa import build_exa_payload, map_exa_response
from lib.search_providers.promote import promote_search_leads
from lib.search_providers.router import _warning_for_status, fetch_search_leads
from lib.search_providers.runtime_web_search import RuntimeWebSearchError, load_runtime_web_search
from lib.search_providers.tavily import build_tavily_payload, map_tavily_response


def test_provider_request_builders_clamp_and_disable_expensive_defaults():
    query = SearchProviderQuery(
        provider="brave",
        query="上海 五角场 租房 5200以内 近7天",
        limit=99,
        days=7,
        include_domains=["wellcee.com"],
    )
    brave = build_brave_params(query)
    assert brave["count"] == 20
    assert "site:wellcee.com" in brave["q"]
    assert brave["freshness"] == "pw"

    tavily = build_tavily_payload(SearchProviderQuery(provider="tavily", query=query.query, limit=3, days=7))
    assert tavily["include_answer"] is False
    assert tavily["include_raw_content"] is False
    assert tavily["search_depth"] == "basic"
    assert tavily["time_range"] == "week"

    exa = build_exa_payload(SearchProviderQuery(provider="exa", query=query.query, limit=5, days=7, include_domains=["fang.com"]))
    assert exa["numResults"] == 5
    assert exa["includeDomains"] == ["fang.com"]
    assert "summary" not in exa["contents"]


def test_provider_fixtures_map_to_search_leads():
    query = SearchProviderQuery(provider="brave", query="上海 五角场 租房", limit=5)
    brave_data = json.loads(open("tests/fixtures/websearch/brave_search_success.json", encoding="utf-8").read())
    leads = map_brave_response(brave_data, query)
    assert leads[0].provider == "brave"
    assert leads[0].domain == "wellcee.com"

    tavily_data = json.loads(open("tests/fixtures/websearch/tavily_search_success.json", encoding="utf-8").read())
    tavily_leads = map_tavily_response(tavily_data, SearchProviderQuery(provider="tavily", query=query.query, limit=5))
    assert tavily_leads[0].score == 0.84

    exa_data = json.loads(open("tests/fixtures/websearch/exa_search_success.json", encoding="utf-8").read())
    exa_leads = map_exa_response(exa_data, SearchProviderQuery(provider="exa", query=query.query, limit=5))
    assert exa_leads[0].published_at is None
    assert "summary" not in exa_leads[0].raw


def test_no_key_returns_provider_warning_without_network(monkeypatch):
    for key in ["BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    plan = SearchPlan(
        request=SearchRequest(city="上海", office_anchor="五角场", providers=["brave"]),
        provider_queries=[SearchProviderQuery(provider="brave", query="上海 五角场 租房")],
    )
    leads, results, warnings = fetch_search_leads(plan)
    assert leads == []
    assert results[0].status == "skipped"
    assert "brave_missing_api_key" in warnings
    assert "no_search_provider_available" in warnings


def test_provider_http_status_warning_mapping_is_stable():
    assert _warning_for_status("brave", 401) == "brave_auth_failed"
    assert _warning_for_status("tavily", 402) == "tavily_quota_limited"
    assert _warning_for_status("exa", 422) == "exa_invalid_request"
    assert _warning_for_status("brave", 429) == "brave_rate_limited"
    assert _warning_for_status("exa", 503) == "exa_provider_error"


def test_promotion_gate_only_allows_p0_rental_leads():
    leads = [
        SearchLead(
            lead_id="ok",
            provider="brave",
            query="q",
            rank=1,
            title="五角场整租一室户",
            url="https://www.wellcee.com/rent-apartment/fixture-001",
            domain="wellcee.com",
            snippet="上海五角场租房，平台联系。",
        ),
        SearchLead(
            lead_id="bad-domain",
            provider="brave",
            query="q",
            rank=2,
            title="上海租房讨论",
            url="https://example.com/rent",
            domain="example.com",
            snippet="租房讨论帖",
        ),
        SearchLead(
            lead_id="bad-semantics",
            provider="brave",
            query="q",
            rank=3,
            title="五角场生活指南",
            url="https://www.wellcee.com/rent-apartment/guide",
            domain="wellcee.com",
            snippet="餐饮交通信息",
        ),
    ]
    listings, promoted, rejected = promote_search_leads(leads)
    assert len(listings) == 1
    assert listings[0].source_id == "wellcee"
    assert listings[0].trust_level == "L1"
    assert listings[0].contact_methods[0].entry_url == "https://www.wellcee.com/rent-apartment/fixture-001"
    assert promoted[0].can_promote is True
    assert {lead.rejection_reason for lead in rejected} == {"non_p0_domain", "no_rental_semantics"}


def test_runtime_web_search_fixture_maps_to_search_leads():
    leads, results, warnings = load_runtime_web_search("tests/fixtures/websearch/runtime_web_search_success.json")
    assert results[0].provider == "runtime_web_search"
    assert results[0].status == "ok"
    assert results[0].lead_count == 3
    assert leads[0].provider == "runtime_web_search"
    assert leads[0].domain == "wellcee.com"
    assert leads[0].raw["runtime_provider"] == "codex_web_search"
    assert "runtime_web_search_missing_url" in warnings


def test_runtime_web_search_direct_shape_requires_runtime_query(tmp_path):
    path = tmp_path / "direct.json"
    path.write_text(
        json.dumps(
            {
                "success": True,
                "data": {"web": [{"title": "五角场整租", "url": "https://www.wellcee.com/rent-apartment/direct-001", "description": "租房"}]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    try:
        load_runtime_web_search(path)
    except RuntimeWebSearchError as exc:
        assert "--runtime-query" in str(exc)
    else:
        raise AssertionError("missing runtime query should fail")

    leads, results, warnings = load_runtime_web_search(path, runtime_query="上海 五角场 租房")
    assert warnings == []
    assert results[0].query == "上海 五角场 租房"
    assert leads[0].title == "五角场整租"


def test_runtime_web_search_malformed_json_reports_clear_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    try:
        load_runtime_web_search(path, runtime_query="上海 五角场 租房")
    except RuntimeWebSearchError as exc:
        assert "runtime websearch JSON is invalid" in str(exc)
    else:
        raise AssertionError("malformed runtime JSON should fail")


def test_runtime_web_search_failed_payload_becomes_failed_provider_result(tmp_path):
    path = tmp_path / "failed.json"
    path.write_text(json.dumps({"query": "上海 五角场 租房", "success": False}, ensure_ascii=False), encoding="utf-8")
    leads, results, warnings = load_runtime_web_search(path)
    assert leads == []
    assert results[0].status == "failed"
    assert results[0].warning == "runtime_web_search_failed"
    assert warnings == ["runtime_web_search_failed"]


def test_runtime_web_search_leads_pass_existing_promotion_gate():
    leads, _, _ = load_runtime_web_search("tests/fixtures/websearch/runtime_web_search_success.json")
    listings, promoted, rejected = promote_search_leads(leads)
    assert {listing.source_id for listing in listings} == {"wellcee", "fang"}
    assert all(lead.provider == "runtime_web_search" for lead in promoted)
    assert {lead.rejection_reason for lead in rejected} == {"non_p0_domain"}
