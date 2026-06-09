from lib.schema import ListingItem, RentProfile, SourceCandidate, VerificationEvidence


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
    assert candidate.can_promote is True
    assert evidence.value is None
