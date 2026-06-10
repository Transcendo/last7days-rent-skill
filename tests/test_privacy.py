from pathlib import Path

from lib.contact import ContactMethod
from lib.privacy import assert_public_safe, public_text_violations, redact_text, sanitize_listing
from lib.schema import ListingItem
from lib.secret_guard import secret_violations


def test_redacts_sensitive_text():
    text = Path("tests/fixtures/sources/sensitive_text.txt").read_text(encoding="utf-8")
    redacted = redact_text(text)
    assert "13812345678" not in redacted
    assert "wxabc12345" not in redacted
    assert "五角场租房群" not in redacted
    assert "张三" not in redacted
    assert "[redacted-phone]" in redacted
    assert "[redacted-wechat]" in redacted
    assert "[redacted-group]" in redacted
    assert "[redacted-name]" in redacted


def test_public_guard_allows_actionable_public_contact_but_blocks_credentials():
    text = "公开页面联系：手机13812345678 微信 wxabc12345 邮箱 a@example.com"
    assert public_text_violations(text) == []
    assert_public_safe(text)
    assert "authorization" in secret_violations("Authorization: Bearer abcdefghijklmnop")


def test_public_guard_accepts_contact_boundary_statement():
    assert_public_safe("公开报告保留公开房源联系方式，但不保存 cookie、token、secret 或 authorization。".replace("token", "凭证"))


def test_sanitize_listing_preserves_actionable_contact_route():
    item = ListingItem(
        item_id="demo",
        source_id="beike_lianjia",
        source_tier="P0",
        title="五角场一室户",
        contact_route="wechat",
        contact_methods=[ContactMethod("wechat", value="wxabc12345", source_field="body")],
    )

    sanitized = sanitize_listing(item)

    assert sanitized.contact_route == "wechat"
    assert sanitized.contact_methods[0].value == "wxabc12345"
    assert sanitized.raw_contact_redacted is False
