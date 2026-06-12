import json

from lib.pipeline import run_search


def test_fixture_pipeline_preserves_contact_and_rejects_non_mvp(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    result = run_search(fixture=True, output_dir=str(tmp_path / "reports"))
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["clusters"]
    assert evidence["privacy"]["contact_methods_preserved_for_action"] is True
    assert all(cluster["canonical_listing"]["contact_methods"] for cluster in evidence["clusters"])
    assert {cluster["canonical_listing"]["source_id"] for cluster in evidence["clusters"]} <= {"beike_lianjia", "wellcee", "fang"}
