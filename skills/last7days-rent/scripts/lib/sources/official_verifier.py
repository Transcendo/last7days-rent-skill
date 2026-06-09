from __future__ import annotations

import hashlib
import re

from ..privacy import redact_text
from ..schema import VerificationEvidence, now_iso


VERIFY_RE = re.compile(r"(?:核验码|备案号|房源发布码)\s*[:：]?\s*([A-Za-z0-9-]{4,40})")


def parse_official_verifier_text(text: str, url: str | None = None) -> list[VerificationEvidence]:
    evidences: list[VerificationEvidence] = []
    for match in VERIFY_RE.finditer(text):
        value = redact_text(match.group(1))
        evidence_id = "verify-" + hashlib.sha1(f"{value}{url}".encode()).hexdigest()[:12]
        evidences.append(
            VerificationEvidence(
                evidence_id=evidence_id,
                source_id="official_verifier",
                evidence_type="rental_verification_code",
                value=value,
                url=url,
                collected_at=now_iso(),
                notes="官方核验入口证据，只用于后续核验，不作为高召回来源。",
            )
        )
    return evidences
