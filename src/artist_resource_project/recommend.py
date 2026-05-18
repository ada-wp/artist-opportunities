from __future__ import annotations

from dataclasses import asdict
from datetime import date

from .ai import OpenAITextAssistant
from .config import DEFAULT_DATA_DIR, DEFAULT_REFERENCE_DATE, DEFAULT_TOP_K
from .intake import IntakeSubmission, intake_to_artist_profile
from .models import ArtistProfile, Recommendation
from .repository import load_artist_profiles, load_opportunities
from .scoring import rank_opportunities


def recommend_from_intake(
    submission: IntakeSubmission,
    data_dir: str = DEFAULT_DATA_DIR,
    top_k: int = DEFAULT_TOP_K,
    today: date | None = None,
) -> dict[str, object]:
    artist = intake_to_artist_profile(submission)
    return recommend_for_profile(
        artist,
        data_dir=data_dir,
        top_k=top_k,
        today=today,
        recipient_email=submission.email,
    )


def recommend_for_profile(
    artist: ArtistProfile,
    data_dir: str = DEFAULT_DATA_DIR,
    top_k: int = DEFAULT_TOP_K,
    today: date | None = None,
    recipient_email: str | None = None,
) -> dict[str, object]:
    reference_day = today or date.fromisoformat(DEFAULT_REFERENCE_DATE)
    opportunities = load_opportunities(data_dir)

    ai = OpenAITextAssistant()
    ranked = rank_opportunities(artist, opportunities, top_k=top_k, today=reference_day)

    recommendations: list[Recommendation] = []
    for index, scored in enumerate(ranked, start=1):
        fit_summary = ai.generate_fit_explanation(
            {
                "artist_name": artist.name,
                "artist_style": artist.style_description,
                "artist_themes": artist.themes,
                "career_goal": artist.career_goal,
                "opportunity_title": scored.opportunity.title,
                "opportunity_description": scored.opportunity.opportunity_description,
                "theme_signals": scored.opportunity.theme_signals,
                "score_breakdown": scored.score_breakdown,
            }
        ) or _fallback_fit_summary(artist, scored.opportunity, scored.score_breakdown)

        recommendations.append(
            Recommendation(
                rank=index,
                opportunity_id=scored.opportunity.id,
                title=scored.opportunity.title,
                organizer=scored.opportunity.organizer,
                deadline=scored.opportunity.deadline,
                application_fee_usd=scored.opportunity.application_fee_usd,
                accepted_media=scored.opportunity.accepted_media,
                location=scored.opportunity.location,
                eligibility=asdict(scored.opportunity.eligibility),
                source_name=scored.opportunity.source_name,
                score=scored.total_score,
                score_breakdown=scored.score_breakdown,
                fit_summary=fit_summary,
                caution_note=scored.caution_note,
                application_url=scored.opportunity.application_url,
            )
        )

    payload: dict[str, object] = {
        "artist_id": artist.id,
        "artist_name": artist.name,
        "generated_on": reference_day.isoformat(),
        "top_recommendations": [asdict(item) for item in recommendations],
    }
    if recipient_email:
        payload["recipient_email"] = recipient_email
    return payload


def recommend_for_artist(
    artist_id: str,
    data_dir: str = DEFAULT_DATA_DIR,
    top_k: int = DEFAULT_TOP_K,
    today: date | None = None,
) -> dict[str, object]:
    artists = load_artist_profiles(data_dir)
    artist = _find_artist(artists, artist_id)
    return recommend_for_profile(artist, data_dir=data_dir, top_k=top_k, today=today)


def _find_artist(artists: list[ArtistProfile], artist_id: str) -> ArtistProfile:
    for artist in artists:
        if artist.id == artist_id:
            return artist
    raise ValueError(f"Unknown artist_id: {artist_id}")


def _fallback_fit_summary(
    artist: ArtistProfile,
    opportunity,
    score_breakdown: dict[str, float],
) -> str:
    strongest = max(score_breakdown, key=score_breakdown.get)
    return (
        f"Strong fit for {artist.name} because it supports painting and aligns with "
        f"themes such as {', '.join(opportunity.theme_signals[:2])}. "
        f"Highest scoring factor: {strongest.replace('_', ' ')}."
    )
