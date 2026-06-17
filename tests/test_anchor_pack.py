from lib.anchor_pack import build_search_brief, load_anchor_pack


def test_search_brief_derives_budget_and_bedroom_from_profile():
    profile = {
        "user_goal": {"scenario": "jd_hq_beijing_poc"},
        "office_anchor": {"anchor_id": "beijing-jd-hq-yizhuang"},
        "housing_constraints": {"preferred_bedrooms": 2, "budget_target": 5000, "budget_max": 5500},
        "commute_preferences": {
            "strategy": "near_first",
            "derived_zones_priority": ["经海路", "次渠南"],
            "expand_zones_if_sparse": ["马驹桥"],
        },
        "risk_preferences": {"source_strategy": "public_all_channels"},
    }
    brief = build_search_brief(profile, load_anchor_pack())
    joined_queries = " ".join(query["query"] for batch in brief["search_batches"] for query in batch["queries"])
    assert "二居室" in joined_queries
    assert "5500" in joined_queries
    assert brief["profile_summary"]["bedroom_label"] == "二居室"
    assert brief["run_budget"]["target_candidates_total"] == 30
    assert brief["run_budget"]["max_detail_pages_total"] == 48
    assert brief["collection_rules"]["l0_policy"] == "lead_pool_only"
    assert brief["collection_rules"]["main_recommendation_min_trust"] == "L1"
    assert {batch["batch_id"] for batch in brief["search_batches"]} >= {
        "p0_price_anchor",
        "near_office",
        "main_residential",
        "space_budget_backup",
        "transfer_personal",
        "brand_apartment",
    }
    source_ids = {source for batch in brief["search_batches"] for query in batch["queries"] for source in query["sources"]}
    assert {"wellcee", "lianjia_mobile_list", "lefull", "inboyu", "brand_apartment_public"} <= source_ids
    assert "nowcoder_public" not in source_ids
    assert "public_article" not in source_ids


def test_anchor_pack_contains_nesthub_guide_and_core_jd_zones():
    pack = load_anchor_pack()
    guide_urls = {source["source_url"] for source in pack["guide_sources"]}
    assert "https://nest-hub.eggcampus.com/docs/beijing/jd-headquarters-renting-guide" in guide_urls

    zones = {zone["zone_id"]: zone for zone in pack["commute_zones"]}
    assert {"near_office", "main_residential", "space_budget_backup"} <= set(zones)
    assert "经海路" in zones["near_office"]["keywords"]
    assert "次渠南" in zones["main_residential"]["keywords"]
    assert "马驹桥" in zones["space_budget_backup"]["keywords"]


def test_search_brief_query_objects_are_runtime_executable():
    brief = build_search_brief(
        {
            "office_anchor": {"anchor_id": "beijing-jd-hq-yizhuang"},
            "housing_constraints": {"preferred_bedrooms": 1, "budget_target": 5000, "budget_max": 6000},
            "risk_preferences": {"source_strategy": "public_all_channels"},
        },
        load_anchor_pack(),
    )
    first_query = brief["search_batches"][0]["queries"][0]
    assert {"query_id", "query", "zone_id", "expected_url_classes", "sources"} <= set(first_query)
    assert "一居室" in first_query["query"]
    assert "京东总部" in first_query["query"]
