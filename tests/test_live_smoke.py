import pytest

from lib.sources.router import smoke_source


@pytest.mark.live
def test_brave_live_smoke_reports_leads_or_provider_warning():
    result = smoke_source("brave", city="上海", area="五角场", limit=3)
    assert result["provider_results"], result
    assert result["lead_count"] >= 1 or result["warnings"], result
