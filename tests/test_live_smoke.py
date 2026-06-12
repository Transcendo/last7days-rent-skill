import pytest

from lib.sources.router import smoke_source


@pytest.mark.live
def test_beike_live_smoke_reports_candidates_or_blocking():
    result = smoke_source("beike_lianjia", city="上海", area="五角场", limit=3)
    assert result["fetches"], result
    assert result["candidate_count"] >= 1 or result["warnings"], result
