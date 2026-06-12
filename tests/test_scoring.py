from lib.dedupe import dedupe_listings
from lib.scoring import score_clusters
from lib.schema import ListingItem, RentProfile


def test_l1_is_not_verified_and_l3_not_auto_created():
    profile = RentProfile.from_dict(
        {
            "office_anchor": {"office_name": "上海五角场", "city": "上海"},
            "commute": {"derived_areas": ["五角场"], "max_minutes": 35},
            "housing_constraints": {"budget_min": 3500, "budget_max": 5200},
        }
    )
    item = ListingItem(
        item_id="a",
        source_id="wellcee",
        source_tier="P0",
        title="五角场一室户",
        body="五角场",
        city="上海",
        price_monthly=4200,
    )
    cluster = score_clusters(dedupe_listings([item]), profile)[0]
    assert cluster.trust_level == "L1"
    assert cluster.trust_level != "L3"
    assert any("不能视为已验真" in reason for reason in cluster.match_reasons)


def test_min_bedrooms_preference_adds_match_reason():
    profile = RentProfile.from_dict(
        {
            "office_anchor": {"office_name": "北京亦庄", "city": "北京"},
            "commute": {"derived_areas": ["亦庄"], "max_minutes": 30},
            "housing_constraints": {"budget_max": 5200, "min_bedrooms": 1, "rental_mode": "whole"},
        }
    )
    item = ListingItem(
        item_id="a",
        source_id="wellcee",
        source_tier="P0",
        title="亦庄一居室整租",
        body="亦庄核心区，1居室，4300元/月",
        city="北京",
        price_monthly=4300,
        layout="1居室",
    )
    cluster = score_clusters(dedupe_listings([item]), profile)[0]
    assert any("至少 1 间卧室" in reason for reason in cluster.match_reasons)
