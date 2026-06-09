from __future__ import annotations

from .commute_plan import derive_commute_areas, profile_to_search_plan
from .env import ensure_local_dirs, get_paths
from .office_anchor import build_office_anchor
from .preference_questions import apply_decision
from .privacy import redact_profile
from .schema import RentProfile, now_iso
from .store import read_json, write_json, write_text


def save_profile(profile: RentProfile) -> RentProfile:
    paths = ensure_local_dirs()
    profile.profile_meta["updated_at"] = now_iso()
    write_json(paths.profile_json, profile.to_dict())
    write_text(paths.profile_md, profile_to_markdown(profile, redacted=True))
    return profile


def load_profile() -> RentProfile | None:
    data = read_json(get_paths().profile_json)
    if not data:
        return None
    return RentProfile.from_dict(data)


def init_profile(
    company: str | None = None,
    office_anchor: str | None = None,
    address_hint: str | None = None,
    city: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    commute_minutes: int = 35,
    rental_mode: str = "either",
) -> RentProfile:
    profile = RentProfile.default()
    office, questions = build_office_anchor(company, office_anchor, address_hint, city)
    profile.office_anchor.update(office)
    profile.commute["max_minutes"] = commute_minutes
    profile.commute["derived_areas"] = derive_commute_areas(office_anchor or address_hint)
    profile.housing_constraints.update(
        {
            "budget_min": budget_min,
            "budget_max": budget_max,
            "rental_mode": rental_mode,
        }
    )
    profile.open_questions = questions
    profile.provenance["profile_first_question"] = "company_or_office_anchor"
    return save_profile(profile)


def refine_profile(decision: str | None, weight: float | None = None) -> RentProfile:
    profile = load_profile() or RentProfile.default()
    profile = apply_decision(profile, decision, weight)
    return save_profile(profile)


def profile_to_markdown(profile: RentProfile, redacted: bool = True) -> str:
    data = redact_profile(profile.to_dict()) if redacted else profile.to_dict()
    plan = profile_to_search_plan(profile)
    lines = [
        "# last7days-rent Profile",
        "",
        "last7days = 帮助用户 7 天完成租房",
        "",
        "## 脱敏摘要" if redacted else "## Profile",
        "",
        f"- 办公点: {data['office_anchor'].get('office_name') or 'unknown'}",
        f"- 城市: {data['office_anchor'].get('city') or 'unknown'}",
        f"- 通勤上限: {data['commute'].get('max_minutes', 'unknown')} 分钟",
        f"- 预算: {data['housing_constraints'].get('budget_min') or 'unknown'} - {data['housing_constraints'].get('budget_max') or 'unknown'}",
        f"- 租住方式: {data['housing_constraints'].get('rental_mode') or 'unknown'}",
        "",
        "## Search Plan",
        "",
        f"- 通勤圈: {', '.join(plan['commute_areas']) if plan['commute_areas'] else 'unknown'}",
        f"- P0 来源优先级: {', '.join(plan['source_priority'])}",
        f"- 需要追问: {', '.join(plan['open_questions']) if plan['open_questions'] else '无'}",
    ]
    return "\n".join(lines) + "\n"
