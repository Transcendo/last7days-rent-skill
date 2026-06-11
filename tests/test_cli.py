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


def test_help_smoke(tmp_path):
    result = run_cli(["--help"], tmp_path)
    assert result.returncode == 0
    assert "profile" in result.stdout


def test_search_help_shows_providers(tmp_path):
    result = run_cli(["search", "--help"], tmp_path)
    assert result.returncode == 0
    assert "--providers" in result.stdout
    assert "--sources" in result.stdout
    assert "--runtime-websearch-json" in result.stdout
    assert "--no-provider-fallback" in result.stdout


def test_profile_show_missing_is_nonzero_but_redacted_safe(tmp_path):
    result = run_cli(["profile", "show", "--redacted"], tmp_path)
    assert result.returncode == 1
    assert "尚未找到本地 profile" in result.stderr


def test_fixture_search_smoke(tmp_path):
    result = run_cli(["search", "--fixture", "--providers", "brave,tavily,exa"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Search provider coverage:" in result.stdout
    assert "HTML report:" in result.stdout
    assert (tmp_path / "reports" / "last7days-rent-fixture.html").exists()


def test_runtime_websearch_search_smoke(tmp_path):
    result = run_cli(
        [
            "search",
            "--office-anchor",
            "上海五角场",
            "--city",
            "上海",
            "--budget-max",
            "5200",
            "--runtime-websearch-json",
            "tests/fixtures/websearch/runtime_web_search_success.json",
            "--no-provider-fallback",
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "- runtime_web_search: status=ok" in result.stdout
    evidence_path = tmp_path / "reports" / "last7days-rent-live.json"
    assert evidence_path.exists()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert {item["provider"] for item in evidence["search_provider_coverage"]} == {"runtime_web_search"}
    assert {cluster["canonical_listing"]["source_id"] for cluster in evidence["clusters"]} == {"wellcee", "fang"}


def test_report_latest_returns_html_path(tmp_path):
    search = run_cli(["search", "--fixture"], tmp_path)
    assert search.returncode == 0, search.stderr
    result = run_cli(["report", "--latest"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("last7days-rent-fixture.html")


def test_sources_list_separates_providers_and_listing_sources(tmp_path):
    result = run_cli(["sources", "list"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert '"search_providers"' in result.stdout
    assert '"listing_sources"' in result.stdout
