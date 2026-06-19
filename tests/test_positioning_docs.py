import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "last7days-rent" / "scripts" / "last7days_rent.py"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_skill_self_intro_contract_is_bigtech_rent_refresh_first():
    skill = read_text("skills/last7days-rent/SKILL.md")
    assert "用户问“你能干什么”时" in skill
    assert "用户问“怎么使用”时" in skill
    assert "7 天快速租房" in skill
    assert "本地化收集用户租房需求，生成专属租房 profile" in skill
    assert "基于 profile 进行全渠道搜索适配和房源信息聚合" in skill
    assert "生成专属个人租房 HTML 候选池" in skill
    assert "基于本地最新 profile 持续更新全渠道房源信息" in skill
    assert "你在哪个城市、哪个公司/办公点上班" in skill
    assert "不要为了走完流程重复询问用户已经在自然语言里明确给出的字段" in skill
    assert "go on / 继续 / 直接开始 / 帮我跑" in skill
    assert "Runtime source audit 契约" in skill
    assert "source_attempts" in skill
    assert "https://nest-hub.eggcampus.com/" in skill
    assert "4 个 tab" in skill
    assert "不要在默认示例" not in skill
    assert "公司附近，一居室" not in skill


def test_readme_and_user_guide_are_runtime_first_not_legacy_search_first():
    readme = read_text("README.md")
    guide = read_text("docs/user-guide.md")
    joined = readme + "\n" + guide
    assert "一线/新一线城市互联网大厂" in joined
    assert "7 天快速租房" in joined
    assert "本地化收集用户租房需求" in joined
    assert "生成专属个人租房 HTML" in joined
    assert "北京京东总部亦庄经海路" in joined
    assert "profile wizard -> refresh --prepare -> runtime web search/browser -> refresh --evidence -> report" in joined
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
