import pytest

from lib.profile_wizard import answer_question, commit_wizard, inspect_wizard, next_question, start_wizard


def test_profile_wizard_low_exposure_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    start_wizard(goal_seed="北京京东总部，二居室，5500以内")

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
    assert state["draft_profile"]["housing_constraints"]["budget_max"] == 5500

    profile = commit_wizard()
    assert profile.profile_meta["schema_version"] == "0.3.0"
    assert profile.wizard_state["current_step"] == "done"
    assert (tmp_path / "profile.json").exists()


def test_profile_wizard_rejects_invalid_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    start_wizard(goal_seed="北京京东总部，一居室，5000以内")
    with pytest.raises(ValueError):
        answer_question("office_anchor", "Z")
