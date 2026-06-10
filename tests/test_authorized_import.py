from lib.authorized_import import import_authorized_text
from lib.contact import has_actionable_contact


def test_authorized_import_preserves_user_provided_contact():
    item = import_authorized_text("五角场转租 4200 元/月\n微信 wxabc12345\n邮箱 renter@example.com")
    assert item.trust_level == "L1"
    assert has_actionable_contact(item)
    assert {method.contact_type for method in item.contact_methods} >= {"wechat", "email"}
