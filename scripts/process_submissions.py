#!/usr/bin/env python3
"""
Process research-complete submissions from data/mvp/submissions.csv against
data/mvp/opportunities.csv.

Rules:
- only process rows where status=research_complete, processed_at is empty,
  and primary_medium is non-empty
- write/update a row in data/mvp/results.csv
- stamp processed_at and set status=emailed_ready after processing

Usage:
  py scripts/process_submissions.py
  py scripts/process_submissions.py --only submission_id
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_CSV = ROOT / "data" / "mvp" / "submissions.csv"
OPPORTUNITIES_CSV = ROOT / "data" / "mvp" / "opportunities.csv"
RESULTS_CSV = ROOT / "data" / "mvp" / "results.csv"

RESULT_COLUMNS = [
    "result_id",
    "submission_id",
    "artist_name",
    "email",
    "generated_at",
    "candidate_count",
    "final_pick_1",
    "final_pick_1_why",
    "final_pick_1_caution",
    "final_pick_1_apply_url",
    "final_pick_2",
    "final_pick_2_why",
    "final_pick_2_caution",
    "final_pick_2_apply_url",
    "final_pick_3",
    "final_pick_3_why",
    "final_pick_3_caution",
    "final_pick_3_apply_url",
    "general_suggestions",
    "email_subject",
    "email_body",
    "sent_at",
]


@dataclass(frozen=True)
class RankedOpportunity:
    row: dict[str, str]
    score: int
    why: str
    caution: str


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_multi(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in re.split(r"[|,;\n]+", value) if part.strip()]


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_deadline(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def region_match(submission_region: str, opportunity_region: str) -> bool:
    sub = submission_region.strip().lower()
    opp = opportunity_region.strip().lower()
    if not sub or not opp:
        return True
    if sub == "us only":
        return any(token in opp for token in ["us", "u.s.", "north america", "international"])
    if sub == "us and international":
        return True
    if sub == "international":
        return "international" in opp
    if sub == "regional only":
        return any(token in opp for token in ["regional", "state"])
    return True


def medium_match(primary_medium: str, accepted_media: str) -> tuple[bool, int]:
    medium = primary_medium.strip().lower()
    haystack = accepted_media.strip().lower()
    if not medium or not haystack:
        return False, 0
    if medium in haystack:
        return True, 40
    if any(token in medium for token in ["watercolor", "watercolour", "gouache", "acrylic", "pastel"]):
        if any(token in haystack for token in ["painting", "mixed media", "all visual arts", "2d", "visual arts"]):
            return True, 32
    if "oil" in medium and "painting" in haystack:
        return True, 34
    if "painting" in medium and any(token in haystack for token in ["painting", "drawing", "mixed media", "visual arts"]):
        return True, 30
    if "drawing" in medium and any(token in haystack for token in ["drawing", "painting", "visual arts"]):
        return True, 28
    if any(token in haystack for token in ["all visual arts", "visual arts"]):
        return True, 20
    return False, 0


def score_opportunity(submission: dict[str, str], opportunity: dict[str, str], today: date) -> RankedOpportunity | None:
    medium_ok, score = medium_match(
        submission.get("primary_medium", ""),
        opportunity.get("accepted_media", ""),
    )
    if not medium_ok:
        return None

    budget_cap = parse_float(submission.get("budget_cap_usd", ""), 0.0)
    fee = parse_float(opportunity.get("application_fee_usd", ""), 0.0)
    if budget_cap and fee > budget_cap:
        return None
    if fee <= budget_cap:
        score += 15

    deadline = parse_deadline(opportunity.get("deadline", ""))
    minimum_days = parse_int(submission.get("minimum_days_until_deadline", ""), 10)
    if deadline is None:
        return None
    days_until = (deadline - today).days
    if days_until < minimum_days:
        return None
    score += 10

    if not region_match(submission.get("eligible_region", ""), opportunity.get("eligible_regions", "")):
        return None
    score += 10

    goals = {value.lower() for value in split_multi(submission.get("career_goal", ""))}
    career_tags = {value.lower() for value in split_multi(opportunity.get("career_value_tags", ""))}
    goal_overlap = goals & career_tags
    if goal_overlap:
        score += 12

    style_text = " ".join(
        [
            submission.get("style_description", ""),
            submission.get("themes", ""),
            submission.get("notes_for_match", ""),
        ]
    ).lower()
    style_tags = split_multi(opportunity.get("style_tags", ""))
    theme_tags = split_multi(opportunity.get("theme_tags", ""))
    style_hits = [tag for tag in style_tags + theme_tags if tag.lower() in style_text]
    score += min(len(style_hits) * 4, 12)

    strategic_value = opportunity.get("strategic_value", "").strip().lower()
    if strategic_value == "high":
        score += 8
    elif strategic_value == "medium":
        score += 4

    organizer_quality = opportunity.get("organizer_quality", "").strip().lower()
    if organizer_quality == "strong":
        score += 8
    elif organizer_quality == "mixed":
        score += 3

    medium_label = submission.get("primary_medium", "your medium")
    why_parts = [
        f"Strong medium fit for {medium_label}",
        (
            f"the fee is within your ${int(budget_cap) if budget_cap.is_integer() else budget_cap} budget"
            if budget_cap
            else "the fee is within budget"
        ),
        f"the deadline gives you {days_until} days to prepare",
    ]
    if goal_overlap:
        why_parts.append(f"it supports goals like {', '.join(sorted(goal_overlap))}")
    if style_hits:
        why_parts.append(f"it connects with style signals like {', '.join(style_hits[:3])}")
    if strategic_value:
        why_parts.append(f"its strategic value is marked {strategic_value}")

    caution = opportunity.get("red_flags", "").strip() or "Recheck the official page before applying."
    return RankedOpportunity(row=opportunity, score=score, why=". ".join(why_parts) + ".", caution=caution)


def build_email_body(submission: dict[str, str], ranked: list[RankedOpportunity], generated_at: str) -> str:
    lines = [
        f"Hi {submission.get('full_name', 'there')},",
        "",
        "Here are your current top opportunity matches based on your medium, budget, timing, and stated goals.",
        "",
        f"Generated on: {generated_at}",
        "",
    ]
    if not ranked:
        lines.extend(
            [
                "I did not find a current strong match in the vetted pool for your criteria.",
                "Try widening your budget, timeline, or medium range and resubmit.",
            ]
        )
        return "\n".join(lines)

    for index, item in enumerate(ranked[:3], start=1):
        lines.extend(
            [
                f"{index}. {item.row.get('title', '')}",
                f"Organizer: {item.row.get('organizer', '')}",
                f"Deadline: {item.row.get('deadline', '')}",
                f"Why I chose it: {item.why}",
                f"Caution: {item.caution}",
                f"Apply: {item.row.get('application_url', '')}",
                "",
            ]
        )

    lines.extend(
        [
            "Suggestions:",
            "- Prioritize the strongest gallery-context option first.",
            "- Recheck deadlines, fees, and eligibility on the official page before applying.",
            "- Use your strongest representative images and tailor your statement to the venue.",
        ]
    )
    return "\n".join(lines)


def build_email_html(submission: dict[str, str], ranked: list[RankedOpportunity], generated_at: str) -> str:
    artist_name = submission.get("full_name", "there")
    if not ranked:
        body = (
            "<p>I did not find a current strong match in the vetted pool for your criteria.</p>"
            "<p>Try widening your budget, timeline, or medium range and resubmit.</p>"
        )
    else:
        cards: list[str] = []
        for index, item in enumerate(ranked[:3], start=1):
            cards.append(
                "<article style='margin:0 0 18px;padding:16px;border:1px solid #ddd;border-radius:12px;'>"
                f"<h3 style='margin:0 0 8px;'>{index}. {item.row.get('title', '')}</h3>"
                f"<p style='margin:0 0 6px;'><strong>Organizer:</strong> {item.row.get('organizer', '')}</p>"
                f"<p style='margin:0 0 6px;'><strong>Deadline:</strong> {item.row.get('deadline', '')}</p>"
                f"<p style='margin:0 0 6px;'><strong>Why I chose it:</strong> {item.why}</p>"
                f"<p style='margin:0 0 6px;'><strong>Caution:</strong> {item.caution}</p>"
                f"<p style='margin:0;'><a href='{item.row.get('application_url', '')}'>View application</a></p>"
                "</article>"
            )
        body = "".join(cards)

    return (
        "<div style='font-family:Arial,sans-serif;color:#1f1a17;line-height:1.55;max-width:700px;'>"
        f"<p>Hi {artist_name},</p>"
        "<p>Here are your current top opportunity matches based on your medium, budget, timing, and stated goals.</p>"
        f"<p><strong>Generated on:</strong> {generated_at}</p>"
        f"{body}"
        "<p><strong>Suggestions</strong></p>"
        "<ul>"
        "<li>Prioritize the strongest gallery-context option first.</li>"
        "<li>Recheck deadlines, fees, and eligibility on the official page before applying.</li>"
        "<li>Use your strongest representative images and tailor your statement to the venue.</li>"
        "</ul>"
        "</div>"
    )


def process_submission(
    submission: dict[str, str],
    opportunities: list[dict[str, str]],
    today: date,
) -> dict[str, str]:
    ranked = []
    for opportunity in opportunities:
        if opportunity.get("is_live", "").strip().upper() not in {"TRUE", "YES", "1"}:
            continue
        scored = score_opportunity(submission, opportunity, today)
        if scored is not None:
            ranked.append(scored)
    ranked.sort(key=lambda item: (-item.score, item.row.get("deadline", ""), item.row.get("title", "")))

    generated_at = datetime.now().isoformat(timespec="seconds")
    top = ranked[:3]
    email_body = build_email_body(submission, top, generated_at)
    email_html = build_email_html(submission, top, generated_at)

    result = {
        "result_id": f"result_{submission.get('submission_id', '')}",
        "submission_id": submission.get("submission_id", ""),
        "artist_name": submission.get("full_name", ""),
        "email": submission.get("email", ""),
        "generated_at": generated_at,
        "candidate_count": str(len(ranked)),
        "final_pick_1": top[0].row.get("title", "") if len(top) > 0 else "",
        "final_pick_1_why": top[0].why if len(top) > 0 else "",
        "final_pick_1_caution": top[0].caution if len(top) > 0 else "",
        "final_pick_1_apply_url": top[0].row.get("application_url", "") if len(top) > 0 else "",
        "final_pick_2": top[1].row.get("title", "") if len(top) > 1 else "",
        "final_pick_2_why": top[1].why if len(top) > 1 else "",
        "final_pick_2_caution": top[1].caution if len(top) > 1 else "",
        "final_pick_2_apply_url": top[1].row.get("application_url", "") if len(top) > 1 else "",
        "final_pick_3": top[2].row.get("title", "") if len(top) > 2 else "",
        "final_pick_3_why": top[2].why if len(top) > 2 else "",
        "final_pick_3_caution": top[2].caution if len(top) > 2 else "",
        "final_pick_3_apply_url": top[2].row.get("application_url", "") if len(top) > 2 else "",
        "general_suggestions": (
            "Prioritize the strongest gallery-context option first. Recheck each official page before applying."
        ),
        "email_subject": f"Your artist opportunity shortlist - {submission.get('full_name', 'Artist')}",
        "email_body": email_body,
        "sent_at": "",
    }
    result["_email_html"] = email_html
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Process new submission rows into results.csv")
    parser.add_argument("--only", help="Only process a specific submission_id")
    args = parser.parse_args()

    submissions = read_csv(SUBMISSIONS_CSV)
    opportunities = read_csv(OPPORTUNITIES_CSV)
    results = read_csv(RESULTS_CSV)
    results_by_submission = {
        row.get("submission_id", ""): row for row in results if row.get("submission_id", "")
    }

    today = date.today()
    processed_count = 0
    for submission in submissions:
        if args.only and submission.get("submission_id") != args.only:
            continue
        if submission.get("status", "").strip().lower() != "research_complete":
            continue
        if submission.get("processed_at", "").strip():
            continue
        if not submission.get("primary_medium", "").strip():
            continue

        result_row = process_submission(submission, opportunities, today)
        results_by_submission[submission["submission_id"]] = result_row
        submission["status"] = "emailed_ready"
        submission["processed_at"] = datetime.now().isoformat(timespec="seconds")
        picks = [result_row.get("final_pick_1", ""), result_row.get("final_pick_2", ""), result_row.get("final_pick_3", "")]
        picks = [pick for pick in picks if pick]
        print(f"Processed {submission.get('full_name', '')} <{submission.get('email', '')}>")
        for index, pick in enumerate(picks, start=1):
            reason = result_row.get(f"final_pick_{index}_why", "")
            print(f"  {index}. {pick}")
            print(f"     Why: {reason}")
        processed_count += 1

    ordered_results = []
    for row in results_by_submission.values():
        if "_email_html" in row:
            row = {key: value for key, value in row.items() if key != "_email_html"}
        ordered_results.append(row)
    ordered_results.sort(key=lambda row: row.get("generated_at", ""), reverse=True)
    write_csv(SUBMISSIONS_CSV, list(submissions[0].keys()) if submissions else [], submissions)
    write_csv(RESULTS_CSV, RESULT_COLUMNS, ordered_results)

    print(f"Processed {processed_count} research-complete submission(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
