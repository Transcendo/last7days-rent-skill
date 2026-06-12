from pathlib import Path

from lib.acquisition.classifier import classify_url
from lib.acquisition.query_builder import build_discovery_queries
from lib.acquisition.service import run_acquisition
from lib.commute_plan import derive_commute_areas
from lib.providers.config import ProviderConfig, load_provider_config
from lib.providers.registry import ProviderRegistry, ProviderResolution
from lib.providers.web import DDGSSearchProvider
from lib.schema import ExtractedDocument, ProviderDiagnostic, RentProfile, SearchHit, SearchRequest
from lib.sources.query import build_search_plan


WELLCEE_JSONLD = """
<html>
  <head>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": "亦庄核心区一居室 55㎡",
        "description": "靠近经海路，费用待确认。",
        "url": "https://www.wellcee.com/rent-apartment/fixture",
        "datePosted": "2026-06-08T00:00:00+00:00",
        "offers": { "price": 4300, "priceCurrency": "CNY" },
        "address": {
          "addressLocality": "北京",
          "addressRegion": "通州",
          "streetAddress": "亦庄核心区附近"
        }
      }
    </script>
  </head>
</html>
"""


def test_provider_config_reads_env_and_local_config(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    monkeypatch.setenv("EXA_API_KEY", "env-exa")
    Path(tmp_path / "config.json").write_text(
        '{"providers":{"search":"brave","extract":"tavily","api_keys":{"exa":"file-exa","brave":"file-brave"}}}',
        encoding="utf-8",
    )
    config = load_provider_config()
    assert config.search == "brave"
    assert config.extract == "tavily"
    assert config.api_key("exa") == "env-exa"
    assert config.api_key("brave") == "file-brave"


def test_registry_missing_explicit_provider_falls_back_to_ddgs(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(DDGSSearchProvider, "is_available", lambda self: True)
    resolution = ProviderRegistry(ProviderConfig(search="brave", extract="exa")).resolve()
    assert resolution.search_provider.name == "ddgs"
    assert resolution.extract_provider.name == "basic_http"
    assert any(diag.provider == "brave" and diag.status == "warning" for diag in resolution.diagnostics)


def test_url_classifier_marks_p0_p1_p2():
    assert classify_url("https://bj.zu.ke.com/zufang/").source_tier == "P0"
    assert classify_url("https://www.anjuke.com/").source_tier == "P1"
    assert classify_url("https://www.xiaohongshu.com/").source_tier == "P2"


def test_discovery_queries_use_source_plan_urls_and_area_hints():
    profile = RentProfile.from_dict(
        {"office_anchor": {"office_name": "北京亦庄办公点", "city": "北京"}, "commute": {"derived_areas": []}}
    )
    assert "经海路" in derive_commute_areas("北京亦庄办公点")
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄办公点", sources=["beike_lianjia", "fang", "wellcee"]), profile)
    queries = [item.query for item in build_discovery_queries(plan, profile)]
    assert any("site:bj.zu.ke.com/zufang" in query for query in queries)
    assert any("site:zu.fang.com" in query for query in queries)
    assert any("site:www.wellcee.com/rent-apartment" in query for query in queries)
    assert any("经海路" in query for query in queries)
    assert any("北京亦庄办公点 附近 租房 近7天" in query for query in queries)


def test_discovery_queries_use_profile_commute_areas_without_office_specific_hint():
    profile = RentProfile.from_dict(
        {"office_anchor": {"office_name": "北京示例办公点", "city": "北京"}, "commute": {"derived_areas": ["经海路", "大族广场"]}}
    )
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京示例办公点", sources=["beike_lianjia", "fang"]), profile)
    queries = [item.query for item in build_discovery_queries(plan, profile)]
    assert any("经海路" in query for query in queries)
    assert any("大族广场" in query for query in queries)


def test_acquisition_with_fake_providers_can_structure_p0_listing(monkeypatch):
    class FakeSearch:
        name = "fake_search"

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            return [
                SearchHit(
                    provider=self.name,
                    query=query,
                    title="北京通州1居整租",
                    url="https://www.wellcee.com/rent-apartment/fixture",
                    description="亦庄核心区附近，1居室，55㎡，4300 RMB/月",
                    position=1,
                )
            ]

    class FakeExtract:
        name = "fake_extract"

        def extract(self, urls, **options):
            return [
                ExtractedDocument(
                    provider=self.name,
                    requested_url=urls[0],
                    final_url=urls[0],
                    title="北京通州1居整租",
                    content=WELLCEE_JSONLD,
                    raw_content=WELLCEE_JSONLD,
                )
            ]

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=FakeSearch(),
            extract_provider=FakeExtract(),
            diagnostics=[ProviderDiagnostic("search", "auto", "fake_search", "fake_search", "selected")],
        )

    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    profile = RentProfile.from_dict({"office_anchor": {"office_name": "北京亦庄办公点", "city": "北京"}})
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄办公点"), profile)
    result = run_acquisition(plan, profile, limit=2)
    assert result.source_candidates
    assert result.actionable_leads
    assert result.structured_listings
    assert result.structured_listings[0].price_monthly == 4300


def test_no_key_basic_http_fallback_returns_l0_leads_without_extract(monkeypatch):
    class FakeSearch:
        name = "fake_search"

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            return [
                SearchHit(
                    provider=self.name,
                    query=query,
                    title="北京亦庄整租一居",
                    url="https://bj.zu.ke.com/zufang/yizhuang1/pg2/",
                    description="亦庄核心区，3500 元/月，36.00㎡，1室0厅，1天前维护",
                    position=1,
                )
            ]

    class BasicHttpShouldNotRun:
        name = "basic_http"

        def extract(self, urls, **options):
            raise AssertionError("basic_http must not run in default no-key search")

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=FakeSearch(),
            extract_provider=BasicHttpShouldNotRun(),
            diagnostics=[ProviderDiagnostic("extract", "auto", "basic_http", "basic_http", "fallback")],
        )

    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    profile = RentProfile.from_dict(
        {
            "office_anchor": {"office_name": "北京亦庄京东总部", "city": "北京"},
            "commute": {"derived_areas": ["亦庄", "经海路"]},
            "housing_constraints": {"budget_max": 5200, "min_bedrooms": 1},
        }
    )
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄京东总部"), profile)
    result = run_acquisition(plan, profile, limit=2)
    assert result.actionable_leads
    assert not result.extracted_documents
    assert not result.structured_listings
    assert any("detail enhancement skipped" in warning for warning in result.warnings)


def test_acquisition_continues_after_single_search_query_failure(monkeypatch):
    class FlakySearch:
        name = "flaky_search"

        def __init__(self):
            self.calls = 0

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary reset")
            return [
                SearchHit(
                    provider=self.name,
                    query=query,
                    title="北京亦庄1居整租",
                    url="https://www.wellcee.com/rent-apartment/fixture",
                    description="亦庄核心区附近，1居室，55㎡，4300 RMB/月",
                    position=1,
                )
            ]

    class FakeExtract:
        name = "fake_extract"

        def extract(self, urls, **options):
            return [
                ExtractedDocument(
                    provider=self.name,
                    requested_url=urls[0],
                    final_url=urls[0],
                    title="北京亦庄1居整租",
                    content=WELLCEE_JSONLD,
                    raw_content=WELLCEE_JSONLD,
                )
            ]

    flaky = FlakySearch()

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=flaky,
            extract_provider=FakeExtract(),
            diagnostics=[ProviderDiagnostic("search", "auto", "flaky_search", "flaky_search", "selected")],
        )

    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    profile = RentProfile.from_dict({"office_anchor": {"office_name": "北京亦庄京东总部", "city": "北京"}})
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄京东总部"), profile)
    result = run_acquisition(plan, profile, limit=2)
    assert any("temporary reset" in warning for warning in result.warnings)
    assert result.actionable_leads
    assert result.structured_listings


def test_provider_extract_plain_text_does_not_become_structured_listing(monkeypatch):
    class FakeSearch:
        name = "fake_search"

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            return [
                SearchHit(
                    provider=self.name,
                    query=query,
                    title="北京通州1居整租",
                    url="https://www.wellcee.com/rent-apartment/plain-text",
                    description="亦庄核心区附近，1居室，55㎡，4300 RMB/月",
                    position=1,
                )
            ]

    class FakeExtract:
        name = "fake_extract"

        def extract(self, urls, **options):
            return [
                ExtractedDocument(
                    provider=self.name,
                    requested_url=urls[0],
                    final_url=urls[0],
                    title="北京通州1居整租",
                    content="亦庄核心区附近，1居室，55㎡，4300 RMB/月",
                    raw_content="亦庄核心区附近，1居室，55㎡，4300 RMB/月",
                )
            ]

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=FakeSearch(),
            extract_provider=FakeExtract(),
            diagnostics=[ProviderDiagnostic("search", "auto", "fake_search", "fake_search", "selected")],
        )

    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    profile = RentProfile.from_dict({"office_anchor": {"office_name": "北京亦庄办公点", "city": "北京"}})
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄办公点"), profile)
    result = run_acquisition(plan, profile, limit=2)
    assert result.source_candidates
    assert result.actionable_leads
    assert not result.structured_listings
    assert any("provider extract kept as evidence only" in warning for warning in result.warnings)


def test_blocked_detail_keeps_l0_lead_and_records_blocked_source(monkeypatch):
    class FakeSearch:
        name = "fake_search"

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            return [
                SearchHit(
                    provider=self.name,
                    query=query,
                    title="北京亦庄一居整租",
                    url="https://www.wellcee.com/rent-apartment/blocked",
                    description="亦庄核心区附近，1居室，55㎡，4300 RMB/月，今天发布",
                    position=1,
                )
            ]

    class BlockedExtract:
        name = "fake_extract"

        def extract(self, urls, **options):
            return [
                ExtractedDocument(
                    provider=self.name,
                    requested_url=urls[0],
                    final_url=urls[0],
                    status="blocked",
                    error="captcha_detected",
                )
            ]

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=FakeSearch(),
            extract_provider=BlockedExtract(),
            diagnostics=[ProviderDiagnostic("extract", "auto", "fake_extract", "fake_extract", "selected")],
        )

    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    profile = RentProfile.from_dict(
        {
            "office_anchor": {"office_name": "北京亦庄办公点", "city": "北京"},
            "commute": {"derived_areas": ["亦庄"]},
            "housing_constraints": {"budget_max": 5200, "min_bedrooms": 1},
        }
    )
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄办公点"), profile)
    result = run_acquisition(plan, profile, limit=2)
    assert result.actionable_leads
    assert not result.structured_listings
    assert result.blocked_sources[0]["status"] == "blocked"
    assert "captcha_detected" in result.blocked_sources[0]["error"]


def test_p1_p2_search_hits_remain_candidates_only(monkeypatch):
    class FakeSearch:
        name = "fake_search"

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            return [
                SearchHit(provider=self.name, query=query, title="安居客候选", url="https://bj.anjuke.com/prop/view/A1", description="P1", position=1),
                SearchHit(provider=self.name, query=query, title="小红书候选", url="https://www.xiaohongshu.com/explore/A2", description="P2", position=2),
            ]

    class FakeExtract:
        name = "fake_extract"

        def extract(self, urls, **options):
            raise AssertionError("P1/P2 candidates must not enter extract")

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=FakeSearch(),
            extract_provider=FakeExtract(),
            diagnostics=[ProviderDiagnostic("search", "auto", "fake_search", "fake_search", "selected")],
        )

    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    profile = RentProfile.from_dict({"office_anchor": {"office_name": "北京亦庄办公点", "city": "北京"}})
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄办公点"), profile)
    result = run_acquisition(plan, profile, limit=2)
    assert {candidate.source_tier for candidate in result.source_candidates} == {"P1", "P2"}
    assert all(not candidate.can_promote for candidate in result.source_candidates)
    assert not result.actionable_leads
    assert not result.extracted_documents
    assert not result.structured_listings
