from __future__ import annotations

import os
from datetime import date

from .config import DEFAULT_DATA_DIR, DEFAULT_REFERENCE_DATE
from .email_delivery import send_intake_results_email
from .intake import IntakeSubmission, parse_intake_payload
from .recommend import recommend_from_intake


def process_intake_submission(
    payload: dict[str, object],
    *,
    send_email: bool = True,
    today: date | None = None,
) -> dict[str, object]:
    submission = parse_intake_payload(payload)
    top_k = int(os.getenv("INTAKE_TOP_K", "5"))
    data_dir = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)
    reference_day = today or date.fromisoformat(
        os.getenv("REFERENCE_DATE", DEFAULT_REFERENCE_DATE)
    )

    recommendations = recommend_from_intake(
        submission,
        data_dir=data_dir,
        top_k=top_k,
        today=reference_day,
    )

    email_result: dict[str, object] | None = None
    email_error: str | None = None
    if send_email:
        try:
            email_result = send_intake_results_email(recommendations)
        except Exception as exc:  # noqa: BLE001 - surface delivery issues to caller
            email_error = str(exc)

    return {
        "status": "ok",
        "submission_id": recommendations["artist_id"],
        "match_count": len(recommendations.get("top_recommendations", [])),
        "recommendations": recommendations,
        "email_sent": email_result is not None,
        "email_result": email_result,
        "email_error": email_error,
    }


def dry_run_intake(payload: dict[str, object]) -> tuple[IntakeSubmission, dict[str, object]]:
    submission = parse_intake_payload(payload)
    top_k = int(os.getenv("INTAKE_TOP_K", "5"))
    data_dir = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)
    recommendations = recommend_from_intake(
        submission,
        data_dir=data_dir,
        top_k=top_k,
    )
    return submission, recommendations
