import json
from pathlib import Path

from lib.agent_evidence import ingest_evidence_file, validate_evidence_file
from lib.render import render_listing_pool_html


SEARCH_BRIEF = Path("tests/fixtures/search_briefs/jd_hq_search_brief.json")
EVIDENCE = Path("tests/fixtures/evidence/jd_hq_runtime_evidence_l0_l1_blocked.json")


def test_jd_search_brief_fixture_matches_poc_contract():
    brief = json.loads(SEARCH_BRIEF.read_text(encoding="utf-8"))
    assert brief["anchor_id"] == "beijing-jd-hq-yizhuang"
    assert brief["profile_constraints"]["budget_max"] == 6000
    assert brief["profile_constraints"]["preferred_bedrooms"] == 1
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
    joined_queries = " ".join(query["query"] for batch in brief["search_batches"] for query in batch["queries"])
    assert "经海路" in joined_queries
    assert "次渠南" in joined_queries
    assert "马驹桥" in joined_queries
    assert "site:douban.com/group" in joined_queries
    assert "site:wellcee.com/rent-apartment" in joined_queries
    assert "site:m.lianjia.com/chuzu/bj/brand/200301001000" in joined_queries
    assert "乐乎" in joined_queries
    assert "泊寓" in joined_queries
    assert "site:nowcoder.com" not in joined_queries
    assert "public_article" not in json.dumps(brief, ensure_ascii=False)


def test_jd_runtime_fixture_ingests_l1_l0_and_blocked_paths(tmp_path):
    assert validate_evidence_file(EVIDENCE) == []
    pool, output_path = ingest_evidence_file(EVIDENCE, pool_path=tmp_path / "pool.json")
    assert output_path.exists()

    assert len(pool["listings"]) == 2
    assert len(pool["rejected_items"]) == 1
    assert pool["source_coverage"]["source_count"] >= 10
    assert pool["source_coverage"]["planned_source_count"] >= 10
    assert pool["source_coverage"]["effective_source_count"] == 2
    assert pool["source_coverage"]["sources"]["wellcee"]["planned_queries"] > 0
    assert pool["source_coverage"]["sources"]["wellcee"]["attempted_queries"] is None
    assert pool["source_coverage"]["sources"]["wellcee"]["attempt_status"] == "not_logged"
    assert pool["source_coverage"]["sources"]["fang"]["accepted_items"] == 1
    assert pool["source_coverage"]["sources"]["brand_apartment_public"]["rejected_or_blocked"] == 1

    main = next(item for item in pool["listings"] if item["recommendation_band"] == "main")
    assert main["trust_level"] == "L1"
    assert main["community"] == "次渠南里"

    lead = next(item for item in pool["listings"] if item["recommendation_band"] == "lead_pool")
    assert lead["trust_level"] == "L0"
    assert "snippet_only" in lead["risk_flags"]

    blocked = pool["rejected_items"][0]
    assert "app_wall" in blocked["reject_reasons"]

    html = render_listing_pool_html(pool)
    assert "主推荐" in html
    assert "线索池" in html
    assert "拒收 / 阻断" in html
    assert "来源覆盖" in html
    assert "计划" in html
    assert "尝试" in html
    assert "入池" in html
    assert "待记录" in html
    assert "L0 不代表已验证房源" in html
