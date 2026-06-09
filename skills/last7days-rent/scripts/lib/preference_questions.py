from __future__ import annotations

from .schema import RentProfile


DECISION_WEIGHTS = {
    "commute": {"commute": 0.38, "budget": 0.2, "trust": 0.18, "freshness": 0.14, "preference": 0.1},
    "trust": {"commute": 0.24, "budget": 0.18, "trust": 0.32, "freshness": 0.12, "preference": 0.14},
    "brand": {"commute": 0.25, "budget": 0.2, "trust": 0.24, "freshness": 0.12, "preference": 0.19},
    "speed": {"commute": 0.25, "budget": 0.2, "trust": 0.18, "freshness": 0.25, "preference": 0.12},
    "quiet": {"commute": 0.25, "budget": 0.2, "trust": 0.2, "freshness": 0.1, "preference": 0.25},
}


QUESTIONS = [
    {"id": "commute", "tradeoff": "通勤 vs 空间", "left": "更短通勤", "right": "更大空间"},
    {"id": "trust", "tradeoff": "可信来源 vs 低价线索", "left": "可信优先", "right": "低价优先"},
    {"id": "brand", "tradeoff": "品牌公寓 vs 个人转租", "left": "品牌公寓", "right": "个人转租"},
    {"id": "speed", "tradeoff": "速度 vs 尽调", "left": "快速决策", "right": "充分尽调"},
    {"id": "quiet", "tradeoff": "安静安全 vs 生活便利", "left": "安静安全", "right": "生活便利"},
]


def apply_decision(profile: RentProfile, decision: str | None, weight: float | None = None) -> RentProfile:
    if not decision:
        return profile
    selected = DECISION_WEIGHTS.get(decision)
    if selected:
        profile.scoring_weights.update(selected)
    if weight is not None:
        profile.decision_preferences[decision] = weight
    else:
        profile.decision_preferences[decision] = "selected"
    return profile
