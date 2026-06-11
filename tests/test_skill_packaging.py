from pathlib import Path
import subprocess
import sys


SKILL_DIR = Path("skills/last7days-rent")


def test_skill_md_uses_installed_skill_relative_cli_path():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "python scripts/last7days_rent.py" in text
    assert "skills/last7days-rent/scripts/last7days_rent.py" not in text


def test_cli_runs_from_installed_skill_root_layout(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/last7days_rent.py", "--help"],
        cwd=SKILL_DIR,
        text=True,
        capture_output=True,
        env={"LAST7DAYS_RENT_HOME": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert "search" in result.stdout


def test_fixture_search_works_without_repo_tests_fixture_dir(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/last7days_rent.py", "search", "--fixture"],
        cwd=SKILL_DIR,
        text=True,
        capture_output=True,
        env={"LAST7DAYS_RENT_HOME": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert "未找到可进入 MVP 短名单" not in result.stdout
    assert "HTML report:" in result.stdout
    assert (tmp_path / "reports" / "last7days-rent-fixture.html").exists()
