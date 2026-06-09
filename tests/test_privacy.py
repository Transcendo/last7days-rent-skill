from pathlib import Path

from lib.privacy import assert_public_safe, public_text_violations, redact_text


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


def test_public_guard_detects_unredacted_fields():
    text = "联系人：张三 手机13812345678 微信wxabc12345 五角场租房群"
    violations = public_text_violations(text)
    assert {"phone", "wechat", "private_group", "real_name"} <= set(violations)


def test_public_guard_accepts_generic_privacy_statement():
    assert_public_safe("公开报告已脱敏手机号、微信号、群名、真实姓名、头像或截图来源身份线索。")
