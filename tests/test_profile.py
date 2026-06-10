from lib.commute_plan import profile_to_search_plan
from lib.env import DEFAULT_STATE_DIR, get_state_dir
from lib.office_anchor import build_office_anchor
from lib.profile_store import init_profile, load_profile


def test_office_anchor_infers_city_and_questions():
    office, questions = build_office_anchor("示例公司", "上海五角场", None, None)
    assert office["city"] == "上海"
    assert questions == []


def test_uncertain_office_anchor_writes_open_question():
    office, questions = build_office_anchor(None, "未知园区", None, None)
    assert office["city"] is None
    assert questions


def test_profile_init_uses_local_home(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    profile = init_profile(office_anchor="上海五角场", budget_max=5200)
    loaded = load_profile()
    assert loaded is not None
    assert profile.office_anchor["city"] == "上海"
    assert (tmp_path / "profile.json").exists()
    plan = profile_to_search_plan(profile)
    assert "五角场" in plan["commute_areas"]


def test_default_state_dir_is_last7days_named(monkeypatch):
    monkeypatch.delenv("LAST7DAYS_RENT_HOME", raising=False)

    assert DEFAULT_STATE_DIR.name == ".last7days-rent"
    assert get_state_dir() == DEFAULT_STATE_DIR


def test_state_dir_override_uses_last7days_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))

    assert get_state_dir() == tmp_path
