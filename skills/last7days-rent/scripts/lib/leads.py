from __future__ import annotations

import hashlib
import re
from typing import Any

from .commute_plan import derive_commute_areas
from .schema import CandidateLead, RentProfile, SourceCandidate


ACTIONABLE_SOURCE_IDS = {"beike_lianjia", "wellcee", "fang"}


def build_candidate_leads(
    profile: RentProfile,
    candidates: list[SourceCandidate],
    *,
    limit: int = 10,
) -> list[CandidateLead]:
    scored: list[CandidateLead] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.can_promote or not candidate.source_url:
            continue
        if candidate.source_id not in ACTIONABLE_SOURCE_IDS:
            continue
        if candidate.source_url in seen:
            continue
        lead = _candidate_to_lead(profile, candidate)
        if not lead:
            continue
        seen.add(candidate.source_url)
        scored.append(lead)
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[: max(0, int(limit))]


def summarize_candidate(candidate: SourceCandidate) -> str:
    parts = [str(value) for value in candidate.visible_fields.values() if value]
    if parts:
        return "，".join(parts)
    return (candidate.snippet or "").replace("\n", " ")[:160] or "unknown"


def _candidate_to_lead(profile: RentProfile, candidate: SourceCandidate) -> CandidateLead | None:
    summary = summarize_candidate(candidate)
    if summary == "unknown":
        return None
    fields = candidate.visible_fields or {}
    if not any(fields.get(key) for key in ["price_text", "area_text", "layout_text"]):
        return None

    text = _candidate_text(candidate, summary)
    commute_matches = _commute_matches(profile, text)
    if _requires_commute_match(profile) and not commute_matches:
        return None

    budget_match = _budget_match(profile, fields.get("price_text"))
    if budget_match is False:
        return None
    bedroom_match = _bedroom_match(profile, fields.get("layout_text") or text)
    if bedroom_match is False:
        return None

    score = _score_lead(candidate, fields, commute_matches, budget_match, bedroom_match)
    if score <= 0:
        return None

    return CandidateLead(
        lead_id=_lead_id(candidate),
        source_id=candidate.source_id,
        url=candidate.source_url,
        title=candidate.title or candidate.source_url,
        summary=summary,
        price_text=_str_or_none(fields.get("price_text")),
        area_text=_str_or_none(fields.get("area_text")),
        layout_text=_str_or_none(fields.get("layout_text")),
        freshness_text=_str_or_none(fields.get("freshness_text")),
        commute_matches=commute_matches,
        budget_match=budget_match,
        bedroom_match=bedroom_match,
        score=score,
    )


def _candidate_text(candidate: SourceCandidate, summary: str) -> str:
    return " ".join(
        part
        for part in [
            candidate.title or "",
            candidate.snippet or "",
            candidate.source_url or "",
            summary,
            " ".join(str(value) for value in (candidate.visible_fields or {}).values() if value),
        ]
        if part
    )


def _requires_commute_match(profile: RentProfile) -> bool:
    return bool(profile.commute.get("derived_areas") or profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint"))


def _commute_matches(profile: RentProfile, text: str) -> list[str]:
    terms: list[str] = []
    for term in profile.commute.get("derived_areas") or []:
        if term and term not in terms:
            terms.append(str(term))
    if not terms:
        office = profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint") or ""
        for term in derive_commute_areas(str(office)):
            if term and term not in terms:
                terms.append(str(term))
    for term in [profile.office_anchor.get("office_name"), profile.office_anchor.get("address_hint")]:
        if term and term not in terms:
            terms.append(str(term))
    return [term for term in terms if term and term in text]


def _budget_match(profile: RentProfile, price_text: Any) -> bool | None:
    price = _extract_number(_str_or_none(price_text))
    if price is None:
        return None
    budget_min = profile.housing_constraints.get("budget_min")
    budget_max = profile.housing_constraints.get("budget_max")
    if budget_min is not None and price < float(budget_min):
        return False
    if budget_max is not None and price > float(budget_max):
        return False
    return True


def _bedroom_match(profile: RentProfile, layout_text: Any) -> bool | None:
    min_bedrooms = profile.housing_constraints.get("min_bedrooms")
    if not min_bedrooms:
        return None
    bedrooms = _bedroom_count(_str_or_none(layout_text))
    if bedrooms is None:
        return None
    return bedrooms >= int(min_bedrooms)


def _score_lead(
    candidate: SourceCandidate,
    fields: dict[str, Any],
    commute_matches: list[str],
    budget_match: bool | None,
    bedroom_match: bool | None,
) -> float:
    score = 0.0
    if commute_matches:
        score += 3.0 + min(len(commute_matches), 3) * 0.2
    if budget_match is True:
        score += 3.0
    elif budget_match is None:
        score += 0.4
    if bedroom_match is True:
        score += 2.0
    elif bedroom_match is None:
        score += 0.4
    if fields.get("price_text"):
        score += 1.0
    if fields.get("area_text"):
        score += 0.8
    if fields.get("layout_text"):
        score += 0.8
    if fields.get("freshness_text"):
        score += 1.0
    if candidate.source_id in ACTIONABLE_SOURCE_IDS:
        score += 0.7
    if candidate.position:
        score += max(0.0, 0.5 - (int(candidate.position) - 1) * 0.05)
    return score


def _lead_id(candidate: SourceCandidate) -> str:
    seed = candidate.source_url or candidate.candidate_id
    return "lead-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _extract_number(value: str | None) -> int | None:
    if not value:
        return None
    found = re.search(r"\d{1,6}", value)
    return int(found.group(0)) if found else None


def _bedroom_count(text: str | None) -> int | None:
    if not text:
        return None
    digit = re.search(r"(\d+)\s*(?:室|居室|居)", text)
    if digit:
        return int(digit.group(1))
    if "一居" in text:
        return 1
    if "两居" in text or "二居" in text:
        return 2
    if "三居" in text:
        return 3
    if "四居" in text:
        return 4
    if "开间" in text:
        return 0
    return None


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
