import json

from lib.acquisition import AcquisitionResult
from lib.leads import build_candidate_leads
from lib.pipeline import run_search
from lib.privacy import public_text_violations
from lib.render import render_chat_shortlist, render_evidence_package, render_markdown_report
from lib.schema import RentProfile, SourceCandidate


def test_fixture_search_outputs_report_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    result = run_search(fixture=True, output_dir=str(tmp_path / "reports"))
    assert result.markdown_path.exists()
    assert result.evidence_path.exists()
    assert "7 天租房行动计划" in result.markdown
    assert "P0 Source Coverage" in result.markdown
    assert "L1 不是已验真" in result.markdown
    assert public_text_violations(result.markdown) == []
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["privacy"]["contact_methods_preserved_for_action"] is True
    assert evidence["privacy"]["secret_guard_enabled"] is True
    assert evidence["clusters"]


def test_ddgs_candidates_render_as_pending_user_leads():
    profile = RentProfile.from_dict(
        {
            "office_anchor": {"office_name": "北京亦庄京东总部", "city": "北京"},
            "commute": {"derived_areas": ["亦庄", "经海路"], "max_minutes": 30},
            "housing_constraints": {"budget_max": 5200, "min_bedrooms": 1, "rental_mode": "whole"},
        }
    )
    candidates = [
        SourceCandidate(
                candidate_id="ok",
                source_id="beike_lianjia",
                source_tier="P0",
                source_url="https://bj.zu.ke.com/zufang/yizhuang1/pg2/",
                title="北京亦庄整租一居",
                snippet="3500 元/月，36.00㎡，1室0厅，1天前维护",
                provider="ddgs",
                visible_fields={
                    "price_text": "3500 元/月",
                    "area_text": "36.00㎡",
                    "layout_text": "1室0厅",
                    "freshness_text": "1天前维护",
                },
        ),
        SourceCandidate(
                candidate_id="studio",
                source_id="beike_lianjia",
                source_tier="P0",
                source_url="https://bj.zu.ke.com/zufang/yizhuang1/studio/",
                title="北京亦庄开间",
                snippet="3100 元/月，33.00㎡，开间，今天维护",
                provider="ddgs",
                visible_fields={"price_text": "3100 元/月", "area_text": "33.00㎡", "layout_text": "开间"},
        ),
        SourceCandidate(
                candidate_id="over",
                source_id="beike_lianjia",
                source_tier="P0",
                source_url="https://bj.zu.ke.com/zufang/yizhuang1/over/",
                title="北京亦庄大户型",
                snippet="8800 元/月，52.34㎡，1室1厅，2天前维护",
                provider="ddgs",
                visible_fields={"price_text": "8800 元/月", "area_text": "52.34㎡", "layout_text": "1室1厅"},
        ),
        SourceCandidate(
                candidate_id="generic",
                source_id="beike_lianjia",
                source_tier="P0",
                source_url="https://bj.zu.ke.com/zufang/rs/",
                title="北京租房信息",
                snippet="5000 元/月，102.00㎡，2室1厅，1天前维护",
                provider="ddgs",
                visible_fields={
                    "price_text": "5000 元/月",
                    "area_text": "102.00㎡",
                    "layout_text": "2室1厅",
                    "freshness_text": "1天前维护",
                },
        ),
    ]
    leads = build_candidate_leads(profile, candidates, limit=5)
    acquisition = AcquisitionResult(source_candidates=candidates, actionable_leads=leads)

    chat = render_chat_shortlist(profile, [], acquisition=acquisition)
    assert "待核验房源线索" in chat
    assert "https://bj.zu.ke.com/zufang/yizhuang1/pg2/" in chat
    assert "studio" not in chat
    assert "over" not in chat
    assert "https://bj.zu.ke.com/zufang/rs/" not in chat

    report = render_markdown_report(profile, [], [], [], live=True, acquisition=acquisition)
    assert "## L0 待核验房源线索" in report
    assert "L0 待打开平台页核验" in report

    evidence = render_evidence_package(profile, [], [], [], live=True, acquisition=acquisition)
    assert evidence["actionable_leads"][0]["status"] == "candidate_only_pending_platform_verification"
    assert evidence["actionable_candidate_leads"][0]["status"] == "candidate_only_pending_platform_verification"
