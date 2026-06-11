from lib.schema import (
    ContactMethod,
    FeedbackEvent,
    ListingCluster,
    ListingItem,
    RentProfile,
    SearchLead,
    SearchPlan,
    SearchProviderQuery,
    SearchProviderResult,
    SearchRequest,
    SourceCandidate,
    SourceFetchResult,
    VerificationEvidence,
)


def test_profile_is_office_anchor_first():
    profile = RentProfile.default()
    assert "office_anchor" in profile.to_dict()
    assert profile.office_anchor["city"] is None
    assert any("公司" in q or "办公点" in q for q in profile.open_questions)


def test_missing_fields_stay_none():
    item = ListingItem(item_id="x", source_id="wellcee", source_tier="P0", title="缺字段房源")
    assert item.price_monthly is None
    assert item.deposit is None
    assert item.available_from is None


def test_shared_contracts_importable():
    candidate = SourceCandidate(candidate_id="c1", source_id="wellcee", source_tier="P0", source_url=None, title="t")
    evidence = VerificationEvidence(evidence_id="e1", source_id="official_verifier", evidence_type="code", value=None)
    request = SearchRequest(city="上海", office_anchor="五角场", budget_max=5200)
    provider_query = SearchProviderQuery(provider="brave", query="上海 五角场 租房")
    plan = SearchPlan(request=request, provider_queries=[provider_query], source_queries={"fang": [{"url": "https://sh.zu.fang.com/"}]})
    provider_result = SearchProviderResult(provider="brave", status="skipped", query=provider_query.query, warning="brave_missing_api_key")
    lead = SearchLead(lead_id="lead-1", provider="brave", query=provider_query.query, rank=1, title="t", url="https://example.com", domain="example.com")
    fetch = SourceFetchResult(source_id="fang", url="https://sh.zu.fang.com/", status="ok", http_status=200)
    contact = ContactMethod("platform", entry_url="https://example.com")
    listing = ListingItem(item_id="l1", source_id="fang", source_tier="P0", title="t", contact_methods=[contact], contact_route="platform")
    cluster = ListingCluster(cluster_id="c1", canonical_listing=listing, source_items=[listing])
    feedback = FeedbackEvent(event_id="f1", listing_id="l1", event_type="real_viewable")
    assert candidate.can_promote is True
    assert evidence.value is None
    assert plan.request.city == "上海"
    assert provider_result.warning == "brave_missing_api_key"
    assert lead.can_promote is False
    assert fetch.http_status == 200
    assert cluster.trust_level == "L1"
    assert feedback.event_type == "real_viewable"
