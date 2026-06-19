import pytest

from lib.profile_wizard import answer_question, commit_wizard, inspect_wizard, next_question, start_wizard


def test_profile_wizard_low_exposure_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    start_wizard(goal_seed="北京租房")

    question = next_question()
    assert question["question_id"] == "office_anchor"
    assert "writes_to" in question

    result = answer_question("office_anchor", "A")
    assert result["message"] == "已确认办公锚点。"
    assert "draft_profile" not in result

    answer_question("bedroom_scope", "two_bedroom")
    answer_question("budget_strategy", "strict_target")
    answer_question("commute_strategy", "near_first")
    answer_question("source_strategy", "public_all_channels")
    answer_question("risk_filter", "collect_then_user_screen")
    state = inspect_wizard()
    assert state["draft_profile"]["housing_constraints"]["preferred_bedrooms"] == 2
    assert state["draft_profile"]["housing_constraints"]["budget_max"] == 5000

    profile = commit_wizard()
    assert profile.profile_meta["schema_version"] == "0.3.0"
    assert profile.wizard_state["current_step"] == "done"
    assert (tmp_path / "profile.json").exists()


def test_profile_wizard_rejects_invalid_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    start_wizard(goal_seed="北京京东总部，一居室，5000以内")
    with pytest.raises(ValueError):
        answer_question("office_anchor", "Z")


def test_profile_wizard_skips_fields_already_present_in_goal_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    start_wizard(goal_seed="北京京东总部，5000RMB，二居室，通勤越近越好，骑电车通勤最好")

    state = inspect_wizard()
    assert state["answered_question_ids"] == [
        "office_anchor",
        "bedroom_scope",
        "budget_strategy",
        "commute_strategy",
    ]
    assert state["current_step"] == "source_strategy"
    assert state["answers"]["bedroom_scope"]["value"] == "two_bedroom"
    assert state["answers"]["budget_strategy"]["value"] == "strict_target"
    assert state["answers"]["commute_strategy"]["value"] == "near_first"
    assert state["draft_profile"]["housing_constraints"]["preferred_bedrooms"] == 2
    assert state["draft_profile"]["housing_constraints"]["budget_max"] == 5000
    assert state["draft_profile"]["commute_preferences"]["strategy"] == "near_first"

    question = next_question()
    assert question["question_id"] == "source_strategy"


def test_profile_wizard_go_on_uses_defaults_when_core_fields_are_complete(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    start_wizard(goal_seed="好的，我在北京京东总部、5000RMB，二居室，通勤越近越好，骑电车通勤是最好的 go on")

    state = inspect_wizard()
    assert state["status"] == "ready_to_commit"
    assert state["current_step"] == "done"
    assert state["answered_question_ids"] == [
        "office_anchor",
        "bedroom_scope",
        "budget_strategy",
        "commute_strategy",
        "source_strategy",
        "risk_filter",
    ]
    assert state["answers"]["source_strategy"]["value"] == "platforms_plus_personal"
    assert state["answers"]["risk_filter"]["value"] == "stable_filter"
    assert next_question()["status"] == "done"
