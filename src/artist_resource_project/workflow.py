from __future__ import annotations

from dataclasses import asdict
from datetime import date

from .config import DEFAULT_REFERENCE_DATE
from .lead_sources import LEAD_SOURCE_REGISTRY
from .models import (
    CandidateOpportunity,
    MatchAssessment,
    MatchArtistProfile,
    Opportunity,
    OrganizerReview,
    RankedMatch,
    SearchFilters,
    SourceCollectionSummary,
    VerificationReview,
)


def collect_candidate_opportunities(
    filters: SearchFilters,
    opportunities: list[Opportunity],
    today: date | None = None,
) -> list[CandidateOpportunity]:
    reference_day = today or date.fromisoformat(DEFAULT_REFERENCE_DATE)
    candidates: list[CandidateOpportunity] = []

    for opportunity in opportunities:
        if opportunity.source_name not in filters.lead_sources:
            continue

        meets_medium_filter = _medium_matches(filters.medium_preferences, opportunity)
        meets_budget_filter = opportunity.application_fee_usd <= filters.budget_cap_usd
        meets_region_filter = _region_matches(filters.eligible_regions, opportunity)
        meets_deadline_filter = _deadline_matches(
            filters.minimum_days_until_deadline,
            reference_day,
            opportunity,
        )
        meets_type_filter = opportunity.opportunity_type in filters.opportunity_types

        if not all(
            [
                meets_medium_filter,
                meets_budget_filter,
                meets_region_filter,
                meets_deadline_filter,
                meets_type_filter,
            ]
        ):
            continue

        candidates.append(
            CandidateOpportunity(
                opportunity_id=opportunity.id,
                source_name=opportunity.source_name,
                source_listing_url=opportunity.listing_url,
                title=opportunity.title,
                organizer=opportunity.organizer,
                official_url=opportunity.verified_from_url or opportunity.source_url,
                application_url=opportunity.application_url,
                deadline=opportunity.deadline,
                application_fee_usd=opportunity.application_fee_usd,
                accepted_media=opportunity.accepted_media,
                eligible_regions=opportunity.eligibility.regions,
                location=opportunity.location,
                opportunity_type=opportunity.opportunity_type,
                meets_medium_filter=meets_medium_filter,
                meets_budget_filter=meets_budget_filter,
                meets_region_filter=meets_region_filter,
                meets_deadline_filter=meets_deadline_filter,
                collected_at=reference_day.isoformat(),
            )
        )

    return candidates


def select_verified_candidates(
    candidates: list[CandidateOpportunity],
    verification_reviews: list[VerificationReview],
) -> list[CandidateOpportunity]:
    verified_ids = {
        review.opportunity_id
        for review in verification_reviews
        if review.overall_status == "verified"
        and review.page_live
        and review.opportunity_real
        and review.deadline_confirmed
        and review.fee_confirmed
        and review.eligibility_confirmed
        and review.application_link_confirmed
    }
    return [candidate for candidate in candidates if candidate.opportunity_id in verified_ids]


def build_source_collection_summaries(
    filters: SearchFilters,
    candidates: list[CandidateOpportunity],
) -> list[SourceCollectionSummary]:
    candidate_ids_by_source: dict[str, list[str]] = {source_name: [] for source_name in filters.lead_sources}
    for candidate in candidates:
        candidate_ids_by_source.setdefault(candidate.source_name, []).append(candidate.opportunity_id)

    summaries: list[SourceCollectionSummary] = []
    for source_name in filters.lead_sources:
        source_meta = LEAD_SOURCE_REGISTRY.get(source_name)
        candidate_ids = candidate_ids_by_source.get(source_name, [])
        summaries.append(
            SourceCollectionSummary(
                source_name=source_name,
                candidate_count=len(candidate_ids),
                candidate_ids=candidate_ids,
                collection_status=(
                    source_meta.collection_status if source_meta else "unknown"
                ),
                access_notes=(
                    source_meta.access_notes
                    if source_meta
                    else "No access notes have been recorded for this source."
                ),
                completeness_note=(
                    source_meta.completeness_note
                    if source_meta
                    else "No completeness note has been recorded for this source."
                ),
            )
        )
    return summaries


def rank_top_matches(
    assessments: list[MatchAssessment],
    limit: int = 3,
) -> list[RankedMatch]:
    ranked = sorted(
        assessments,
        key=lambda assessment: (
            -_label_score(assessment.overall_match),
            -_label_score(assessment.strategic_value_fit),
            -_label_score(assessment.career_fit),
            -_label_score(assessment.organizer_context_fit),
            -_label_score(assessment.medium_fit),
            assessment.opportunity_id,
        ),
    )
    return [
        RankedMatch(
            rank=index,
            opportunity_id=assessment.opportunity_id,
            organizer_name=assessment.organizer_name,
            overall_match=assessment.overall_match,
            rationale=assessment.rationale,
        )
        for index, assessment in enumerate(ranked[:limit], start=1)
    ]


def build_match_workflow_summary(
    filters: SearchFilters,
    artist_profile: MatchArtistProfile,
    candidates: list[CandidateOpportunity],
    verification_reviews: list[VerificationReview],
    organizer_reviews: list[OrganizerReview],
    match_assessments: list[MatchAssessment],
) -> dict[str, object]:
    verified_candidates = select_verified_candidates(candidates, verification_reviews)
    source_collection_summaries = build_source_collection_summaries(filters, candidates)
    top_matches = rank_top_matches(match_assessments)

    return {
        "search_filters": asdict(filters),
        "artist_profile": asdict(artist_profile),
        "candidate_opportunities": [asdict(candidate) for candidate in candidates],
        "source_collection_summaries": [asdict(summary) for summary in source_collection_summaries],
        "verification_reviews": [asdict(review) for review in verification_reviews],
        "organizer_reviews": [asdict(review) for review in organizer_reviews],
        "verified_candidate_ids": [candidate.opportunity_id for candidate in verified_candidates],
        "match_assessments": [asdict(assessment) for assessment in match_assessments],
        "top_matches": [asdict(match) for match in top_matches],
    }


def _medium_matches(medium_preferences: list[str], opportunity: Opportunity) -> bool:
    accepted_media = {value.lower() for value in opportunity.accepted_media}
    disciplines = {value.lower() for value in opportunity.disciplines}
    opportunity_media = accepted_media | disciplines

    for medium in medium_preferences:
        filter_value = medium.strip().lower()
        if filter_value in opportunity_media:
            return True
        if "painting" in filter_value and {"painting", "2d", "visual arts", "mixed media"} & opportunity_media:
            return True
        if "drawing" in filter_value and {"drawing", "2d", "visual arts"} & opportunity_media:
            return True
    return False


def _region_matches(eligible_regions: list[str], opportunity: Opportunity) -> bool:
    candidate_regions = {region.lower() for region in eligible_regions}
    opportunity_regions = {region.lower() for region in opportunity.eligibility.regions}
    return bool(candidate_regions & opportunity_regions or "international" in opportunity_regions)


def _deadline_matches(minimum_days: int, reference_day: date, opportunity: Opportunity) -> bool:
    days_until_deadline = (opportunity.deadline_date() - reference_day).days
    return days_until_deadline >= minimum_days


def _label_score(value: str) -> int:
    normalized = value.strip().lower()
    mapping = {
        "very high": 5,
        "high": 4,
        "strong": 4,
        "good": 3,
        "medium-high": 3,
        "medium": 2,
        "mixed": 1,
        "low-medium": 1,
        "low": 0,
        "weak": 0,
    }
    return mapping.get(normalized, 0)
