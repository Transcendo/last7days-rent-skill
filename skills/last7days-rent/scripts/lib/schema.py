from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Literal


TrustLevel = Literal["L0", "L1", "L2", "L3"]
SourceTier = Literal["P0", "P1", "P2", "private", "websearch", "non_mvp"]
RentalMode = Literal["whole", "shared", "either"]
ContactRoute = Literal["platform", "phone", "wechat", "qq", "feishu", "email", "original_post", "user_authorized", "unknown"]

UNKNOWN = "unknown"
MVP_SOURCE_IDS = {"beike_lianjia", "wellcee", "fang", "official_verifier"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    return value


@dataclass
class RentProfile:
    profile_meta: dict[str, Any] = field(default_factory=dict)
    privacy: dict[str, Any] = field(default_factory=dict)
    user_goal: dict[str, Any] = field(default_factory=dict)
    office_anchor: dict[str, Any] = field(default_factory=dict)
    commute: dict[str, Any] = field(default_factory=dict)
    housing_constraints: dict[str, Any] = field(default_factory=dict)
    decision_preferences: dict[str, Any] = field(default_factory=dict)
    scoring_weights: dict[str, float] = field(default_factory=dict)
    source_preferences: dict[str, Any] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "RentProfile":
        return cls(
            profile_meta={"schema_version": "0.1.0", "created_at": now_iso(), "updated_at": now_iso()},
            privacy={"storage": "local_private", "redact_public_output": True},
            user_goal={"slogan": "last7days = 帮助用户 7 天完成租房", "target_days": 7},
            office_anchor={"company": None, "office_name": None, "address_hint": None, "city": None, "confidence": 0.0},
            commute={"max_minutes": 35, "preferred_transit": ["metro", "walk"], "derived_areas": []},
            housing_constraints={"budget_min": None, "budget_max": None, "rental_mode": "either", "move_in_by": None},
            decision_preferences={},
            scoring_weights={
                "commute": 0.3,
                "budget": 0.25,
                "trust": 0.2,
                "freshness": 0.15,
                "preference": 0.1,
                "risk_penalty": 0.35,
            },
            source_preferences={"p0_order": ["beike_lianjia", "wellcee", "fang", "official_verifier"]},
            open_questions=["请先确认公司、办公点或园区，用它推导城市和通勤圈。"],
            provenance={"created_by": "last7days-rent local engine"},
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RentProfile":
        base = cls.default()
        merged = to_plain(base)
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
        return cls(**merged)

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class SearchRequest:
    city: str | None = None
    office_anchor: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    days: int = 7
    limit: int = 10
    sources: list[str] = field(default_factory=list)
    fixture: bool = False

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class SearchPlan:
    request: SearchRequest
    commute_areas: list[str] = field(default_factory=list)
    source_queries: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    contact_requirements: list[str] = field(default_factory=lambda: ["platform", "phone", "wechat", "qq", "feishu", "email", "original_post", "user_authorized"])
    risk_filters: list[str] = field(default_factory=lambda: ["p1_p2_source_not_allowed", "private_source_not_allowed", "websearch_not_allowed"])
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class SourceFetchResult:
    source_id: str
    url: str
    status: str
    fetched_at: str = field(default_factory=now_iso)
    elapsed_ms: int | None = None
    http_status: int | None = None
    warning: str | None = None
    raw_path: str | None = None
    candidate_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class SourceCandidate:
    candidate_id: str
    source_id: str
    source_tier: SourceTier
    source_url: str | None
    title: str
    snippet: str | None = None
    collected_at: str = field(default_factory=now_iso)
    can_promote: bool = True
    raw: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ContactMethod:
    contact_type: ContactRoute
    value: str | None = None
    entry_url: str | None = None
    source_field: str | None = None
    public_visible: bool = True
    collected_at: str = field(default_factory=now_iso)
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContactMethod":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class ListingItem:
    item_id: str
    source_id: str
    source_tier: SourceTier
    title: str
    body: str = ""
    source_url: str | None = None
    platform_id: str | None = None
    published_at: str | None = None
    maintained_at: str | None = None
    collected_at: str = field(default_factory=now_iso)
    city: str | None = None
    district: str | None = None
    community_name: str | None = None
    address_hint: str | None = None
    price_monthly: int | None = None
    deposit: str | None = None
    payment_cycle: str | None = None
    service_fee: str | None = None
    agency_fee: str | None = None
    layout: str | None = None
    area_sqm: float | None = None
    floor: str | None = None
    orientation: str | None = None
    available_from: str | None = None
    contact_route: ContactRoute = "unknown"
    contact_methods: list[ContactMethod] = field(default_factory=list)
    raw_contact_redacted: bool = False
    image_hashes: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    trust_level: TrustLevel = "L1"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ListingItem":
        normalized = dict(data)
        normalized["contact_methods"] = [
            method if isinstance(method, ContactMethod) else ContactMethod.from_dict(method)
            for method in normalized.get("contact_methods", [])
        ]
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class ListingCluster:
    cluster_id: str
    canonical_listing: ListingItem
    source_items: list[ListingItem]
    merge_reasons: list[str] = field(default_factory=list)
    trust_level: TrustLevel = "L1"
    match_score: float = 0.0
    risk_score: float = 0.0
    final_score: float = 0.0
    risk_flags: list[str] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)
    next_questions: list[str] = field(default_factory=list)
    field_provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)


@dataclass
class VerificationEvidence:
    evidence_id: str
    source_id: str
    evidence_type: str
    value: str | None
    url: str | None = None
    collected_at: str = field(default_factory=now_iso)
    notes: str | None = None


@dataclass
class FeedbackEvent:
    event_id: str
    listing_id: str
    event_type: str
    created_at: str = field(default_factory=now_iso)
    notes: str | None = None
    source_id: str | None = None
    effects: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_plain(self)
