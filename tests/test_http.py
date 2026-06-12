from urllib.error import HTTPError
from io import BytesIO

from lib.sources import http


class _Headers:
    def get(self, name, default=None):
        return default

    def get_content_charset(self):
        return "utf-8"


class _Response:
    status = 200
    headers = _Headers()

    def __init__(self, url):
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size):
        return "北京亦庄一居室".encode("utf-8")

    def geturl(self):
        return self._url


def test_fetch_public_url_percent_encodes_non_ascii_url(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return _Response(request.full_url)

    monkeypatch.setattr(http, "_urlopen_no_redirect", fake_urlopen)

    text, result = http.fetch_public_url("basic_http", "https://example.com/北京/经海路?q=一居室")

    assert text == "北京亦庄一居室"
    assert result.status == "ok"
    assert "%E5%8C%97%E4%BA%AC" in captured["url"]
    assert "%E4%B8%80%E5%B1%85%E5%AE%A4" in captured["url"]


def test_fetch_public_url_records_redirect_without_following(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 302, "Found", {}, BytesIO(b"redirect"))

    monkeypatch.setattr(http, "_urlopen_no_redirect", fake_urlopen)

    _, result = http.fetch_public_url("fang", "https://zu.fang.com/")

    assert result.status == "failed"
    assert result.http_status == 302
    assert result.warning == "http_302"
