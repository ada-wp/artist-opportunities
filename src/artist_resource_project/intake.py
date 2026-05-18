from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from .models import ArtistProfile


@dataclass(frozen=True)
class IntakeSubmission:
    name: str
    email: str
    primary_medium: str
    style_description: str
    themes: list[str]
    budget_cap_usd: float
    minimum_days_until_deadline: int
    career_goal: str
    eligible_regions: list[str]
    career_stage: str
    geographic_preferences: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        if not self.email.strip() or "@" not in self.email:
            raise ValueError("email must be a valid address")
        if not self.primary_medium.strip():
            raise ValueError("primary_medium is required")
        if not self.style_description.strip():
            raise ValueError("style_description is required")
        if not self.themes:
            raise ValueError("themes must contain at least one value")
        if self.budget_cap_usd < 0:
            raise ValueError("budget_cap_usd must be non-negative")
        if self.minimum_days_until_deadline < 0:
            raise ValueError("minimum_days_until_deadline must be non-negative")
        if not self.career_goal.strip():
            raise ValueError("career_goal is required")
        if not self.eligible_regions:
            raise ValueError("eligible_regions must contain at least one region")
        if not self.career_stage.strip():
            raise ValueError("career_stage is required")


def parse_intake_payload(payload: dict[str, object]) -> IntakeSubmission:
    """Normalize a webhook/JSON body from Framer, Make, or a custom form."""
    data = _flatten_payload(payload)
    return IntakeSubmission(
        name=_require_str(data, "name"),
        email=_require_str(data, "email"),
        primary_medium=_require_str(data, "primary_medium", "medium", "medium_preferences"),
        style_description=_require_str(data, "style_description", "style", "practice_description"),
        themes=_parse_list(data, "themes", "theme", "theme_tags"),
        budget_cap_usd=_parse_float(data, "budget_cap_usd", "budget", "budget_cap"),
        minimum_days_until_deadline=_parse_int(
            data,
            "minimum_days_until_deadline",
            "min_days_until_deadline",
            "minimum_days",
        ),
        career_goal=_require_str(data, "career_goal", "goals", "career_goals"),
        eligible_regions=_parse_list(data, "eligible_regions", "regions", "region"),
        career_stage=_require_str(data, "career_stage", "stage"),
        geographic_preferences=_parse_list(
            data,
            "geographic_preferences",
            "location_preferences",
            "locations",
            required=False,
        ),
    )


def intake_to_artist_profile(submission: IntakeSubmission) -> ArtistProfile:
    slug = re.sub(r"[^a-z0-9]+", "-", submission.email.lower()).strip("-")[:40]
    artist_id = f"intake_{slug}_{uuid.uuid4().hex[:8]}"
    return ArtistProfile(
        id=artist_id,
        name=submission.name.strip(),
        primary_medium=submission.primary_medium.strip(),
        style_description=submission.style_description.strip(),
        themes=[theme.strip() for theme in submission.themes if theme.strip()],
        budget_cap_usd=submission.budget_cap_usd,
        minimum_days_until_deadline=submission.minimum_days_until_deadline,
        career_goal=submission.career_goal.strip(),
        eligible_regions=[region.strip() for region in submission.eligible_regions if region.strip()],
        career_stage=submission.career_stage.strip(),
        geographic_preferences=[
            value.strip() for value in submission.geographic_preferences if value.strip()
        ],
    )


def _flatten_payload(payload: dict[str, object]) -> dict[str, object]:
    if "data" in payload and isinstance(payload["data"], dict):
        merged = {**payload, **payload["data"]}  # type: ignore[arg-type]
        merged.pop("data", None)
        return merged
    return payload


def _require_str(data: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError(f"Missing required field: one of {', '.join(keys)}")


def _parse_list(data: dict[str, object], *keys: str, required: bool = True) -> list[str]:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                return items
        if isinstance(value, str) and value.strip():
            return [part.strip() for part in re.split(r"[,;|\n]+", value) if part.strip()]
    if required:
        raise ValueError(f"Missing required list field: one of {', '.join(keys)}")
    return []


def _parse_float(data: dict[str, object], *keys: str) -> float:
    for key in keys:
        value = data.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid number for {key}") from exc
    raise ValueError(f"Missing required number field: one of {', '.join(keys)}")


def _parse_int(data: dict[str, object], *keys: str) -> int:
    for key in keys:
        value = data.get(key)
        if value is None or value == "":
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid integer for {key}") from exc
    raise ValueError(f"Missing required integer field: one of {', '.join(keys)}")
