from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .commute_plan import profile_to_search_plan
from .commute_plan import derive_commute_areas
from .contact import platform_contact
from .dedupe import dedupe_listings
from .env import ensure_local_dirs
from .normalize import normalize_listings
from .profile_store import load_profile
from .render import render_chat_shortlist, render_evidence_package, render_html_report, write_outputs
from .schema import ListingItem, RentProfile, SearchLead, SearchPlan, SearchProviderResult, SearchRequest, SourceFetchResult, VerificationEvidence, now_iso
from .scoring import score_clusters
from .rerank import rerank_clusters
from .search_providers.fixtures import load_fixture_search_leads
from .search_providers.promote import promote_search_leads
from .search_providers.router import fetch_search_leads
from .search_providers.runtime_web_search import RuntimeWebSearchError, load_runtime_web_search
from .sources.query import build_search_plan, request_from_profile
from .sources.router import load_fixture_sources


@dataclass
class SearchResult:
    chat_summary: str
    html_path: Path
    evidence_path: Path
    html: str
    evidence: dict
    source_fetches: list[SourceFetchResult]
    search_provider_results: list[SearchProviderResult]
    search_leads: list[SearchLead]
    promoted_leads: list[SearchLead]
    rejected_leads: list[SearchLead]

    @property
    def markdown_path(self) -> Path:
        return self.html_path

    @property
    def markdown(self) -> str:
        return self.html


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
            contact_methods=[platform_contact("https://sh.zu.ke.com/zufang/SH2143668995679584256.html", "built_in_fixture.beike.url")],
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
            contact_methods=[platform_contact("https://www.wellcee.com/rent-apartment/fixture-001", "built_in_fixture.wellcee.url")],
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
            contact_methods=[platform_contact("https://zu.fang.com/chuzu/1_61403538_1.htm", "built_in_fixture.fang.url")],
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


def _provider_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "websearch"


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


def collect_fixture_search_inputs(
    *,
    limit: int,
    days: int,
    sources: list[str] | None = None,
    providers: list[str] | None = None,
) -> tuple[
    RentProfile,
    list[ListingItem],
    list[VerificationEvidence],
    list[str],
    list[SearchProviderResult],
    list[SearchLead],
    list[SearchLead],
    list[SearchLead],
]:
    profile = load_fixture_profile()
    request = request_from_profile(profile, limit=limit, days=days, sources=sources, providers=providers)
    plan = build_search_plan(request, profile)
    leads, provider_results, warnings = load_fixture_search_leads(_provider_fixture_dir(), plan.provider_queries)
    listings, promoted_leads, rejected_leads = promote_search_leads(leads)
    legacy_evidences: list[VerificationEvidence] = []
    fixture_dir = _fixture_dir()
    if fixture_dir.exists():
        _, legacy_evidences, legacy_warnings = load_fixture_sources(fixture_dir)
        warnings.extend(legacy_warnings)
    if listings:
        return profile, listings, legacy_evidences, warnings, provider_results, leads, promoted_leads, rejected_leads
    legacy_profile, legacy_listings, legacy_evidences, legacy_warnings = collect_fixture_inputs()
    warnings.extend(legacy_warnings)
    return legacy_profile, legacy_listings, legacy_evidences, warnings, provider_results, leads, promoted_leads, rejected_leads


def profile_from_request(request: SearchRequest) -> RentProfile:
    return RentProfile.from_dict(
        {
            "office_anchor": {
                "office_name": request.office_anchor,
                "address_hint": request.office_anchor,
                "city": request.city,
                "confidence": 0.6 if request.office_anchor else 0.0,
            },
            "commute": {"max_minutes": 35, "derived_areas": derive_commute_areas(request.office_anchor)},
            "housing_constraints": {
                "budget_min": request.budget_min,
                "budget_max": request.budget_max,
                "rental_mode": "either",
            },
            "open_questions": [] if request.office_anchor and request.city else ["请确认办公点、城市和通勤上限。"],
        }
    )


def collect_live_search_inputs(
    *,
    plan: SearchPlan,
    runtime_websearch_json: str | None = None,
    runtime_query: str | None = None,
    provider_fallback: bool = True,
) -> tuple[
    list[ListingItem],
    list[VerificationEvidence],
    list[str],
    list[SourceFetchResult],
    list[SearchProviderResult],
    list[SearchLead],
    list[SearchLead],
    list[SearchLead],
]:
    evidences: list[VerificationEvidence] = []
    source_fetches: list[SourceFetchResult] = []
    search_provider_results: list[SearchProviderResult] = []
    search_leads: list[SearchLead] = []
    warnings: list[str] = []

    should_fetch_provider_fallback = True
    if runtime_websearch_json:
        try:
            runtime_leads, runtime_results, runtime_warnings = load_runtime_web_search(
                runtime_websearch_json,
                runtime_query=runtime_query,
            )
        except RuntimeWebSearchError as exc:
            raise SystemExit(str(exc)) from exc
        search_leads.extend(runtime_leads)
        search_provider_results.extend(runtime_results)
        warnings.extend(runtime_warnings)
        _, runtime_promoted, _ = promote_search_leads(runtime_leads)
        should_fetch_provider_fallback = provider_fallback and not runtime_promoted
        if runtime_leads and not runtime_promoted:
            warnings.append("runtime_web_search_leads_found_but_none_promoted")

    if not runtime_websearch_json or should_fetch_provider_fallback:
        provider_leads, provider_results, provider_warnings = fetch_search_leads(plan)
        search_leads.extend(provider_leads)
        search_provider_results.extend(provider_results)
        warnings.extend(provider_warnings)

    raw_listings, promoted_leads, rejected_leads = promote_search_leads(search_leads)
    if search_leads and not promoted_leads:
        warnings.append("search_leads_found_but_none_promoted")
    return (
        raw_listings,
        evidences,
        warnings,
        source_fetches,
        search_provider_results,
        search_leads,
        promoted_leads,
        rejected_leads,
    )


def run_search(
    fixture: bool = False,
    limit: int = 5,
    output_dir: str | None = None,
    office_anchor: str | None = None,
    city: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    days: int = 7,
    sources: list[str] | None = None,
    providers: list[str] | None = None,
    runtime_websearch_json: str | None = None,
    runtime_query: str | None = None,
    provider_fallback: bool = True,
) -> SearchResult:
    paths = ensure_local_dirs()
    source_fetches: list[SourceFetchResult] = []
    search_provider_results: list[SearchProviderResult] = []
    search_leads: list[SearchLead] = []
    promoted_leads: list[SearchLead] = []
    rejected_leads: list[SearchLead] = []
    if fixture:
        (
            profile,
            raw_listings,
            evidences,
            warnings,
            search_provider_results,
            search_leads,
            promoted_leads,
            rejected_leads,
        ) = collect_fixture_search_inputs(limit=limit, days=days, sources=sources, providers=providers)
    else:
        request = SearchRequest(
            city=city,
            office_anchor=office_anchor,
            budget_min=budget_min,
            budget_max=budget_max,
            days=days,
            limit=limit,
            sources=sources or ["beike_lianjia", "fang", "wellcee"],
            providers=providers or ["auto"],
        )
        profile = load_profile()
        if profile and not any([office_anchor, city, budget_min, budget_max]):
            request = request_from_profile(profile, limit=limit, days=days, sources=sources, providers=providers)
        else:
            if not request.office_anchor or not request.city:
                raise SystemExit("live search 需要 --office-anchor 和 --city，或先运行 profile init。")
            profile = profile_from_request(request)
        plan = build_search_plan(request, profile)
        (
            raw_listings,
            evidences,
            warnings,
            source_fetches,
            search_provider_results,
            search_leads,
            promoted_leads,
            rejected_leads,
        ) = collect_live_search_inputs(
            plan=plan,
            runtime_websearch_json=runtime_websearch_json,
            runtime_query=runtime_query,
            provider_fallback=provider_fallback,
        )
        if not raw_listings:
            warnings.append("live search did not produce shortlist candidates; see source coverage and blocking warnings.")
    profile_to_search_plan(profile)
    accepted, rejected = normalize_listings(raw_listings, profile)
    warnings.extend(f"rejected {item.source_id}:{item.item_id} due to {', '.join(item.risk_flags)}" for item in rejected)
    clusters = dedupe_listings(accepted)
    scored = score_clusters(clusters, profile)
    ranked = rerank_clusters(scored, limit=limit)
    reports_dir = Path(output_dir).expanduser() if output_dir else paths.reports_dir
    basename = "last7days-rent-fixture" if fixture else "last7days-rent-live"
    html = render_html_report(
        profile,
        ranked,
        evidences,
        warnings,
        live=not fixture,
        source_fetches=source_fetches,
        search_provider_results=search_provider_results,
        search_leads=search_leads,
        promoted_leads=promoted_leads,
        rejected_leads=rejected_leads,
    )
    evidence = render_evidence_package(
        profile,
        ranked,
        evidences,
        warnings,
        live=not fixture,
        source_fetches=source_fetches,
        search_provider_results=search_provider_results,
        search_leads=search_leads,
        promoted_leads=promoted_leads,
        rejected_leads=rejected_leads,
    )
    html_path, evidence_path = write_outputs(reports_dir, basename, html, evidence)
    chat_summary = render_chat_shortlist(profile, ranked)
    return SearchResult(
        chat_summary,
        html_path,
        evidence_path,
        html,
        evidence,
        source_fetches,
        search_provider_results,
        search_leads,
        promoted_leads,
        rejected_leads,
    )
