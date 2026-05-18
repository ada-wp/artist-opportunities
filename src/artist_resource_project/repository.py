from __future__ import annotations

import json
from pathlib import Path

from .models import ArtistProfile, Eligibility, Opportunity


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artist_profiles(data_dir: str | Path) -> list[ArtistProfile]:
    base = Path(data_dir)
    payload = _load_json(base / "artist_profiles.json")
    return [ArtistProfile(**item) for item in payload]


def load_opportunities(data_dir: str | Path) -> list[Opportunity]:
    base = Path(data_dir)
    payload = _load_json(base / "opportunities.json")
    records: list[Opportunity] = []

    for item in payload:
        item = _normalize_opportunity_record(item)
        eligibility = Eligibility(**item["eligibility"])
        item = {**item, "eligibility": eligibility}
        records.append(Opportunity(**item))

    return records


def _normalize_opportunity_record(item: dict) -> dict:
    lead_source_url = item.get("lead_source_url") or item.get("source_url", "")
    verified_from_url = item.get("verified_from_url") or item.get("application_url", "")
    page_check_status = item.get("page_check_status", "unchecked")
    disciplines = item.get("disciplines") or list(item.get("accepted_media", []))
    opportunity_type = item.get("opportunity_type", "open_call")

    return {
        **item,
        "lead_source_url": lead_source_url,
        "verified_from_url": verified_from_url,
        "page_check_status": page_check_status,
        "disciplines": disciplines,
        "opportunity_type": opportunity_type,
        "is_live": item.get("is_live", False),
        "verified_at": item.get("verified_at", ""),
        "last_checked_at": item.get("last_checked_at", ""),
    }
