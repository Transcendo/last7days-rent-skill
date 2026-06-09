from pathlib import Path

from lib.sources.beike_lianjia import parse_beike_lianjia_html
from lib.sources.fang import parse_fang_html
from lib.sources.official_verifier import parse_official_verifier_text
from lib.sources.registry import get_source_meta, is_enabled_p0_source, source_registry
from lib.sources.wellcee import parse_wellcee_jsonld


FIXTURES = Path("tests/fixtures/sources")


def test_registry_disables_non_mvp_sources():
    registry = source_registry()
    for source_id in ["58", "anjuke", "douban", "xiaohongshu", "weibo", "wechat_official", "wechat_group", "websearch", "user_import"]:
        assert registry[source_id]["enabled"] is False
        assert registry[source_id]["status"] == "non_mvp"
    assert is_enabled_p0_source("wellcee")
    assert get_source_meta("official_verifier").can_promote_to_listing is False


def test_beike_lianjia_fixture_parser():
    items = parse_beike_lianjia_html((FIXTURES / "beike_lianjia.html").read_text(encoding="utf-8"))
    assert len(items) == 2
    assert items[0].platform_id == "SH2143668995679584256"
    assert items[0].price_monthly == 4200


def test_wellcee_jsonld_parser():
    items = parse_wellcee_jsonld((FIXTURES / "wellcee.html").read_text(encoding="utf-8"))
    assert len(items) == 1
    assert items[0].source_id == "wellcee"
    assert items[0].price_monthly == 4200


def test_fang_parser_and_official_verifier():
    items = parse_fang_html((FIXTURES / "fang.html").read_text(encoding="utf-8"))
    evidence = parse_official_verifier_text((FIXTURES / "official_verifier.txt").read_text(encoding="utf-8"))
    assert items[0].source_id == "fang"
    assert items[0].price_monthly == 5100
    assert evidence[0].source_id == "official_verifier"
