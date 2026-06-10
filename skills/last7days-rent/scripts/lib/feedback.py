from __future__ import annotations

from pathlib import Path

from .env import ensure_local_dirs
from .schema import FeedbackEvent
from .store import append_jsonl, read_jsonl


POSITIVE_EVENTS = {"real_viewable", "track"}
NEGATIVE_EVENTS = {
    "rented",
    "expired",
    "too_far",
    "too_expensive",
    "lead_gen_suspected",
    "reject_agent",
    "untrusted_source",
    "contact_failed",
    "wrong_contact",
}


def append_feedback(event: FeedbackEvent) -> Path:
    paths = ensure_local_dirs()
    append_jsonl(paths.feedback_jsonl, event.to_dict())
    return paths.feedback_jsonl


def load_feedback() -> list[dict]:
    return read_jsonl(ensure_local_dirs().feedback_jsonl)


def feedback_boost_for_listing(listing_id: str, source_id: str | None = None) -> float:
    boost = 0.0
    for row in load_feedback():
        if row.get("listing_id") == listing_id or (source_id and row.get("source_id") == source_id):
            if row.get("event_type") in POSITIVE_EVENTS:
                boost += 0.08
            if row.get("event_type") in NEGATIVE_EVENTS:
                boost -= 0.12
    return boost
