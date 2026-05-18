from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from .config import DEFAULT_REFERENCE_DATE, ScoringWeights
from .models import ArtistProfile, Opportunity


@dataclass(frozen=True)
class ScoredOpportunity:
    opportunity: Opportunity
    total_score: float
    score_breakdown: dict[str, float]
    caution_note: str


def filter_opportunities(
    artist: ArtistProfile,
    opportunities: list[Opportunity],
    today: date | None = None,
) -> list[Opportunity]:
    reference_day = today or date.fromisoformat(DEFAULT_REFERENCE_DATE)
    filtered: list[Opportunity] = []

    for opportunity in opportunities:
        if opportunity.deadline_date() < reference_day:
            continue
        if not _medium_supported(opportunity):
            continue
        if opportunity.application_fee_usd > artist.budget_cap_usd:
            continue
        days_until_deadline = (opportunity.deadline_date() - reference_day).days
        if days_until_deadline < artist.minimum_days_until_deadline:
            continue
        if _requires_verification(opportunity):
            continue
        filtered.append(opportunity)

    return filtered


def score_opportunity(
    artist: ArtistProfile,
    opportunity: Opportunity,
    weights: ScoringWeights | None = None,
    today: date | None = None,
) -> ScoredOpportunity:
    scoring = weights or ScoringWeights()
    reference_day = today or date.fromisoformat(DEFAULT_REFERENCE_DATE)

    medium_fit = scoring.medium_fit if _medium_supported(opportunity) else 0
    style_theme_fit = _match_ratio(artist.themes, opportunity.theme_signals) * scoring.style_theme_fit
    budget_fit = _budget_score(artist.budget_cap_usd, opportunity.application_fee_usd) * scoring.budget_fit
    deadline_fit = _deadline_score(reference_day, artist.minimum_days_until_deadline, opportunity) * scoring.deadline_fit
    career_goal_fit = _career_goal_score(artist.career_goal, opportunity.career_value_signals) * scoring.career_goal_fit
    eligibility_fit = _eligibility_score(artist, opportunity) * scoring.eligibility_fit
    source_quality_fit = _source_quality_score(opportunity) * scoring.source_quality_fit

    breakdown = {
        "medium_fit": round(medium_fit, 2),
        "style_theme_fit": round(style_theme_fit, 2),
        "budget_fit": round(budget_fit, 2),
        "deadline_fit": round(deadline_fit, 2),
        "career_goal_fit": round(career_goal_fit, 2),
        "eligibility_fit": round(eligibility_fit, 2),
        "source_quality_fit": round(source_quality_fit, 2),
    }
    total_score = round(sum(breakdown.values()), 2)

    caution = _build_caution_note(artist, opportunity)
    return ScoredOpportunity(
        opportunity=opportunity,
        total_score=total_score,
        score_breakdown=breakdown,
        caution_note=caution,
    )


def rank_opportunities(
    artist: ArtistProfile,
    opportunities: list[Opportunity],
    top_k: int,
    weights: ScoringWeights | None = None,
    today: date | None = None,
) -> list[ScoredOpportunity]:
    eligible = filter_opportunities(artist, opportunities, today=today)
    scored = [
        score_opportunity(artist, opportunity, weights=weights, today=today)
        for opportunity in eligible
    ]
    ranked = sorted(
        scored,
        key=lambda item: (
            -item.total_score,
            item.opportunity.deadline,
            item.opportunity.application_fee_usd,
        ),
    )
    return ranked[:top_k]


def _medium_supported(opportunity: Opportunity) -> bool:
    media = {value.lower() for value in opportunity.accepted_media}
    return bool({"painting", "visual arts", "2d", "mixed media"} & media)


def _requires_verification(opportunity: Opportunity) -> bool:
    return (
        opportunity.source_type in {"discovery_social", "discovery_editorial"}
        and opportunity.verification_status != "verified"
    )


def _match_ratio(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_set = {item.lower() for item in left}
    right_set = {item.lower() for item in right}
    overlap = len(left_set & right_set)
    return min(1.0, overlap / max(1, min(len(left_set), len(right_set))))


def _budget_score(budget_cap: float, fee: float) -> float:
    if fee <= 0:
        return 1.0
    ratio = fee / max(1.0, budget_cap)
    if ratio <= 0.25:
        return 1.0
    if ratio <= 0.6:
        return 0.85
    if ratio <= 0.8:
        return 0.6
    return 0.35


def _deadline_score(reference_day: date, minimum_days: int, opportunity: Opportunity) -> float:
    days_until = (opportunity.deadline_date() - reference_day).days
    if days_until < minimum_days:
        return 0.0
    if days_until <= 14:
        return 1.0
    if days_until <= 30:
        return 0.85
    if days_until <= 60:
        return 0.65
    return 0.45


def _career_goal_score(goal: str, signals: list[str]) -> float:
    goal_phrases = _goal_phrases(goal)
    normalized_signals = [_normalize_text(signal) for signal in signals if signal.strip()]
    if not goal_phrases or not normalized_signals:
        return 0.0
    phrase_scores = [_best_goal_phrase_match(phrase, normalized_signals) for phrase in goal_phrases]
    return round(sum(phrase_scores) / len(phrase_scores), 2)


def _goal_phrases(goal: str) -> list[str]:
    normalized_goal = _normalize_text(goal)
    return [phrase.strip() for phrase in re.split(r"\band\b|,", normalized_goal) if phrase.strip()]


def _best_goal_phrase_match(goal_phrase: str, normalized_signals: list[str]) -> float:
    phrase_tokens = set(goal_phrase.split())
    if not phrase_tokens:
        return 0.0

    best_match = 0.0
    for signal in normalized_signals:
        if goal_phrase in signal:
            return 1.0

        signal_tokens = set(signal.split())
        overlap = len(phrase_tokens & signal_tokens)
        if overlap:
            best_match = max(best_match, overlap / len(phrase_tokens))

    return best_match


def _normalize_text(value: str) -> str:
    lowered = value.lower().replace("/", " ")
    normalized = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    return " ".join(normalized.split())


def _eligibility_score(artist: ArtistProfile, opportunity: Opportunity) -> float:
    region_overlap = bool(
        set(item.lower() for item in artist.eligible_regions)
        & set(item.lower() for item in opportunity.eligibility.regions)
    )
    stage_match = (
        artist.career_stage.lower() in {item.lower() for item in opportunity.eligibility.career_stages}
        or "all" in {item.lower() for item in opportunity.eligibility.career_stages}
    )
    if region_overlap and stage_match:
        return 1.0
    if region_overlap or stage_match:
        return 0.6
    return 0.2


def _source_quality_score(opportunity: Opportunity) -> float:
    confidence_bonus = {"high": 1.0, "medium": 0.75, "low": 0.4}[opportunity.confidence_level]
    quality_bonus = opportunity.quality_score / 5
    return round((confidence_bonus + quality_bonus) / 2, 2)


def _build_caution_note(artist: ArtistProfile, opportunity: Opportunity) -> str:
    cautions: list[str] = []
    if opportunity.application_fee_usd > artist.budget_cap_usd * 0.6:
        cautions.append("Fee is near the stated budget cap.")
    goal_match = _career_goal_score(artist.career_goal, opportunity.career_value_signals)
    if goal_match < 0.7:
        cautions.append("Career-goal alignment is weaker than the top matches.")
    if not cautions:
        return "No major cautions."
    return " ".join(cautions)
