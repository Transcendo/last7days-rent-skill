import json

from lib.pipeline import run_search
from lib.schema import SearchLead, SearchProviderResult


def test_fixture_pipeline_preserves_contact_and_rejects_non_mvp(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    result = run_search(fixture=True, output_dir=str(tmp_path / "reports"))
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["clusters"]
    assert evidence["search_leads"]
    assert all(lead["provider"] in {"brave", "tavily", "exa"} for lead in evidence["search_leads"])
    assert evidence["privacy"]["contact_methods_preserved_for_action"] is True
    assert all(cluster["canonical_listing"]["contact_methods"] for cluster in evidence["clusters"])
    assert {cluster["canonical_listing"]["source_id"] for cluster in evidence["clusters"]} <= {"beike_lianjia", "wellcee", "fang"}


def test_runtime_web_search_promotions_skip_provider_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))

    def fail_fetch(_plan):
        raise AssertionError("provider fallback should not run when runtime web search promoted listings")

    monkeypatch.setattr("lib.pipeline.fetch_search_leads", fail_fetch)
    result = run_search(
        output_dir=str(tmp_path / "reports"),
        office_anchor="上海五角场",
        city="上海",
        budget_max=5200,
        runtime_websearch_json="tests/fixtures/websearch/runtime_web_search_success.json",
    )
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert {item["provider"] for item in evidence["search_provider_coverage"]} == {"runtime_web_search"}
    assert {cluster["canonical_listing"]["source_id"] for cluster in evidence["clusters"]} == {"wellcee", "fang"}
    assert any(lead["provider"] == "runtime_web_search" for lead in evidence["promoted_leads"])


def test_runtime_web_search_without_promotions_falls_back_to_providers(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    runtime_path = tmp_path / "runtime-empty-promotion.json"
    runtime_path.write_text(
        json.dumps(
            {
                "query": "上海 五角场 租房",
                "success": True,
                "data": {
                    "web": [
                        {
                            "title": "上海租房讨论",
                            "url": "https://example.com/forum/rent",
                            "description": "租房讨论，不是 P0 域名。",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def provider_fetch(_plan):
        return (
            [
                SearchLead(
                    lead_id="fallback-wellcee",
                    provider="brave",
                    query="上海 五角场 租房",
                    rank=1,
                    title="五角场整租一室户",
                    url="https://www.wellcee.com/rent-apartment/fallback-001",
                    domain="wellcee.com",
                    snippet="上海五角场租房，整租一室户，平台联系。",
                )
            ],
            [SearchProviderResult(provider="brave", status="ok", query="上海 五角场 租房", lead_count=1)],
            [],
        )

    monkeypatch.setattr("lib.pipeline.fetch_search_leads", provider_fetch)
    result = run_search(
        output_dir=str(tmp_path / "reports"),
        office_anchor="上海五角场",
        city="上海",
        budget_max=5200,
        runtime_websearch_json=str(runtime_path),
    )
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert {item["provider"] for item in evidence["search_provider_coverage"]} == {"runtime_web_search", "brave"}
    assert evidence["clusters"][0]["canonical_listing"]["source_id"] == "wellcee"
    assert "runtime_web_search_leads_found_but_none_promoted" in evidence["warnings"]


def test_no_provider_fallback_keeps_runtime_only(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    runtime_path = tmp_path / "runtime-empty-promotion.json"
    runtime_path.write_text(
        json.dumps(
            {
                "query": "上海 五角场 租房",
                "success": True,
                "data": {"web": [{"title": "上海租房讨论", "url": "https://example.com/forum/rent", "description": "租房讨论"}]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fail_fetch(_plan):
        raise AssertionError("provider fallback should be disabled")

    monkeypatch.setattr("lib.pipeline.fetch_search_leads", fail_fetch)
    result = run_search(
        output_dir=str(tmp_path / "reports"),
        office_anchor="上海五角场",
        city="上海",
        budget_max=5200,
        runtime_websearch_json=str(runtime_path),
        provider_fallback=False,
    )
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert {item["provider"] for item in evidence["search_provider_coverage"]} == {"runtime_web_search"}
    assert evidence["clusters"] == []
    assert "live search did not produce shortlist candidates; see source coverage and blocking warnings." in evidence["warnings"]
