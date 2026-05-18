from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeadSource:
    name: str
    role: str
    collection_status: str
    access_notes: str
    completeness_note: str
    verification_note: str


LEAD_SOURCE_REGISTRY: dict[str, LeadSource] = {
    "NYFA Opportunities Board": LeadSource(
        name="NYFA Opportunities Board",
        role="discovery",
        collection_status="manual_or_research",
        access_notes="Usable as a discovery source through manual research or assisted browsing, but direct automated collection may be blocked.",
        completeness_note="Useful for finding leads, but collection is not yet complete or automated from this environment.",
        verification_note="Use NYFA as a discovery source and verify against the organizer or application page.",
    ),
    "CaFE": LeadSource(
        name="CaFE",
        role="discovery",
        collection_status="planned",
        access_notes="Public call pages are generally accessible enough for Step 2 discovery and detail-page review.",
        completeness_note="Public coverage appears workable for candidate collection, but still requires verification against the organizer or official application page.",
        verification_note="Use CaFE as a discovery source and verify against the organizer or official application page.",
    ),
    "Artenda": LeadSource(
        name="Artenda",
        role="discovery",
        collection_status="planned",
        access_notes="Public access is partial and some useful listing details may be limited or hidden behind previews or subscription prompts.",
        completeness_note="Step 2 collection from public pages is likely incomplete, so treat Artenda as a weaker discovery signal source for now.",
        verification_note="Use Artenda as a discovery source and verify against the organizer or official application page.",
    ),
    "ArtDeadline": LeadSource(
        name="ArtDeadline",
        role="discovery",
        collection_status="planned",
        access_notes="Public listing pages are generally accessible enough for Step 2 discovery and detail-page review.",
        completeness_note="Public coverage appears workable for candidate collection, but still requires verification against the organizer or official application page.",
        verification_note="Use ArtDeadline as a discovery source and verify against the organizer or official application page.",
    ),
}


def get_supported_lead_sources() -> list[str]:
    return list(LEAD_SOURCE_REGISTRY.keys())
