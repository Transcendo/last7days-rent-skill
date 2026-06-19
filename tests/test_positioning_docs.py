import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "last7days-rent" / "scripts" / "last7days_rent.py"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_skill_self_intro_contract_is_bigtech_office_anchor_first():
    skill = read_text("skills/last7days-rent/SKILL.md")
    assert "用户问“你能干什么”时" in skill
    assert "用户问“怎么使用”时" in skill
    assert "我帮一线/新一线互联网公司同学围绕办公点找房" in skill
    assert "你在哪个城市、哪个公司/办公点上班" in skill
    assert "不要在默认示例" not in skill
    assert "公司附近，一居室" not in skill


def test_readme_and_user_guide_are_runtime_first_not_legacy_search_first():
    readme = read_text("README.md")
    guide = read_text("docs/user-guide.md")
    joined = readme + "\n" + guide
    assert "一线/新一线互联网大厂" in joined
    assert "北京京东总部亦庄经海路" in joined
    assert "profile wizard -> plan -> runtime web search/browser -> ingest -> render -> report" in joined
    assert "search --days" not in guide
    assert "search --fixture" not in guide
    assert "profile init" not in guide


def test_cli_help_uses_concrete_office_anchor_goal_seed(tmp_path):
    env = os.environ.copy()
    env["LAST7DAYS_RENT_HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(CLI), "profile", "wizard", "start", "--help"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0
    assert "北京京东总部亦庄经海路" in result.stdout
    assert "公司附近" not in result.stdout
