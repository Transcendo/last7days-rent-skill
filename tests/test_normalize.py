from lib.normalize import canonical_url, normalize_listings
from lib.schema import ListingItem, RentProfile


def test_canonical_url_strips_utm():
    assert canonical_url("HTTPS://Example.COM/a/?utm_source=x&b=1") == "https://example.com/a?b=1"


def test_normalize_rejects_non_mvp():
    profile = RentProfile.default()
    good = ListingItem(item_id="good", source_id="wellcee", source_tier="P0", title="好房")
    bad = ListingItem(item_id="bad", source_id="douban", source_tier="P2", title="豆瓣")
    accepted, rejected = normalize_listings([good, bad], profile)
    assert [item.item_id for item in accepted] == ["good"]
    assert [item.item_id for item in rejected] == ["bad"]
