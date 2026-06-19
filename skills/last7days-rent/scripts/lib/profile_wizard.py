from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .env import ensure_local_dirs, get_paths
from .profile_store import save_profile
from .schema import RentProfile, now_iso
from .store import read_json, write_json


DEFAULT_ANCHOR_SCENARIO = "beijing_jd_hq_anchor_example"
WIZARD_SCHEMA_VERSION = "0.3.0"


@dataclass(frozen=True)
class WizardQuestion:
    question_id: str
    title: str
    body: str
    options: list[dict[str, Any]]
    writes_to: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "title": self.title,
            "body": self.body,
            "type": "single_choice",
            "options": self.options,
            "writes_to": self.writes_to,
        }


QUESTIONS: list[WizardQuestion] = [
    WizardQuestion(
        question_id="office_anchor",
        title="确认办公锚点",
        body="你说的北京京东总部，我先理解为亦庄经海路附近的京东总部办公区。",
        writes_to=["office_anchor", "commute_preferences.derived_zones_priority"],
        options=[
            {
                "value": "jd_hq_jinghailu",
                "label": "京东总部 / 亦庄经海路",
                "description": "优先覆盖经海路、锋创科技园、次渠南、次渠嘉园、次渠锦园。",
                "recommended": True,
            },
            {"value": "jd_other_yizhuang", "label": "京东亦庄其他办公点", "description": "先追问更具体楼宇或地铁站。"},
            {"value": "unknown", "label": "我不确定", "description": "先核对办公锚点，再继续确认通勤圈。"},
        ],
    ),
    WizardQuestion(
        question_id="bedroom_scope",
        title="确认户型硬约束",
        body="请确认你要看的户型范围。",
        writes_to=["housing_constraints.preferred_bedrooms", "housing_constraints.min_bedrooms", "housing_constraints.allow_shared"],
        options=[
            {"value": "one_bedroom", "label": "正规一居 / 一室一厅", "description": "优先整租正规一居，默认排除合租。", "recommended": True},
            {"value": "two_bedroom", "label": "二居室", "description": "优先整租二居，候选会更少，可能需要扩圈。"},
            {"value": "independent_any", "label": "独立整租即可", "description": "预算和通勤优先，户型不做强限制。"},
            {"value": "shared_ok", "label": "可以接受合租主卧", "description": "合租会单独标风险。"},
        ],
    ),
    WizardQuestion(
        question_id="budget_strategy",
        title="确认预算策略",
        body="请确认预算是硬上限，还是允许少量超预算作为备选。",
        writes_to=["housing_constraints.budget_target", "housing_constraints.budget_max", "housing_constraints.over_budget_policy"],
        options=[
            {"value": "strict_target", "label": "严格按目标预算以内", "description": "候选少时优先扩圈，不自动超预算。", "recommended": True},
            {"value": "backup_5500", "label": "目标 5000，最高可到 5500", "description": "5001-5500 作为超预算备选。"},
            {"value": "backup_6000", "label": "目标 5000，最高可到 6000", "description": "更容易找到正规房源，但会明显标注超预算。"},
        ],
    ),
    WizardQuestion(
        question_id="commute_strategy",
        title="确认通勤策略",
        body="以经海路为锚点，请选择通勤和房源数量之间的取舍。",
        writes_to=["commute_preferences.strategy", "commute_preferences.max_minutes", "commute_preferences.expand_zones_if_sparse"],
        options=[
            {"value": "balanced", "label": "均衡通勤", "description": "优先 35-45 分钟内，候选数量更稳。", "recommended": True},
            {"value": "near_first", "label": "尽量近", "description": "优先 30 分钟内，候选可能较少。"},
            {"value": "budget_first", "label": "尽量便宜", "description": "可接受 45-60 分钟，扩大到外围片区。"},
            {"value": "metro_only", "label": "只看地铁通勤", "description": "优先地铁和步行组合。"},
        ],
    ),
    WizardQuestion(
        question_id="source_strategy",
        title="确认房源来源偏好",
        body="请确认公开来源要覆盖到什么程度。",
        writes_to=["risk_preferences.source_strategy", "risk_preferences.preferred_sources"],
        options=[
            {"value": "platforms_plus_personal", "label": "平台优先，个人转租补充", "description": "优先平台，个人转租只做补充。", "recommended": True},
            {"value": "public_all_channels", "label": "全渠道都要", "description": "平台、豆瓣转租、Wellcee 和品牌公寓都纳入，统一标风险。"},
            {"value": "platform_only", "label": "只看平台房源", "description": "更稳，但可能错过低价线索。"},
            {"value": "personal_first", "label": "优先个人直租/转租", "description": "可能更便宜，但核验成本更高。"},
        ],
    ),
    WizardQuestion(
        question_id="risk_filter",
        title="确认风险过滤强度",
        body="全渠道会带来更多候选，也会带来更多噪音。",
        writes_to=["risk_preferences.risk_filter"],
        options=[
            {"value": "stable_filter", "label": "稳妥过滤", "description": "明显异常线索先排除。", "recommended": True},
            {"value": "collect_then_user_screen", "label": "先都收进来，再由我筛", "description": "尽量保留候选，风险标签更醒目。"},
            {"value": "contactable_first", "label": "只要能联系就先保留", "description": "更激进，适合快速扫盘。"},
        ],
    ),
]


def wizard_state_path():
    return get_paths().state_dir / "profile_wizard.json"


def start_wizard(scenario: str = DEFAULT_ANCHOR_SCENARIO, goal_seed: str | None = None) -> dict[str, Any]:
    ensure_local_dirs()
    goal_seed = goal_seed or "北京京东总部亦庄经海路，一居室，预算 6000 RMB 以内，通勤 45 分钟内"
    draft = _default_profile(scenario, goal_seed)
    state = {
        "schema_version": WIZARD_SCHEMA_VERSION,
        "scenario": scenario,
        "goal_seed": goal_seed,
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "answered_question_ids": [],
        "answers": {},
        "draft_profile": draft,
        "current_step": "office_anchor",
        "status": "in_progress",
    }
    write_json(wizard_state_path(), state)
    return state


def load_wizard_state() -> dict[str, Any]:
    state = read_json(wizard_state_path())
    if not state:
        raise ValueError("尚未开始 profile wizard，请先运行 profile wizard start。")
    return state


def next_question() -> dict[str, Any]:
    state = load_wizard_state()
    answered = set(state.get("answered_question_ids", []))
    for question in QUESTIONS:
        if question.question_id not in answered:
            state["current_step"] = question.question_id
            state["updated_at"] = now_iso()
            write_json(wizard_state_path(), state)
            return question.to_dict()
    state["current_step"] = "done"
    state["status"] = "ready_to_commit"
    state["updated_at"] = now_iso()
    write_json(wizard_state_path(), state)
    return {"status": "done", "message": "profile 已确认，可以 commit。"}


def answer_question(question_id: str, value: str, answer_note: str | None = None) -> dict[str, Any]:
    state = load_wizard_state()
    question = _question_by_id(question_id)
    value = _normalize_answer_value(question, value)
    draft = state["draft_profile"]
    _apply_answer(draft, question_id, value)
    answered = list(state.get("answered_question_ids", []))
    if question_id not in answered:
        answered.append(question_id)
    state["answered_question_ids"] = answered
    state.setdefault("answers", {})[question_id] = {"value": value, "answer_note": answer_note}
    state["updated_at"] = now_iso()
    state["current_step"] = "done" if len(answered) >= len(QUESTIONS) else next(q.question_id for q in QUESTIONS if q.question_id not in answered)
    write_json(wizard_state_path(), state)
    return {
        "question_id": question_id,
        "value": value,
        "message": _confirmation(question_id, value),
        "next_question": None if state["current_step"] == "done" else state["current_step"],
    }


def inspect_wizard() -> dict[str, Any]:
    return load_wizard_state()


def commit_wizard() -> RentProfile:
    state = load_wizard_state()
    draft = state["draft_profile"]
    draft.setdefault("profile_meta", {})["status"] = "confirmed"
    draft.setdefault("profile_meta", {})["updated_at"] = now_iso()
    draft["wizard_state"] = {
        "current_step": "done",
        "answered_question_ids": state.get("answered_question_ids", []),
        "confirmed_fields": _confirmed_fields(state.get("answered_question_ids", [])),
        "open_questions": [],
    }
    profile = RentProfile.from_dict(draft)
    save_profile(profile)
    profile_path = get_paths().profiles_dir / "jd-hq-beijing.profile.json"
    write_json(profile_path, profile.to_dict())
    state["status"] = "committed"
    state["committed_profile_path"] = str(profile_path)
    state["updated_at"] = now_iso()
    write_json(wizard_state_path(), state)
    return profile


def _default_profile(scenario: str, goal_seed: str) -> dict[str, Any]:
    parsed = _parse_goal_seed(goal_seed)
    budget_target = parsed.get("budget_max") or 5000
    bedrooms = parsed.get("bedrooms") or 1
    return {
        "profile_meta": {"schema_version": WIZARD_SCHEMA_VERSION, "created_at": now_iso(), "updated_at": now_iso(), "status": "draft"},
        "privacy": {"storage": "local_private", "redact_public_output": True},
        "user_goal": {"target_days": 7, "scenario": scenario, "goal_seed": goal_seed},
        "office_anchor": {
            "company": "京东",
            "campus_name": "京东总部",
            "office_name": "京东总部",
            "city": "北京",
            "anchor_id": "beijing-jd-hq-yizhuang",
            "nearest_metro": ["经海路"],
            "confidence": "agent_prefilled",
        },
        "commute": {"max_minutes": 35, "preferred_transit": ["walk", "bike", "metro"], "derived_areas": ["经海路", "锋创科技园", "次渠南", "次渠嘉园", "次渠锦园"]},
        "commute_preferences": {
            "strategy": "balanced",
            "max_minutes": 35,
            "preferred_modes": ["walk", "bike", "metro"],
            "derived_zones_priority": ["经海路", "锋创科技园", "次渠南", "次渠嘉园", "次渠锦园"],
            "expand_zones_if_sparse": ["次渠", "亦庄文化园", "荣京东街", "马驹桥"],
        },
        "housing_constraints": {
            "budget_target": budget_target,
            "budget_max": budget_target,
            "budget_hard_max": budget_target,
            "rental_mode": "whole",
            "preferred_bedrooms": bedrooms,
            "min_bedrooms": bedrooms,
            "allow_studio": False,
            "allow_shared": False,
            "over_budget_policy": "strict",
        },
        "risk_preferences": {
            "source_strategy": "platforms_plus_personal",
            "preferred_sources": ["ke", "lianjia", "ziroom", "5i5j", "58", "anjuke", "douban", "public_web"],
            "allow_personal_transfer": True,
            "allow_direct_landlord": True,
            "risk_filter": "stable_filter",
            "require_contact_path": True,
        },
        "source_preferences": {"preferred_sources": ["58", "安居客", "贝壳", "链家", "自如", "我爱我家", "豆瓣公开小组"]},
        "open_questions": [],
        "provenance": {"created_by": "profile_wizard", "profile_first_question": "office_anchor"},
    }


def _parse_goal_seed(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    if any(token in text for token in ["二居", "两居", "2居", "2室"]):
        parsed["bedrooms"] = 2
    elif any(token in text for token in ["一居", "1居", "1室"]):
        parsed["bedrooms"] = 1
    budget = re.search(r"(\d{4,5})\s*(?:rmb|RMB|元)?\s*(?:以内|以下|内)?", text)
    if budget:
        parsed["budget_max"] = int(budget.group(1))
    return parsed


def _question_by_id(question_id: str) -> WizardQuestion:
    for question in QUESTIONS:
        if question.question_id == question_id:
            return question
    raise ValueError(f"未知问题: {question_id}")


def _normalize_answer_value(question: WizardQuestion, value: str) -> str:
    value = value.strip()
    if len(value) == 1 and value.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        idx = ord(value.upper()) - ord("A")
        if 0 <= idx < len(question.options):
            return str(question.options[idx]["value"])
    option_values = {str(option["value"]) for option in question.options}
    if value not in option_values:
        raise ValueError(f"无效答案: {value}")
    return value


def _apply_answer(draft: dict[str, Any], question_id: str, value: str) -> None:
    if question_id == "office_anchor":
        if value == "jd_hq_jinghailu":
            draft["office_anchor"].update({"confidence": "user_confirmed", "anchor_id": "beijing-jd-hq-yizhuang"})
        elif value == "unknown":
            draft["office_anchor"]["confidence"] = "needs_confirmation"
            draft["open_questions"] = ["请确认北京京东总部对应的具体办公楼或地铁站。"]
        else:
            draft["office_anchor"]["confidence"] = "needs_specific_building"
            draft["open_questions"] = ["请补充京东亦庄办公点的具体楼宇或最近地铁站。"]
    elif question_id == "bedroom_scope":
        if value == "two_bedroom":
            bedrooms, allow_shared, allow_studio = 2, False, False
        elif value == "independent_any":
            bedrooms, allow_shared, allow_studio = None, False, True
        elif value == "shared_ok":
            bedrooms, allow_shared, allow_studio = 1, True, False
        else:
            bedrooms, allow_shared, allow_studio = 1, False, False
        draft["housing_constraints"].update({"preferred_bedrooms": bedrooms, "min_bedrooms": bedrooms, "allow_shared": allow_shared, "allow_studio": allow_studio})
    elif question_id == "budget_strategy":
        target = int(draft["housing_constraints"].get("budget_target") or draft["housing_constraints"].get("budget_max") or 5000)
        if value == "backup_5500":
            max_budget = max(target, 5500)
            policy = "allow_backup"
        elif value == "backup_6000":
            max_budget = max(target, 6000)
            policy = "allow_backup"
        else:
            max_budget = target
            policy = "strict"
        draft["housing_constraints"].update({"budget_target": target, "budget_max": max_budget, "budget_hard_max": max_budget, "over_budget_policy": policy})
    elif question_id == "commute_strategy":
        minutes = {"near_first": 30, "balanced": 40, "budget_first": 60, "metro_only": 45}[value]
        draft["commute_preferences"].update({"strategy": value, "max_minutes": minutes})
        draft["commute"].update({"max_minutes": minutes})
    elif question_id == "source_strategy":
        preferred = {
            "platform_only": ["ke", "lianjia", "ziroom", "5i5j", "58", "anjuke"],
            "personal_first": ["douban", "public_web", "58", "anjuke", "ke", "lianjia"],
            "public_all_channels": ["ke", "lianjia", "ziroom", "5i5j", "58", "anjuke", "douban", "xiaohongshu", "wechat_public", "public_web"],
            "platforms_plus_personal": ["ke", "lianjia", "ziroom", "5i5j", "58", "anjuke", "douban", "public_web"],
        }[value]
        draft["risk_preferences"].update({"source_strategy": value, "preferred_sources": preferred, "allow_personal_transfer": value != "platform_only"})
    elif question_id == "risk_filter":
        draft["risk_preferences"]["risk_filter"] = value


def _confirmation(question_id: str, value: str) -> str:
    labels = {
        "office_anchor": "已确认办公锚点。",
        "bedroom_scope": "已确认户型范围。",
        "budget_strategy": "已确认预算策略。",
        "commute_strategy": "已确认通勤策略。",
        "source_strategy": "已确认来源偏好。",
        "risk_filter": "已确认风险过滤强度。",
    }
    return labels.get(question_id, "已记录。")


def _confirmed_fields(answered: list[str]) -> list[str]:
    fields: list[str] = []
    for question_id in answered:
        fields.extend(_question_by_id(question_id).writes_to)
    return fields
