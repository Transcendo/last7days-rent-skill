from lib.schema import SearchRequest
from lib.sources.query import build_search_plan


def test_search_plan_builds_live_p0_query_descriptors():
    plan = build_search_plan(SearchRequest(city="上海", office_anchor="上海五角场", budget_max=5200, sources=["beike_lianjia", "fang"]))
    assert "beike_lianjia" in plan.source_queries
    assert "fang" in plan.source_queries
    assert "wujiaochang" in plan.source_queries["beike_lianjia"][0]["url"]
    assert "house-a026-b01647" in plan.source_queries["fang"][0]["url"]
    assert "platform" in plan.contact_requirements


def test_search_plan_expands_yizhuang_commute_areas():
    plan = build_search_plan(SearchRequest(city="北京", office_anchor="北京亦庄", budget_max=5200))
    assert "经海路" in plan.commute_areas
    assert "大族广场" in plan.commute_areas
