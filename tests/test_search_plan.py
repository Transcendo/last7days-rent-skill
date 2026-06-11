from lib.schema import SearchRequest
from lib.sources.query import build_search_plan


def test_search_plan_builds_live_p0_query_descriptors():
    plan = build_search_plan(
        SearchRequest(
            city="上海",
            office_anchor="上海五角场",
            budget_max=5200,
            sources=["wellcee"],
            providers=["brave", "tavily", "exa"],
        )
    )
    assert [query.provider for query in plan.provider_queries] == ["brave", "tavily", "exa"]
    assert all("上海" in query.query and "五角场" in query.query and "租房" in query.query for query in plan.provider_queries)
    assert all(query.include_domains == ["wellcee.com"] for query in plan.provider_queries)
    assert plan.provider_queries[0].freshness == "pw"
    assert "platform" in plan.contact_requirements
