from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    medium_fit: int = 30
    style_theme_fit: int = 20
    budget_fit: int = 15
    deadline_fit: int = 10
    career_goal_fit: int = 10
    eligibility_fit: int = 10
    source_quality_fit: int = 5


DEFAULT_TOP_K = 10
DEFAULT_DATA_DIR = "data/seed"
DEFAULT_REFERENCE_DATE = "2026-03-29"
