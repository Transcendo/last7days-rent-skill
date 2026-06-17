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


def test_validate_evidence_rejects_fake_l1_without_opened_detail(tmp_path):
    evidence = {
        "runtime_meta": {"runtime_name": "fixture"},
        "query_context": {"anchor_id": "beijing-jd-hq-yizhuang"},
        "items": [
            {
                "evidence_id": "ev-fake-l1",
                "batch_id": "p0_price_anchor",
                "query_id": "p0-q01",
                "query": "北京 京东总部 一居 租房",
                "collected_via": "web_search_result",
                "source_url": "https://example.com/search-result",
                "source_name": "Example",
                "source_domain": "example.com",
                "source_type": "platform_listing",
                "page_opened": False,
                "url_class": "search_result",
                "listing_candidate_status": "candidate_l1",
                "title": "搜索结果页",
                "snippet": "经海路一居 5800",
                "raw_excerpt": "搜索结果摘要，不是详情页",
                "observed_at": "2026-06-14T10:00:00+08:00",
                "visible_fields": {"price_text": "5800元/月", "district_hint": "经海路"},
            }
        ],
    }
    path = tmp_path / "fake-l1.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

    errors = validate_evidence_file(path)
    messages = " ".join(error["message"] for error in errors)
    assert "candidate_l1 requires page_opened=true" in messages
    assert "candidate_l1 cannot be login/captcha/app-wall/search-result only" in messages


def test_validate_evidence_rejects_private_identity_leak(tmp_path):
    evidence = {
        "query_context": {"anchor_id": "beijing-jd-hq-yizhuang"},
        "items": [
            {
                "evidence_id": "ev-private",
                "batch_id": "community_posts",
                "query_id": "community-q01",
                "query": "次渠南 京东总部 租房",
                "collected_via": "opened_page",
                "source_url": "https://example.org/post/1",
                "source_name": "公开帖子",
                "source_domain": "example.org",
                "source_type": "community_post",
                "page_opened": True,
                "title": "次渠南出租",
                "snippet": "联系人：张三，微信：wxabc12345",
                "raw_excerpt": "联系人：张三，微信：wxabc12345",
                "observed_at": "2026-06-14T10:00:00+08:00",
                "visible_fields": {"price_text": "5800元/月", "district_hint": "次渠南", "layout_text": "一居"},
            }
        ],
    }
    path = tmp_path / "private.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

    errors = validate_evidence_file(path)
    messages = " ".join(error["message"] for error in errors)
    assert "raw wechat id must be redacted" in messages
    assert "poster/contact name must be redacted" in messages


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
