import json

from lib.pipeline import run_search
from lib.privacy import public_text_violations


def test_fixture_search_outputs_report_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    result = run_search(fixture=True, output_dir=str(tmp_path / "reports"))
    assert result.markdown_path.exists()
    assert result.evidence_path.exists()
    assert "7 天租房行动计划" in result.markdown
    assert "P0 Source Coverage" in result.markdown
    assert "L1 不是已验真" in result.markdown
    assert public_text_violations(result.markdown) == []
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["privacy"]["no_plain_phone_wechat_group_real_name"] is True
    assert evidence["clusters"]
