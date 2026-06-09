from lib.risk import risk_flags_for_listing, should_reject_listing
from lib.schema import ListingItem, RentProfile


def test_p1_p2_sources_cannot_enter_mvp_pipeline():
    item = ListingItem(item_id="58-1", source_id="58", source_tier="P2", title="低价房", price_monthly=1800)
    assert should_reject_listing(item)
    assert "p1_p2_source_not_allowed" in risk_flags_for_listing(item)


def test_private_and_websearch_sources_rejected():
    private = ListingItem(item_id="p", source_id="wechat_group", source_tier="private", title="群内房源")
    web = ListingItem(item_id="w", source_id="websearch", source_tier="websearch", title="搜索片段")
    assert "private_source_not_allowed" in risk_flags_for_listing(private)
    assert "websearch_not_allowed" in risk_flags_for_listing(web)


def test_low_price_and_missing_fee_flags():
    profile = RentProfile.from_dict({"housing_constraints": {"budget_min": 4000, "budget_max": 6000}})
    item = ListingItem(item_id="x", source_id="wellcee", source_tier="P0", title="异常低价", price_monthly=1500)
    flags = risk_flags_for_listing(item, profile)
    assert "low_price_anomaly" in flags
    assert "fee_terms_missing" in flags
