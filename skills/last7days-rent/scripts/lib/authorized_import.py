from __future__ import annotations

import hashlib
from pathlib import Path

from .contact import attach_contact_methods, extract_contact_methods
from .schema import ListingItem, now_iso


def import_authorized_text(text: str, *, source_url: str | None = None, source_label: str = "user_authorized") -> ListingItem:
    title = _first_non_empty_line(text) or "用户授权导入房源"
    item_id = "user-import-" + hashlib.sha1(text.encode()).hexdigest()[:12]
    item = ListingItem(
        item_id=item_id,
        source_id=source_label,
        source_tier="private",
        source_url=source_url,
        title=title,
        body=text,
        trust_level="L1",
        contact_route="unknown",
        collected_at=now_iso(),
        provenance={"body": "user_authorized_input"},
    )
    attach_contact_methods(item, extract_contact_methods(text, entry_url=source_url, source_field="user_authorized_input"))
    return item


def import_authorized_file(path: str | Path, *, source_url: str | None = None) -> ListingItem:
    text = Path(path).expanduser().read_text(encoding="utf-8")
    return import_authorized_text(text, source_url=source_url)


def _first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:80]
    return None
