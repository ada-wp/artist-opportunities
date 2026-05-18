from __future__ import annotations

from pathlib import Path
import pytest

from artist_resource_project.models import (
    MatchArtistProfile,
    MatchAssessment,
    OrganizerReview,
    SearchFilters,
    VerificationReview,
)
from artist_resource_project.lead_sources import get_supported_lead_sources
from artist_resource_project.recommend import recommend_for_artist
from artist_resource_project.repository import load_artist_profiles, load_opportunities
from artist_resource_project.scoring import filter_opportunities
from artist_resource_project.ui_prototype import write_ui_prototype
from artist_resource_project.workflow import (
    build_match_workflow_summary,
    build_source_collection_summaries,
    collect_candidate_opportunities,
    rank_top_matches,
    select_verified_candidates,
)


DATA_DIR = "data/seed"


def test_filter_opportunities_excludes_unverified_and_short_deadlines() -> None:
    artists = load_artist_profiles(DATA_DIR)
    opportunities = load_opportunities(DATA_DIR)
    artist = next(item for item in artists if item.id == "painter_001")

    filtered = filter_opportunities(artist, opportunities)
    filtered_ids = {item.id for item in filtered}

    assert "opp_011" not in filtered_ids
    assert "opp_012" not in filtered_ids


def test_load_opportunities_reads_seed_records() -> None:
    opportunities = load_opportunities(DATA_DIR)

    assert opportunities
    assert len(opportunities) == 12
    assert "NYFA Opportunities Board" in {item.source_name for item in opportunities}
    assert "Instagram Lead" in {item.source_name for item in opportunities}


def test_recommend_for_artist_returns_ranked_payload() -> None:
    payload = recommend_for_artist("painter_003")

    assert payload["artist_id"] == "painter_003"
    assert payload["generated_on"] == "2026-03-29"
    assert payload["top_recommendations"]
    assert payload["top_recommendations"][0]["rank"] == 1


def test_structured_match_workflow_models_hold_expected_fields() -> None:
    search_filters = SearchFilters(
        lead_sources=["NYFA Opportunities Board", "CaFE"],
        medium_preferences=["oil painting", "drawing"],
        budget_cap_usd=100,
        eligible_regions=["US"],
        minimum_days_until_deadline=10,
        opportunity_types=["open_call", "residency"],
    )
    organizer_review = OrganizerReview(
        organizer_name="Example Gallery",
        website_quality="strong",
        past_programming_quality="strong",
        artist_quality_signal="good",
        social_presence_quality="moderate",
        outside_reference_signal="moderate",
        fee_and_terms_risk="low",
        opportunity_type_reality="physical exhibition",
        juror_credibility="strong",
        audience_quality="strong",
        consistency_signal="strong",
        strategic_value="high",
        competitiveness_level="high",
    )
    artist_profile = MatchArtistProfile(
        career_stage="emerging",
        medium_preferences=["oil painting", "drawing"],
        style_description="Contemporary figurative painting with an atelier foundation.",
        themes=["figure", "atmosphere", "psychology"],
        career_goal="Start getting into galleries and build reputation.",
        artwork_image_paths=[f"work_{index}.jpg" for index in range(1, 11)],
        target_visibility=["gallery exposure", "reputation building"],
        preferred_contexts=["commercial gallery", "nonprofit"],
        competitiveness_tolerance="high",
    )
    assessment = MatchAssessment(
        opportunity_id="opp_example",
        organizer_name="Example Gallery",
        medium_fit="high",
        style_fit="high",
        theme_fit="medium",
        career_fit="high",
        organizer_context_fit="high",
        strategic_value_fit="high",
        competitiveness_fit="medium",
        overall_match="strong",
    )

    assert search_filters.lead_sources == ["NYFA Opportunities Board", "CaFE"]
    assert search_filters.medium_preferences == ["oil painting", "drawing"]
    assert search_filters.minimum_days_until_deadline == 10
    assert organizer_review.organizer_name == "Example Gallery"
    assert artist_profile.medium_preferences == ["oil painting", "drawing"]
    assert len(artist_profile.artwork_image_paths) == 10
    assert assessment.overall_match == "strong"


def test_search_filters_require_core_values() -> None:
    with pytest.raises(ValueError):
        SearchFilters(
            lead_sources=["NYFA Opportunities Board"],
            medium_preferences=[],
            budget_cap_usd=100,
            eligible_regions=["US"],
            minimum_days_until_deadline=10,
        )


def test_match_artist_profile_limits_uploaded_images_to_ten() -> None:
    with pytest.raises(ValueError):
        MatchArtistProfile(
            career_stage="emerging",
            medium_preferences=["oil painting"],
            style_description="Quiet figurative painting.",
            themes=["figure"],
            career_goal="Build gallery reputation.",
            artwork_image_paths=[f"work_{index}.jpg" for index in range(1, 12)],
        )


def test_collect_candidate_opportunities_applies_only_hard_filters() -> None:
    opportunities = load_opportunities(DATA_DIR)
    filters = SearchFilters(
        lead_sources=["NYFA Opportunities Board"],
        medium_preferences=["oil painting", "drawing"],
        budget_cap_usd=100,
        eligible_regions=["US"],
        minimum_days_until_deadline=10,
    )

    candidates = collect_candidate_opportunities(filters, opportunities)
    candidate_ids = {candidate.opportunity_id for candidate in candidates}

    assert "opp_011" not in candidate_ids
    assert "opp_012" not in candidate_ids
    assert "opp_002" in candidate_ids
    assert all(candidate.source_name == "NYFA Opportunities Board" for candidate in candidates)


def test_verified_candidate_selection_requires_fully_verified_review() -> None:
    opportunities = load_opportunities(DATA_DIR)
    filters = SearchFilters(
        lead_sources=["NYFA Opportunities Board"],
        medium_preferences=["oil painting", "drawing"],
        budget_cap_usd=100,
        eligible_regions=["US"],
        minimum_days_until_deadline=10,
    )
    candidates = collect_candidate_opportunities(filters, opportunities)
    reviews = [
        VerificationReview(
            opportunity_id="opp_002",
            page_live=True,
            opportunity_real=True,
            deadline_confirmed=True,
            confirmed_deadline="2026-04-15",
            fee_confirmed=True,
            confirmed_fee_text="$40 for 1-3 works",
            eligibility_confirmed=True,
            confirmed_eligibility_notes="Open to U.S. resident artists.",
            application_link_confirmed=True,
            verified_from_url="https://www.firststreetgallery.org/exhibitions/nje-prospectus/",
            overall_status="verified",
            reviewed_at="2026-03-31",
        ),
        VerificationReview(
            opportunity_id="opp_012",
            page_live=True,
            opportunity_real=True,
            deadline_confirmed=True,
            confirmed_deadline="2026-04-02",
            fee_confirmed=True,
            confirmed_fee_text="$15",
            eligibility_confirmed=False,
            confirmed_eligibility_notes="",
            application_link_confirmed=True,
            verified_from_url="https://example.org/opportunity",
            overall_status="needs_follow_up",
            reviewed_at="2026-03-31",
        ),
    ]

    verified = select_verified_candidates(candidates, reviews)

    assert [candidate.opportunity_id for candidate in verified] == ["opp_002"]


def test_source_collection_summaries_report_selected_sources() -> None:
    opportunities = load_opportunities(DATA_DIR)
    filters = SearchFilters(
        lead_sources=["NYFA Opportunities Board", "CaFE", "ArtDeadline", "Artenda"],
        medium_preferences=["oil painting", "drawing"],
        budget_cap_usd=100,
        eligible_regions=["US"],
        minimum_days_until_deadline=10,
        opportunity_types=["open_call", "residency"],
    )

    candidates = collect_candidate_opportunities(filters, opportunities)
    summaries = build_source_collection_summaries(filters, candidates)
    summaries_by_source = {summary.source_name: summary for summary in summaries}

    assert summaries_by_source["NYFA Opportunities Board"].candidate_count >= 1
    assert summaries_by_source["CaFE"].collection_status == "planned"
    assert "accessible" in summaries_by_source["CaFE"].access_notes.lower()
    assert "incomplete" in summaries_by_source["Artenda"].completeness_note.lower()


def test_match_workflow_summary_builds_top_matches() -> None:
    opportunities = load_opportunities(DATA_DIR)
    filters = SearchFilters(
        lead_sources=["NYFA Opportunities Board", "CaFE"],
        medium_preferences=["oil painting", "drawing"],
        budget_cap_usd=100,
        eligible_regions=["US"],
        minimum_days_until_deadline=10,
    )
    candidates = collect_candidate_opportunities(filters, opportunities)
    artist_profile = MatchArtistProfile(
        career_stage="emerging",
        medium_preferences=["oil painting", "drawing"],
        style_description="Contemporary figurative work with tonal sensitivity.",
        themes=["figure", "atmosphere", "psychology"],
        career_goal="Start getting into galleries and build reputation.",
        artwork_image_paths=[f"work_{index}.jpg" for index in range(1, 4)],
        target_visibility=["gallery exposure"],
        preferred_contexts=["commercial gallery"],
        competitiveness_tolerance="medium-high",
    )
    organizer_reviews = [
        OrganizerReview(
            organizer_name="Example Gallery",
            website_quality="strong",
            past_programming_quality="strong",
            artist_quality_signal="good",
            social_presence_quality="moderate",
            outside_reference_signal="moderate",
            fee_and_terms_risk="low",
            opportunity_type_reality="physical exhibition",
            juror_credibility="strong",
            audience_quality="strong",
            consistency_signal="strong",
            strategic_value="high",
            competitiveness_level="high",
        )
    ]
    verification_reviews = [
        VerificationReview(
            opportunity_id="opp_002",
            page_live=True,
            opportunity_real=True,
            deadline_confirmed=True,
            confirmed_deadline="2026-04-15",
            fee_confirmed=True,
            confirmed_fee_text="$40 for 1-3 works",
            eligibility_confirmed=True,
            confirmed_eligibility_notes="Open to U.S. resident artists.",
            application_link_confirmed=True,
            verified_from_url="https://www.firststreetgallery.org/exhibitions/nje-prospectus/",
            overall_status="verified",
            reviewed_at="2026-03-31",
        )
    ]
    assessments = [
        MatchAssessment(
            opportunity_id="opp_002",
            organizer_name="Example Gallery",
            medium_fit="high",
            style_fit="high",
            theme_fit="medium",
            career_fit="high",
            organizer_context_fit="high",
            strategic_value_fit="high",
            competitiveness_fit="medium",
            overall_match="strong",
            rationale="Strong gallery-context opportunity for an emerging figurative painter.",
        ),
        MatchAssessment(
            opportunity_id="opp_008",
            organizer_name="Another Gallery",
            medium_fit="high",
            style_fit="medium",
            theme_fit="medium",
            career_fit="medium",
            organizer_context_fit="medium",
            strategic_value_fit="medium",
            competitiveness_fit="medium",
            overall_match="medium",
            rationale="Valid but strategically weaker than the top choice.",
        ),
    ]

    ranked = rank_top_matches(assessments)
    summary = build_match_workflow_summary(
        filters=filters,
        artist_profile=artist_profile,
        candidates=candidates,
        verification_reviews=verification_reviews,
        organizer_reviews=organizer_reviews,
        match_assessments=assessments,
    )

    assert ranked[0].opportunity_id == "opp_002"
    assert summary["verified_candidate_ids"] == ["opp_002"]
    assert len(summary["source_collection_summaries"]) == 2
    assert summary["top_matches"][0]["opportunity_id"] == "opp_002"


def test_lead_source_registry_includes_next_planned_sources() -> None:
    supported = get_supported_lead_sources()

    assert "NYFA Opportunities Board" in supported
    assert "CaFE" in supported
    assert "Artenda" in supported
    assert "ArtDeadline" in supported


def test_ui_prototype_writer_creates_html_file() -> None:
    output_path = Path(DATA_DIR) / "ui_prototype_test.html"

    try:
        written = write_ui_prototype(output_path)

        assert written == output_path
        assert output_path.exists()
        assert "<title>Artist Opportunity Workflow Prototype</title>" in output_path.read_text(encoding="utf-8")
    finally:
        if output_path.exists():
            output_path.unlink()
