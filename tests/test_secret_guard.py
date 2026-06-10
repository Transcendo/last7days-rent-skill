import pytest

from lib.secret_guard import assert_no_secrets, sanitize_text, scrub_headers, secret_violations


def test_secret_guard_detects_credentials():
    text = "Authorization: Bearer abcdefghijklmnop token=abcdefghijkl secret=abcdefghijkl sessionid=abcdefghijkl"
    violations = secret_violations(text)
    assert {"authorization", "token", "secret", "session"} <= set(violations)
    with pytest.raises(ValueError):
        assert_no_secrets(text)


def test_secret_guard_sanitizes_cache_text_and_headers():
    assert "[blocked-credential]" in sanitize_text("Cookie: sid=abcdefghijkl;")
    headers = scrub_headers({"Authorization": "Bearer abcdefghijklmnop", "User-Agent": "ok"})
    assert headers == {"User-Agent": "ok"}
