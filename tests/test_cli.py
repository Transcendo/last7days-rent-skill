import os
import subprocess
import sys
from pathlib import Path


CLI = Path("skills/last7days-rent/scripts/last7days_rent.py")


def run_cli(args, tmp_path):
    env = os.environ.copy()
    env["LAST7DAYS_RENT_HOME"] = str(tmp_path)
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, env=env)


def test_help_smoke(tmp_path):
    result = run_cli(["--help"], tmp_path)
    assert result.returncode == 0
    assert "profile" in result.stdout


def test_profile_show_missing_is_nonzero_but_redacted_safe(tmp_path):
    result = run_cli(["profile", "show", "--redacted"], tmp_path)
    assert result.returncode == 1
    assert "尚未找到本地 profile" in result.stderr


def test_fixture_search_smoke(tmp_path):
    result = run_cli(["search", "--fixture"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Markdown report:" in result.stdout
    assert (tmp_path / "reports" / "last7days-rent-fixture.md").exists()


def test_fixture_search_accepts_provider_flags(tmp_path):
    result = run_cli(["search", "--fixture", "--provider-search", "ddgs", "--provider-extract", "basic_http"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "JSON evidence:" in result.stdout
