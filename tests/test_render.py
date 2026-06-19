from lib.render import render_listing_pool_html


def test_render_listing_pool_html_has_filters_and_privacy_note():
    html = render_listing_pool_html(
        {
            "pool_meta": {"pool_id": "jd-hq-beijing", "updated_at": "2026-06-13T10:00:00+08:00"},
            "profile_summary": {"office_anchor": "北京京东总部", "budget_max": 5500, "preferred_bedrooms": 2},
            "listings": [
                {
                    "listing_id": "listing-1",
                    "status": "new",
                    "trust_level": "L1",
                    "title": "次渠锦园二居",
                    "community": "次渠锦园",
                    "district_hint": "次渠南",
                    "price_text": "5300元/月",
                    "area_text": "60平",
                    "layout_text": "2室",
                    "source_urls": ["https://example.com/listing/1"],
                    "source_names": ["豆瓣公开小组"],
                    "risk_flags": ["needs_fee_verification"],
                    "next_actions": ["确认仍在租"],
                    "first_seen_at": "2026-06-13T10:00:00+08:00",
                }
            ],
        }
    )

    assert "北京京东总部" in html
    assert "次渠锦园二居" in html
    assert "全部可信等级" in html
    assert "避坑指南" in html
    assert "https://nest-hub.eggcampus.com/" in html
    assert "京东总部租房避坑指南" not in html
    assert "下一步策略" in html
    assert "来源覆盖" in html
    assert "风险指南" in html
    assert "今天先做" in html
    assert "按房源行动" in html
    assert "7 天计划" in html
    assert "打开豆瓣公开小组来源" in html
    assert "下一步：确认仍在租" not in html
    assert "不保存 cookie" in html
