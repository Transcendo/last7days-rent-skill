from lib.feedback import append_feedback, feedback_boost_for_listing
from lib.schema import FeedbackEvent


def test_feedback_jsonl_and_boost(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST7DAYS_RENT_HOME", str(tmp_path))
    event = FeedbackEvent(event_id="fb1", listing_id="listing-1", event_type="real_viewable", source_id="wellcee")
    path = append_feedback(event)
    assert path.exists()
    assert feedback_boost_for_listing("listing-1", "wellcee") > 0
