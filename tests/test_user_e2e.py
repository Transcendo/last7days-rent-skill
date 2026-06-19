import json
import os
import subprocess
import sys
from pathlib import Path


CLI = Path("skills/last7days-rent/scripts/last7days_rent.py")


def run_cli(args, state_dir):
    env = os.environ.copy()
    env["LAST7DAYS_RENT_HOME"] = str(state_dir)
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, env=env)


def test_user_can_complete_runtime_first_poc_flow(tmp_path):
    state_dir = tmp_path / "last7days-home"

    start = run_cli(["profile", "wizard", "start", "--goal-seed", "北京京东总部，二居室，5500以内"], state_dir)
    assert start.returncode == 0, start.stderr

    answers = [
        ("office_anchor", "A"),
        ("bedroom_scope", "two_bedroom"),
        ("budget_strategy", "strict_target"),
        ("commute_strategy", "near_first"),
        ("source_strategy", "public_all_channels"),
        ("risk_filter", "collect_then_user_screen"),
    ]
    for question_id, value in answers:
        result = run_cli(["profile", "wizard", "answer", "--question-id", question_id, "--value", value], state_dir)
        assert result.returncode == 0, result.stderr
        assert "{" not in result.stdout

    inspect_json = run_cli(["profile", "wizard", "inspect", "--format", "json"], state_dir)
    assert inspect_json.returncode == 0, inspect_json.stderr
    assert json.loads(inspect_json.stdout)["draft_profile"]["housing_constraints"]["preferred_bedrooms"] == 2

    commit = run_cli(["profile", "wizard", "commit"], state_dir)
    assert commit.returncode == 0, commit.stderr
    assert (state_dir / "profile.json").exists()
    assert (state_dir / "profiles" / "jd-hq-beijing.profile.json").exists()

    prepare = run_cli(["refresh", "--prepare"], state_dir)
    assert prepare.returncode == 0, prepare.stderr
    brief_file = next((state_dir / "refresh").glob("*.search-brief.json"))
    brief = json.loads(brief_file.read_text(encoding="utf-8"))
    assert brief["profile_summary"]["budget_max"] == 5500
    assert brief["profile_summary"]["bedroom_label"] == "二居室"
    assert brief["refresh_meta"]["brief_path"] == str(brief_file)
    assert "attempted_queries" in brief["runtime_audit_required_fields"]

    evidence = Path("tests/fixtures/evidence/jd_hq_runtime_evidence.json")
    refresh = run_cli(["refresh", "--evidence", str(evidence)], state_dir)
    assert refresh.returncode == 0, refresh.stderr
    refresh_result = json.loads(refresh.stdout)
    assert "audit_warnings" in refresh_result
    assert refresh_result["coverage_summary"]["planned"] >= 10
    pool_path = Path(refresh_result["pool"])
    assert pool_path.exists()
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    assert pool["listings"]
    assert any(item["trust_level"] == "L2" for item in pool["listings"])
    assert pool["source_coverage"]["sources"]["wellcee"]["status"] == "not_attempted"

    html_path = Path(refresh_result["report"])
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "京东总部" in html
    assert "次渠锦园" in html
    assert "渠道覆盖" in html
    assert "避坑指南" in html
    assert "下一步策略" in html
    assert "风险指南" in html
