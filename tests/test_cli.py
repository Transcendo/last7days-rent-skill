import json
import os
import subprocess
import sys
from pathlib import Path


CLI = Path("skills/last7days-rent/scripts/last7days_rent.py")


def run_cli(args, tmp_path):
    env = os.environ.copy()
    env["LAST7DAYS_RENT_HOME"] = str(tmp_path)
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, env=env)


def test_help_smoke_is_runtime_first(tmp_path):
    result = run_cli(["--help"], tmp_path)
    assert result.returncode == 0
    assert "profile" in result.stdout
    assert "plan" in result.stdout
    assert "ingest" in result.stdout


def test_profile_show_missing_is_nonzero_but_redacted_safe(tmp_path):
    result = run_cli(["profile", "show", "--redacted"], tmp_path)
    assert result.returncode == 1
    assert "尚未找到本地 profile" in result.stderr


def test_profile_wizard_plan_ingest_render_cli_flow(tmp_path):
    assert run_cli(["profile", "wizard", "start", "--goal-seed", "北京京东总部，二居室，5500以内"], tmp_path).returncode == 0
    assert run_cli(["profile", "wizard", "answer", "--question-id", "office_anchor", "--value", "A"], tmp_path).returncode == 0
    assert run_cli(["profile", "wizard", "answer", "--question-id", "bedroom_scope", "--value", "two_bedroom"], tmp_path).returncode == 0
    assert run_cli(["profile", "wizard", "answer", "--question-id", "budget_strategy", "--value", "strict_target"], tmp_path).returncode == 0
    assert run_cli(["profile", "wizard", "answer", "--question-id", "commute_strategy", "--value", "near_first"], tmp_path).returncode == 0
    assert run_cli(["profile", "wizard", "answer", "--question-id", "source_strategy", "--value", "public_all_channels"], tmp_path).returncode == 0
    assert run_cli(["profile", "wizard", "answer", "--question-id", "risk_filter", "--value", "collect_then_user_screen"], tmp_path).returncode == 0
    commit = run_cli(["profile", "wizard", "commit"], tmp_path)
    assert commit.returncode == 0, commit.stderr
    assert (tmp_path / "profile.json").exists()

    plan = run_cli(["plan"], tmp_path)
    assert plan.returncode == 0, plan.stderr
    brief = json.loads(plan.stdout)
    first_batch_queries = " ".join(query["query"] for query in brief["search_batches"][0]["queries"])
    assert "二居室" in first_batch_queries
    assert "5500" in first_batch_queries
    assert brief["collection_rules"]["l0_policy"] == "lead_pool_only"
    assert brief["run_budget"]["max_detail_pages_total"] == 48

    evidence_path = Path("tests/fixtures/evidence/jd_hq_runtime_evidence.json")
    validate = run_cli(["ingest", "--evidence", str(evidence_path), "--validate"], tmp_path)
    assert validate.returncode == 0, validate.stderr
    ingest = run_cli(["ingest", "--evidence", str(evidence_path)], tmp_path)
    assert ingest.returncode == 0, ingest.stderr
    render = run_cli(["render"], tmp_path)
    assert render.returncode == 0, render.stderr
    assert (tmp_path / "reports" / "jd-hq-beijing-rentals.html").exists()
    latest = run_cli(["report", "--latest"], tmp_path)
    assert latest.returncode == 0, latest.stderr
    assert latest.stdout.strip().endswith(".html")


def test_profile_wizard_start_go_on_can_skip_to_commit(tmp_path):
    result = run_cli(
        [
            "profile",
            "wizard",
            "start",
            "--goal-seed",
            "好的，我在北京京东总部、5000RMB，二居室，通勤越近越好，骑电车通勤是最好的 go on",
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready_to_commit"
    assert payload["current_step"] == "done"
    assert payload["next"] == "profile wizard commit"
    assert payload["answered_question_ids"] == [
        "office_anchor",
        "bedroom_scope",
        "budget_strategy",
        "commute_strategy",
        "source_strategy",
        "risk_filter",
    ]


def test_search_is_deprecated_without_legacy_flags(tmp_path):
    result = run_cli(["search"], tmp_path)
    assert result.returncode == 2
    assert "runtime search" in result.stderr


def test_user_errors_do_not_print_tracebacks(tmp_path):
    missing_wizard = run_cli(["profile", "wizard", "next"], tmp_path)
    assert missing_wizard.returncode == 1
    assert "尚未开始 profile wizard" in missing_wizard.stderr
    assert "Traceback" not in missing_wizard.stderr

    assert run_cli(["profile", "wizard", "start"], tmp_path).returncode == 0
    invalid_answer = run_cli(["profile", "wizard", "answer", "--question-id", "office_anchor", "--value", "Z"], tmp_path)
    assert invalid_answer.returncode == 1
    assert "无效答案" in invalid_answer.stderr
    assert "Traceback" not in invalid_answer.stderr
