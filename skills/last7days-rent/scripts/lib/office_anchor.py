from __future__ import annotations

from typing import Any


CITY_KEYWORDS = {
    "北京": ["北京", "西二旗", "后厂村", "中关村", "望京"],
    "上海": ["上海", "五角场", "张江", "漕河泾", "陆家嘴"],
    "深圳": ["深圳", "南山", "科技园", "后海", "前海"],
    "杭州": ["杭州", "未来科技城", "西溪", "滨江"],
}


def infer_city(anchor_text: str | None, explicit_city: str | None = None) -> tuple[str | None, float, list[str]]:
    if explicit_city:
        return explicit_city, 1.0, []
    if not anchor_text:
        return None, 0.0, ["请确认公司、办公点或园区，用它推导城市和通勤圈。"]
    for city, keywords in CITY_KEYWORDS.items():
        if any(keyword in anchor_text for keyword in keywords):
            return city, 0.82, []
    return None, 0.25, [f"无法从办公点锚点“{anchor_text}”稳定推导城市，请确认城市和通勤圈。"]


def build_office_anchor(
    company: str | None,
    office_anchor: str | None,
    address_hint: str | None,
    city: str | None,
) -> tuple[dict[str, Any], list[str]]:
    anchor_text = " ".join(part for part in [company, office_anchor, address_hint, city] if part)
    inferred_city, confidence, questions = infer_city(anchor_text, city)
    office = {
        "company": company,
        "office_name": office_anchor,
        "address_hint": address_hint,
        "city": inferred_city,
        "confidence": confidence,
    }
    if not office_anchor and not address_hint:
        questions.insert(0, "请先提供公司、办公点或园区名称；MVP 不能从城市泛搜开始。")
    return office, questions
