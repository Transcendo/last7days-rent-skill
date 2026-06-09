from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .commute_plan import profile_to_search_plan
from .dedupe import dedupe_listings
from .env import ensure_local_dirs
from .normalize import normalize_listings
from .profile_store import load_profile
from .render import render_chat_shortlist, render_evidence_package, render_markdown_report, write_outputs
from .schema import ListingItem, RentProfile, VerificationEvidence, now_iso
from .scoring import score_clusters
from .rerank import rerank_clusters
from .sources.router import load_fixture_sources


@dataclass
class SearchResult:
    chat_summary: str
    markdown_path: Path
    evidence_path: Path
    markdown: str
    evidence: dict


def default_fixture_profile() -> RentProfile:
    return RentProfile.from_dict(
        {
            "office_anchor": {
                "company": "示例公司",
                "office_name": "上海五角场",
                "address_hint": "五角场地铁站附近",
                "city": "上海",
                "confidence": 0.9,
            },
            "commute": {"max_minutes": 35, "preferred_transit": ["metro"], "derived_areas": ["五角场", "政立路", "江湾体育场"]},
            "housing_constraints": {"budget_min": 3500, "budget_max": 5200, "rental_mode": "whole", "move_in_by": None},
            "open_questions": [],
        }
    )


def built_in_fixture_sources() -> tuple[list[ListingItem], list[VerificationEvidence], list[str]]:
    now = now_iso()
    listings = [
        ListingItem(
            item_id="fixture-beike-001",
            source_id="beike_lianjia",
            source_tier="P0",
            platform_id="SH2143668995679584256",
            source_url="https://sh.zu.ke.com/zufang/SH2143668995679584256.html",
            title="政立路附近一室户 整租 42㎡",
            body="五角场通勤圈，整租一室户，42㎡，押一付三。",
            city="上海",
            district="杨浦",
            community_name="政立路小区",
            address_hint="政立路附近",
            price_monthly=4200,
            deposit="押一付三",
            layout="1室1厅",
            area_sqm=42.0,
            published_at=now,
            contact_route="platform",
            provenance={"title": "fixture.beike.title", "price_monthly": "fixture.beike.price"},
        ),
        ListingItem(
            item_id="fixture-wellcee-001",
            source_id="wellcee",
            source_tier="P0",
            source_url="https://www.wellcee.com/rent-apartment/fixture-001",
            title="政立路一室户转租 42㎡",
            body="靠近五角场，预算内，费用待确认。",
            city="上海",
            district="杨浦",
            community_name="政立路小区",
            address_hint="政立路附近",
            price_monthly=4200,
            deposit=None,
            layout="1室1厅",
            area_sqm=42.0,
            published_at=now,
            contact_route="platform",
            provenance={"title": "fixture.wellcee.jsonld.name", "price_monthly": "fixture.wellcee.offers.price"},
        ),
        ListingItem(
            item_id="fixture-fang-001",
            source_id="fang",
            source_tier="P0",
            source_url="https://zu.fang.com/chuzu/1_61403538_1.htm",
            title="江湾体育场附近 2室1厅 68㎡",
            body="房天下房源，地铁通勤方便。",
            city="上海",
            district="杨浦",
            community_name="江湾体育场小区",
            address_hint="江湾体育场附近",
            price_monthly=5100,
            deposit=None,
            layout="2室1厅",
            area_sqm=68.0,
            published_at=now,
            contact_route="platform",
            provenance={"title": "fixture.fang.title", "price_monthly": "fixture.fang.title"},
        ),
        ListingItem(
            item_id="fixture-58-001",
            source_id="58",
            source_tier="P2",
            title="五角场超低价一居 1800 元/月",
            body="只加微信，先交定金。",
            price_monthly=1800,
            contact_route="wechat",
            provenance={"title": "fixture.non_mvp"},
        ),
    ]
    evidences = [
        VerificationEvidence(
            evidence_id="verify-fixture-001",
            source_id="official_verifier",
            evidence_type="rental_verification_code",
            value="SH-VERIFY-001",
            url="https://example.gov/verify",
            notes="fixture official verifier evidence",
        )
    ]
    return listings, evidences, []


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "sources"


def load_fixture_profile() -> RentProfile:
    profile_path = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "profile" / "profile.json"
    if profile_path.exists():
        import json

        return RentProfile.from_dict(json.loads(profile_path.read_text(encoding="utf-8")))
    return default_fixture_profile()


def collect_fixture_inputs() -> tuple[RentProfile, list[ListingItem], list[VerificationEvidence], list[str]]:
    profile = load_fixture_profile()
    fixture_dir = _fixture_dir()
    if fixture_dir.exists():
        listings, evidences, warnings = load_fixture_sources(fixture_dir)
        if listings:
            return profile, listings, evidences, warnings
    listings, evidences, warnings = built_in_fixture_sources()
    return profile, listings, evidences, warnings


def run_search(fixture: bool = False, limit: int = 5, output_dir: str | None = None) -> SearchResult:
    paths = ensure_local_dirs()
    if fixture:
        profile, raw_listings, evidences, warnings = collect_fixture_inputs()
    else:
        profile = load_profile()
        if not profile:
            raise SystemExit("尚未找到本地 profile。请先运行 profile init，或使用 search --fixture。")
        raw_listings, evidences, warnings = [], [], ["MVP 当前只实现 fixture/offline dry run；真实网络采集需由后续 adapter 调用。"]
    profile_to_search_plan(profile)
    accepted, rejected = normalize_listings(raw_listings, profile)
    warnings.extend(f"rejected {item.source_id}:{item.item_id} due to {', '.join(item.risk_flags)}" for item in rejected)
    clusters = dedupe_listings(accepted)
    scored = score_clusters(clusters, profile)
    ranked = rerank_clusters(scored, limit=limit)
    reports_dir = Path(output_dir).expanduser() if output_dir else paths.reports_dir
    basename = "last7days-rent-fixture" if fixture else "last7days-rent-report"
    markdown = render_markdown_report(profile, ranked, evidences, warnings)
    evidence = render_evidence_package(profile, ranked, evidences, warnings)
    markdown_path, evidence_path = write_outputs(reports_dir, basename, markdown, evidence)
    chat_summary = render_chat_shortlist(profile, ranked)
    return SearchResult(chat_summary, markdown_path, evidence_path, markdown, evidence)
