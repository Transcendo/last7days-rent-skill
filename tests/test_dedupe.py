from lib.dedupe import dedupe_listings
from lib.schema import ListingItem


def test_dedupe_multisource_same_listing():
    left = ListingItem(
        item_id="a",
        source_id="beike_lianjia",
        source_tier="P0",
        title="政立路一室户 42㎡",
        community_name="政立路小区",
        layout="1室1厅",
        area_sqm=42,
        price_monthly=4200,
    )
    right = ListingItem(
        item_id="b",
        source_id="wellcee",
        source_tier="P0",
        title="政立路一室户转租 42㎡",
        community_name="政立路小区",
        layout="1室1厅",
        area_sqm=42,
        price_monthly=4200,
    )
    clusters = dedupe_listings([left, right])
    assert len(clusters) == 1
    assert clusters[0].trust_level == "L2"
