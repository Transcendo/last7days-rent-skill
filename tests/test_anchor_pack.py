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
    joined_queries = " ".join(query for batch in brief["search_batches"] for query in batch["queries"])
    assert "二居室" in joined_queries
    assert "5500" in joined_queries
    assert brief["profile_summary"]["bedroom_label"] == "二居室"
    assert brief["run_budget"]["target_accepted_listings"] == 10
