import json
from html.parser import HTMLParser

from lib.pipeline import run_search
from lib.privacy import public_text_violations


def test_fixture_search_outputs_report_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    result = run_search(fixture=True, output_dir=str(tmp_path / "reports"))
    assert result.html_path.exists()
    assert result.evidence_path.exists()
    assert result.html.startswith("<!doctype html>")
    parser = HTMLParser()
    parser.feed(result.html)
    parser.close()
    assert "7 天租房行动计划" in result.html
    assert "Source Coverage" in result.html
    assert "Search Provider Coverage" in result.html
    assert "Contact Coverage" in result.html
    assert "搜索发现线索" in result.html
    assert "L1 不是已验真" in result.html
    assert "平台入口:" in result.html
    assert public_text_violations(result.html) == []
    lower_html = result.html.lower()
    assert "<script" not in lower_html
    assert 'rel="stylesheet"' not in lower_html
    assert "fonts.googleapis" not in lower_html
    assert "file://" not in lower_html
    for forbidden in ["token", "session", "authorization", "cookie"]:
        assert forbidden not in lower_html
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["privacy"]["contact_methods_preserved_for_action"] is True
    assert evidence["privacy"]["secret_guard_enabled"] is True
    assert evidence["search_provider_coverage"]
    assert evidence["search_leads"]
    assert evidence["promoted_leads"]
    assert evidence["rejected_leads"]
    assert evidence["clusters"]
