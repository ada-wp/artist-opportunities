from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ArtistProfile:
    id: str
    name: str
    primary_medium: str
    style_description: str
    themes: list[str]
    budget_cap_usd: float
    minimum_days_until_deadline: int
    career_goal: str
    eligible_regions: list[str]
    career_stage: str
    geographic_preferences: list[str] = field(default_factory=list)
    eligibility_constraints: list[str] = field(default_factory=list)
    artwork_image_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchFilters:
    lead_sources: list[str]
    medium_preferences: list[str]
    budget_cap_usd: float
    eligible_regions: list[str]
    minimum_days_until_deadline: int
    opportunity_types: list[str] = field(default_factory=lambda: ["open_call"])
    location_preferences: list[str] = field(default_factory=list)
    format_preferences: list[str] = field(default_factory=list)
    geographic_scope_preferences: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.lead_sources:
            raise ValueError("lead_sources must contain at least one source")
        if any(not source.strip() for source in self.lead_sources):
            raise ValueError("lead_sources may not contain empty values")
        if not self.medium_preferences:
            raise ValueError("medium_preferences must contain at least one medium")
        if any(not medium.strip() for medium in self.medium_preferences):
            raise ValueError("medium_preferences may not contain empty values")
        if self.budget_cap_usd < 0:
            raise ValueError("budget_cap_usd must be non-negative")
        if self.minimum_days_until_deadline < 0:
            raise ValueError("minimum_days_until_deadline must be non-negative")
        if not self.eligible_regions:
            raise ValueError("eligible_regions must contain at least one region")


@dataclass(frozen=True)
class Eligibility:
    regions: list[str]
    career_stages: list[str]
    notes: str = ""


@dataclass(frozen=True)
class Opportunity:
    id: str
    title: str
    organizer: str
    source_name: str
    source_type: str
    source_url: str
    confidence_level: str
    verification_status: str
    listing_url: str
    application_url: str
    deadline: str
    application_fee_usd: float
    accepted_media: list[str]
    eligibility: Eligibility
    location: str
    opportunity_description: str
    theme_signals: list[str]
    career_value_signals: list[str]
    opportunity_type: str = "open_call"
    disciplines: list[str] = field(default_factory=list)
    lead_source_url: str = ""
    verified_from_url: str = ""
    page_check_status: str = "unchecked"
    is_live: bool = False
    verified_at: str = ""
    last_checked_at: str = ""
    notable_restrictions: list[str] = field(default_factory=list)
    image_reference_urls: list[str] = field(default_factory=list)
    quality_score: int = 3

    def deadline_date(self) -> date:
        return date.fromisoformat(self.deadline)


@dataclass(frozen=True)
class CandidateOpportunity:
    opportunity_id: str
    source_name: str
    source_listing_url: str
    title: str
    organizer: str
    official_url: str
    application_url: str
    deadline: str
    application_fee_usd: float
    accepted_media: list[str]
    eligible_regions: list[str]
    location: str
    opportunity_type: str
    meets_medium_filter: bool
    meets_budget_filter: bool
    meets_region_filter: bool
    meets_deadline_filter: bool
    collected_at: str
    notes: str = ""

    def __post_init__(self) -> None:
        required_fields = {
            "opportunity_id": self.opportunity_id,
            "source_name": self.source_name,
            "source_listing_url": self.source_listing_url,
            "title": self.title,
            "organizer": self.organizer,
            "official_url": self.official_url,
            "application_url": self.application_url,
            "deadline": self.deadline,
            "location": self.location,
            "opportunity_type": self.opportunity_type,
            "collected_at": self.collected_at,
        }
        for field_name, value in required_fields.items():
            if not value.strip():
                raise ValueError(f"{field_name} is required")


@dataclass(frozen=True)
class SourceCollectionSummary:
    source_name: str
    candidate_count: int
    candidate_ids: list[str]
    collection_status: str
    access_notes: str
    completeness_note: str

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if self.candidate_count < 0:
            raise ValueError("candidate_count must be non-negative")
        if not self.collection_status.strip():
            raise ValueError("collection_status is required")
        if not self.access_notes.strip():
            raise ValueError("access_notes is required")
        if not self.completeness_note.strip():
            raise ValueError("completeness_note is required")


@dataclass(frozen=True)
class VerificationReview:
    opportunity_id: str
    page_live: bool
    opportunity_real: bool
    deadline_confirmed: bool
    confirmed_deadline: str
    fee_confirmed: bool
    confirmed_fee_text: str
    eligibility_confirmed: bool
    confirmed_eligibility_notes: str
    application_link_confirmed: bool
    verified_from_url: str
    overall_status: str
    reviewed_at: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip():
            raise ValueError("opportunity_id is required")
        if not self.overall_status.strip():
            raise ValueError("overall_status is required")
        if not self.reviewed_at.strip():
            raise ValueError("reviewed_at is required")
        if not self.verified_from_url.strip():
            raise ValueError("verified_from_url is required")
        if self.deadline_confirmed and not self.confirmed_deadline.strip():
            raise ValueError("confirmed_deadline is required when deadline_confirmed is True")
        if self.fee_confirmed and not self.confirmed_fee_text.strip():
            raise ValueError("confirmed_fee_text is required when fee_confirmed is True")
        if self.eligibility_confirmed and not self.confirmed_eligibility_notes.strip():
            raise ValueError(
                "confirmed_eligibility_notes is required when eligibility_confirmed is True"
            )


@dataclass(frozen=True)
class OrganizerReview:
    organizer_name: str
    website_quality: str
    past_programming_quality: str
    artist_quality_signal: str
    social_presence_quality: str
    outside_reference_signal: str
    fee_and_terms_risk: str
    opportunity_type_reality: str
    juror_credibility: str
    audience_quality: str
    consistency_signal: str
    strategic_value: str
    competitiveness_level: str
    good_signs: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        required_fields = {
            "organizer_name": self.organizer_name,
            "website_quality": self.website_quality,
            "past_programming_quality": self.past_programming_quality,
            "artist_quality_signal": self.artist_quality_signal,
            "social_presence_quality": self.social_presence_quality,
            "outside_reference_signal": self.outside_reference_signal,
            "fee_and_terms_risk": self.fee_and_terms_risk,
            "opportunity_type_reality": self.opportunity_type_reality,
            "juror_credibility": self.juror_credibility,
            "audience_quality": self.audience_quality,
            "consistency_signal": self.consistency_signal,
            "strategic_value": self.strategic_value,
            "competitiveness_level": self.competitiveness_level,
        }
        for field_name, value in required_fields.items():
            if not value.strip():
                raise ValueError(f"{field_name} is required")


@dataclass(frozen=True)
class MatchArtistProfile:
    career_stage: str
    medium_preferences: list[str]
    style_description: str
    themes: list[str]
    career_goal: str
    artwork_image_paths: list[str] = field(default_factory=list)
    target_visibility: list[str] = field(default_factory=list)
    preferred_contexts: list[str] = field(default_factory=list)
    competitiveness_tolerance: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.career_stage.strip():
            raise ValueError("career_stage is required")
        if not self.medium_preferences:
            raise ValueError("medium_preferences must contain at least one medium")
        if any(not medium.strip() for medium in self.medium_preferences):
            raise ValueError("medium_preferences may not contain empty values")
        if not self.style_description.strip():
            raise ValueError("style_description is required")
        if not self.career_goal.strip():
            raise ValueError("career_goal is required")
        if len(self.artwork_image_paths) > 10:
            raise ValueError("artwork_image_paths may contain at most 10 images")


@dataclass(frozen=True)
class MatchAssessment:
    opportunity_id: str
    organizer_name: str
    medium_fit: str
    style_fit: str
    theme_fit: str
    career_fit: str
    organizer_context_fit: str
    strategic_value_fit: str
    competitiveness_fit: str
    overall_match: str
    strengths: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    rationale: str = ""

    def __post_init__(self) -> None:
        required_fields = {
            "opportunity_id": self.opportunity_id,
            "organizer_name": self.organizer_name,
            "medium_fit": self.medium_fit,
            "style_fit": self.style_fit,
            "theme_fit": self.theme_fit,
            "career_fit": self.career_fit,
            "organizer_context_fit": self.organizer_context_fit,
            "strategic_value_fit": self.strategic_value_fit,
            "competitiveness_fit": self.competitiveness_fit,
            "overall_match": self.overall_match,
        }
        for field_name, value in required_fields.items():
            if not value.strip():
                raise ValueError(f"{field_name} is required")


@dataclass(frozen=True)
class RankedMatch:
    rank: int
    opportunity_id: str
    organizer_name: str
    overall_match: str
    rationale: str


@dataclass(frozen=True)
class Recommendation:
    rank: int
    opportunity_id: str
    title: str
    organizer: str
    deadline: str
    application_fee_usd: float
    accepted_media: list[str]
    location: str
    eligibility: dict[str, object]
    source_name: str
    score: float
    score_breakdown: dict[str, float]
    fit_summary: str
    caution_note: str
    application_url: str
