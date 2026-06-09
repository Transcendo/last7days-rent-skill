from __future__ import annotations

from pathlib import Path

from ..schema import ListingItem, VerificationEvidence
from .beike_lianjia import parse_beike_lianjia_html
from .fang import parse_fang_html
from .official_verifier import parse_official_verifier_text
from .registry import is_enabled_p0_source
from .wellcee import parse_wellcee_jsonld


def parse_source_fixture(source_id: str, text: str) -> tuple[list[ListingItem], list[VerificationEvidence], list[str]]:
    warnings: list[str] = []
    if source_id != "official_verifier" and not is_enabled_p0_source(source_id):
        return [], [], [f"{source_id} is not an enabled P0 listing source"]
    try:
        if source_id == "beike_lianjia":
            return parse_beike_lianjia_html(text), [], warnings
        if source_id == "wellcee":
            return parse_wellcee_jsonld(text), [], warnings
        if source_id == "fang":
            return parse_fang_html(text), [], warnings
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
