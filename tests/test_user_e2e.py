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

    brief_file = state_dir / "brief.json"
    plan = run_cli(["plan", "--output", str(brief_file)], state_dir)
    assert plan.returncode == 0, plan.stderr
    brief = json.loads(brief_file.read_text(encoding="utf-8"))
    assert brief["profile_summary"]["budget_max"] == 5500
    assert brief["profile_summary"]["bedroom_label"] == "二居室"

    evidence = Path("tests/fixtures/evidence/jd_hq_runtime_evidence.json")
    ingest = run_cli(["ingest", "--evidence", str(evidence)], state_dir)
    assert ingest.returncode == 0, ingest.stderr
    pool_path = state_dir / "pools" / "jd-hq-beijing.listing-pool.json"
    assert pool_path.exists()
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    assert pool["listings"]
    assert any(item["trust_level"] == "L2" for item in pool["listings"])

    render = run_cli(["render"], state_dir)
    assert render.returncode == 0, render.stderr
    html_path = state_dir / "reports" / "jd-hq-beijing-rentals.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "北京京东总部" in html
    assert "次渠锦园" in html
