from pathlib import Path

from lib.acquisition.classifier import classify_url
from lib.acquisition.query_builder import build_discovery_queries
from lib.acquisition.service import run_acquisition
from lib.providers.config import ProviderConfig, load_provider_config
from lib.providers.registry import ProviderRegistry, ProviderResolution
from lib.providers.web import DDGSSearchProvider
from lib.schema import ExtractedDocument, ProviderDiagnostic, RentProfile, SearchHit, SearchRequest
from lib.sources.query import build_search_plan


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


def test_discovery_queries_include_yizhuang_office_anchors():
    profile = RentProfile.from_dict(
        {"office_anchor": {"office_name": "北京亦庄办公点", "city": "北京"}, "commute": {"derived_areas": []}}
    )
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄办公点"), profile)
    queries = [item.query for item in build_discovery_queries(plan, profile)]
    assert any("bj.zu.ke.com/zufang" in query for query in queries)
    assert any("经海路" in query for query in queries)
    assert any("wellcee.com/rent-apartment" in query for query in queries)


def test_acquisition_with_fake_providers_can_structure_p0_listing(monkeypatch):
    class FakeSearch:
        name = "fake_search"

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
    assert result.structured_listings
    assert result.structured_listings[0].price_monthly == 4300
