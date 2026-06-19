from lib.agent_evidence import validate_evidence_file
from lib.anchor_pack import build_search_brief, load_anchor_pack


def test_runtime_adapter_contract_fixture_is_valid():
    assert validate_evidence_file("tests/fixtures/evidence/jd_hq_runtime_evidence.json") == []


def test_search_brief_contains_runtime_budget_and_collection_rules():
    brief = build_search_brief(
        {
            "user_goal": {"scenario": "jd_hq_beijing_poc"},
            "office_anchor": {"anchor_id": "beijing-jd-hq-yizhuang"},
            "housing_constraints": {"preferred_bedrooms": 2, "budget_max": 5500},
            "commute_preferences": {"strategy": "near_first"},
            "risk_preferences": {"source_strategy": "public_all_channels"},
        },
        load_anchor_pack(),
    )
    assert brief["run_budget"]["max_detail_pages_total"] == 48
    assert brief["run_budget"]["target_l1_or_better"] == 8
    assert brief["collection_rules"]["l0_policy"] == "lead_pool_only"
    assert brief["collection_rules"]["main_recommendation_min_trust"] == "L1"
    assert "batch_id" in brief["collection_rules"]["must_capture"]
    assert "raw_excerpt" in brief["collection_rules"]["must_capture"]
    assert "risk_checks" in brief
    assert "商水商电" in brief["risk_checks"]
