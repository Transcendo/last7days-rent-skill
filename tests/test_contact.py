from lib.contact import contact_display_text, extract_contact_methods, has_actionable_contact, platform_contact


def test_extracts_and_preserves_public_contact_methods():
    text = "手机 13812345678，微信 wxabc12345，QQ 1234567，邮箱 renter@example.com，原帖联系说明：站内私信。"
    methods = extract_contact_methods(text, entry_url="https://example.com/listing/1")
    display = contact_display_text(methods)
    assert "13812345678" in display
    assert "wxabc12345" in display
    assert "renter@example.com" in display
    assert has_actionable_contact(methods)


def test_platform_entry_is_actionable_contact():
    methods = [platform_contact("https://sh.zu.fang.com/chuzu/3_431717913_1.htm")]
    assert has_actionable_contact(methods)
    assert "平台入口" in contact_display_text(methods)
