from __future__ import annotations

from .schema import RentProfile


FIRST_QUESTION = "你的公司、办公点或园区在哪里？请先给出办公点锚点，再由系统推导城市和通勤圈。"


def create_empty_profile() -> RentProfile:
    profile = RentProfile.default()
    profile.open_questions = [FIRST_QUESTION]
    return profile
