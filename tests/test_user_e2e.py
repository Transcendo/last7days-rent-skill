import json
import os
import subprocess
import sys
from pathlib import Path

from lib.pipeline import run_search
from lib.profile_store import init_profile
from lib.providers.registry import ProviderRegistry, ProviderResolution
from lib.schema import ProviderDiagnostic, SearchHit


CLI = Path("skills/last7days-rent/scripts/last7days_rent.py")


def run_cli(args, state_dir):
    env = os.environ.copy()
    env["LAST7DAYS_RENT_HOME"] = str(state_dir)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        env=env,
    )


def test_user_can_start_from_reset_profile_and_complete_fixture_flow(tmp_path):
    state_dir = tmp_path / "last7days-home"
    assert not state_dir.exists()

    missing = run_cli(["profile", "show", "--redacted"], state_dir)
    assert missing.returncode == 1
    assert "尚未找到本地 profile" in missing.stderr

    init = run_cli(
        [
            "profile",
            "init",
            "--office-anchor",
            "北京亦庄办公点",
            "--city",
            "北京",
            "--budget-max",
            "5200",
            "--commute-minutes",
            "35",
            "--rental-mode",
            "whole",
            "--min-bedrooms",
            "1",
        ],
        state_dir,
    )
    assert init.returncode == 0, init.stderr
    assert "北京亦庄办公点" in init.stdout
    assert (state_dir / "profile.json").exists()
    assert (state_dir / "profile.md").exists()

    shown = run_cli(["profile", "show", "--redacted"], state_dir)
    assert shown.returncode == 0, shown.stderr
    profile = json.loads(shown.stdout)
    assert profile["office_anchor"]["office_name"] == "北京亦庄办公点"
    assert profile["office_anchor"]["city"] == "北京"
    assert profile["housing_constraints"]["budget_max"] == 5200
    assert profile["housing_constraints"]["min_bedrooms"] == 1

    search = run_cli(["search", "--fixture", "--limit", "3"], state_dir)
    assert search.returncode == 0, search.stderr
    assert "近 7 天候选房源：北京 / 北京亦庄办公点 / 预算 5200" in search.stdout
    assert "Markdown report:" in search.stdout
    assert "JSON evidence:" in search.stdout

    report_path = state_dir / "reports" / "last7days-rent-fixture.md"
    evidence_path = state_dir / "reports" / "last7days-rent-fixture.json"
    assert report_path.exists()
    assert evidence_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "- 办公点: 北京亦庄办公点" in report
    assert "- 城市: 北京" in report
    assert "- 最少卧室: 1" in report
    assert "7 天租房行动计划" in report

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["mode"] == "fixture"
    assert evidence["profile_redacted_summary"]["office_anchor"]["office_name"] == "北京亦庄办公点"
    assert evidence["profile_redacted_summary"]["office_anchor"]["city"] == "北京"
    assert evidence["clusters"]

    latest = run_cli(["report", "--latest"], state_dir)
    assert latest.returncode == 0, latest.stderr
    assert str(report_path) in latest.stdout

    feedback = run_cli(
        [
            "feedback",
            "--listing-id",
            evidence["clusters"][0]["cluster_id"],
            "--event-type",
            "track",
            "--notes",
            "用户准备联系核验",
        ],
        state_dir,
    )
    assert feedback.returncode == 0, feedback.stderr
    assert (state_dir / "feedback.jsonl").exists()


def test_profile_init_then_default_search_returns_l0_leads_without_extract_key(tmp_path, monkeypatch):
    class FakeDDGS:
        name = "ddgs"

        def is_available(self):
            return True

        def search(self, query, limit=5, **options):
            return [
                SearchHit(
                    provider=self.name,
                    query=query,
                    title="北京亦庄京东总部附近一居整租",
                    url="https://bj.zu.ke.com/zufang/yizhuang1/pg2/",
                    description="亦庄核心区，3500 元/月，36.00㎡，1室0厅，1天前维护",
                    position=1,
                )
            ]

    class BasicHttpShouldNotRun:
        name = "basic_http"

        def extract(self, urls, **options):
            raise AssertionError("default no-key E2E must not extract detail pages")

    def fake_resolve(self):
        return ProviderResolution(
            search_provider=FakeDDGS(),
            extract_provider=BasicHttpShouldNotRun(),
            diagnostics=[
                ProviderDiagnostic("search", "auto", "ddgs", "ddgs", "selected"),
                ProviderDiagnostic("extract", "auto", "basic_http", "basic_http", "fallback"),
            ],
        )

    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path / "last7days-home"))
    monkeypatch.setattr(ProviderRegistry, "resolve", fake_resolve)
    init_profile(
        office_anchor="北京亦庄京东总部",
        city="北京",
        budget_max=5200,
        commute_minutes=35,
        rental_mode="whole",
        min_bedrooms=1,
    )

    result = run_search(limit=5, output_dir=str(tmp_path / "reports"))
    assert "待核验房源线索" in result.chat_summary
    assert "https://bj.zu.ke.com/zufang/yizhuang1/pg2/" in result.chat_summary
    assert "已找到 L0 待核验线索" in result.chat_summary
    assert "未找到符合当前预算" not in result.chat_summary
    assert result.acquisition.actionable_leads
    assert not result.acquisition.extracted_documents

    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["actionable_leads"]
    assert evidence["verified_shortlist"] == []
    assert evidence["blocked_sources"] == []
