from __future__ import annotations

from pathlib import Path

from ..schema import ListingItem, SearchPlan, SearchRequest, SourceFetchResult, VerificationEvidence
from .beike_lianjia import parse_beike_lianjia_html
from .fang import parse_fang_html
from .http import fetch_public_url
from .official_verifier import parse_official_verifier_text
from .query import build_search_plan
from .registry import get_source_meta, is_enabled_p0_source
from .wellcee import parse_wellcee_jsonld


def parse_source_fixture(source_id: str, text: str, base_url: str | None = None) -> tuple[list[ListingItem], list[VerificationEvidence], list[str]]:
    warnings: list[str] = []
    if source_id != "official_verifier" and not is_enabled_p0_source(source_id):
        return [], [], [f"{source_id} is not an enabled P0 listing source"]
    try:
        if source_id == "beike_lianjia":
            return parse_beike_lianjia_html(text, base_url=base_url or "https://sh.zu.ke.com"), [], warnings
        if source_id == "wellcee":
            return parse_wellcee_jsonld(text), [], warnings
        if source_id == "fang":
            return parse_fang_html(text, base_url=base_url or "https://zu.fang.com"), [], warnings
        if source_id == "official_verifier":
            return [], parse_official_verifier_text(text), warnings
    except Exception as exc:  # adapter failures should not block pipeline
        return [], [], [f"{source_id} parse failed: {exc}"]
    return [], [], [f"{source_id} has no parser"]


def load_fixture_sources(fixture_dir: Path) -> tuple[list[ListingItem], list[VerificationEvidence], list[str]]:
    source_files = {
        "beike_lianjia": fixture_dir / "beike_lianjia.html",
        "wellcee": fixture_dir / "wellcee.html",
        "fang": fixture_dir / "fang.html",
        "official_verifier": fixture_dir / "official_verifier.txt",
    }
    listings: list[ListingItem] = []
    evidences: list[VerificationEvidence] = []
    warnings: list[str] = []
    for source_id, path in source_files.items():
        if not path.exists():
            warnings.append(f"missing fixture: {path.name}")
            continue
        parsed, parsed_evidence, parsed_warnings = parse_source_fixture(source_id, path.read_text(encoding="utf-8"))
        listings.extend(parsed)
        evidences.extend(parsed_evidence)
        warnings.extend(parsed_warnings)
    return listings, evidences, warnings


def fetch_live_sources(plan: SearchPlan) -> tuple[list[ListingItem], list[VerificationEvidence], list[str], list[SourceFetchResult]]:
    listings: list[ListingItem] = []
    evidences: list[VerificationEvidence] = []
    warnings: list[str] = []
    fetches: list[SourceFetchResult] = []
    for source_id, queries in plan.source_queries.items():
        meta = get_source_meta(source_id)
        if not meta or not meta.enabled:
            warnings.append(f"{source_id}: disabled or unknown source")
            continue
        if not meta.live_enabled:
            warnings.append(f"{source_id}: live search disabled; {meta.status}")
            continue
        for query in queries:
            url = query["url"]
            text, fetch_result = fetch_public_url(source_id, url)
            fetches.append(fetch_result)
            if fetch_result.status == "blocked" or fetch_result.warning:
                warnings.append(f"{source_id}: {url} -> {fetch_result.warning or fetch_result.status} (HTTP {fetch_result.http_status or 'unknown'})")
            if fetch_result.status != "ok":
                continue
            parsed, parsed_evidences, parsed_warnings = parse_source_fixture(source_id, text, base_url=fetch_result.url)
            limited = parsed[: plan.request.limit]
            fetch_result.candidate_count = len(limited)
            listings.extend(limited)
            evidences.extend(parsed_evidences)
            warnings.extend(f"{source_id}: {warning}" for warning in parsed_warnings)
            if not limited:
                warnings.append(f"{source_id}: empty_parse for {url}")
    return listings, evidences, warnings, fetches


def smoke_source(source_id: str, city: str | None = None, area: str | None = None, limit: int = 5) -> dict:
    request = SearchRequest(city=city or "上海", office_anchor=area or "五角场", limit=limit, sources=[source_id])
    plan = build_search_plan(request)
    listings, evidences, warnings, fetches = fetch_live_sources(plan)
    return {
        "source_id": source_id,
        "request": request.to_dict(),
        "fetches": [fetch.to_dict() for fetch in fetches],
        "candidate_count": len(listings),
        "evidence_count": len(evidences),
        "has_actionable_contact": any(item.contact_methods for item in listings),
        "warnings": warnings,
    }
