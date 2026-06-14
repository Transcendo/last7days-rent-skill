import json

from lib.agent_evidence import ingest_evidence_file, validate_evidence_file


def test_validate_evidence_reports_field_errors(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"query_context": {}, "items": [{"source_url": "not-a-url"}]}), encoding="utf-8")
    errors = validate_evidence_file(bad)
    paths = {error["path"] for error in errors}
    assert "items[0].batch_id" in paths
    assert "items[0].query_id" in paths
    assert "items[0].page_opened" in paths
    assert "items[0].raw_excerpt" in paths
    assert "items[0].source_url" in paths


def test_ingest_evidence_merges_independent_sources_to_l2(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    pool, path = ingest_evidence_file("tests/fixtures/evidence/jd_hq_runtime_evidence.json")
    assert path.exists()
    assert len(pool["listings"]) == 2
    merged = next(item for item in pool["listings"] if item["community"] == "次渠锦园北区")
    assert merged["trust_level"] == "L2"
    assert len(merged["observations"]) == 2
    snippet_only = next(item for item in pool["listings"] if item["community"] == "经海路小区")
    assert snippet_only["trust_level"] == "L0"
