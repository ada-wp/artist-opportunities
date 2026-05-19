#!/usr/bin/env python3
"""
Generate concise live-research brief files for research_pending submissions.

This is the operator-facing bridge between:
- automated intake/sync/queueing
and
- Codex-assisted live discovery and review

Usage:
  py scripts/generate_research_brief.py
  py scripts/generate_research_brief.py --only <submission_id>
  py scripts/generate_research_brief.py --all-with-medium
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_CSV = ROOT / "data" / "mvp" / "submissions.csv"
BRIEFS_DIR = ROOT / "data" / "mvp" / "research_briefs"
SUBMISSION_COLUMNS = [
    "submission_id",
    "submitted_at",
    "status",
    "full_name",
    "email",
    "career_stage",
    "primary_medium",
    "medium_expansion",
    "budget_cap_usd",
    "eligible_region",
    "minimum_days_until_deadline",
    "opportunity_types",
    "location_preference",
    "lead_source_scope",
    "style_description",
    "themes",
    "career_goal",
    "target_visibility",
    "preferred_contexts",
    "competitiveness_tolerance",
    "artist_website",
    "instagram",
    "artwork_links",
    "notes_for_match",
    "research_brief",
    "research_brief_path",
    "processed_at",
    "initial_email_sent_at",
    "last_followup_sent_at",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_submission_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in rows:
        clean_row = {column: (row.get(column, "") or "") for column in SUBMISSION_COLUMNS}
        normalized.append(clean_row)
    return normalized


def build_brief(row: dict[str, str]) -> str:
    parts = [
        f"Submission ID: {row.get('submission_id', '')}",
        f"Artist: {row.get('full_name', '')}",
        f"Email: {row.get('email', '')}",
        f"Career stage: {row.get('career_stage', '') or 'not provided'}",
        f"Primary medium: {row.get('primary_medium', '') or 'not provided'}",
        f"Budget cap: {row.get('budget_cap_usd', '') or 'not provided'}",
        f"Eligible region: {row.get('eligible_region', '') or 'not provided'}",
        f"Minimum days before deadline: {row.get('minimum_days_until_deadline', '') or 'not provided'}",
        f"Style description: {row.get('style_description', '') or 'not provided'}",
        f"Themes: {row.get('themes', '') or 'not provided'}",
        f"Career goal: {row.get('career_goal', '') or 'not provided'}",
        f"Notes: {row.get('notes_for_match', '') or 'not provided'}",
        "",
        "Research task:",
        "1. Search current live public sources: NYFA, CaFE, ArtDeadline.",
        "2. Use the artist criteria as hard filters first.",
        "3. Collect all plausible candidates.",
        "4. Verify each surviving candidate on the official page.",
        "5. Review the organizer/gallery context.",
        "6. Assess fit and rank the final top 3.",
        "7. Write results back into the stage CSVs and final results.csv.",
        "",
        "Important:",
        "- Discovery should be live and source-aware, not just cache-based.",
        "- Do not trust snippets alone; verify deadlines, fees, eligibility, and application URL.",
        "- If too few strong results survive, mark the row needs_review instead of forcing a weak email.",
    ]
    return "\n".join(parts)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "unknown"

def brief_path_for_row(row: dict[str, str], duplicate_index: int = 1) -> Path:
    submission_id = slugify(row.get("submission_id", "unknown_submission"))
    artist_name = slugify(row.get("full_name", "unknown_artist"))
    suffix = f"-{duplicate_index}" if duplicate_index > 1 else ""
    return BRIEFS_DIR / f"{submission_id}__{artist_name}{suffix}.md"


def write_brief_file(row: dict[str, str], duplicate_index: int = 1) -> Path:
    path = brief_path_for_row(row, duplicate_index=duplicate_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_brief(row) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a live-research brief for one queued submission")
    parser.add_argument("--only", help="submission_id to brief")
    parser.add_argument(
        "--all-with-medium",
        action="store_true",
        help="Generate briefs for all rows where primary_medium has a value",
    )
    args = parser.parse_args()

    rows = read_rows(SUBMISSIONS_CSV)
    rows = normalize_submission_rows(rows)
    if args.only:
        match_count = 0
        for row in rows:
            if row.get("submission_id") == args.only:
                match_count += 1
                row["research_brief"] = build_brief(row)
                path = write_brief_file(row, duplicate_index=match_count)
                row["research_brief_path"] = str(path.relative_to(ROOT))
                print(f"Wrote brief: {path}")
                print()
                print(build_brief(row))
                if match_count > 1:
                    print("\n---\n")
        if match_count:
            write_rows(SUBMISSIONS_CSV, SUBMISSION_COLUMNS, rows)
            return 0
        raise SystemExit(f"Unknown submission_id: {args.only}")

    if args.all_with_medium:
        target_rows = [row for row in rows if row.get("primary_medium", "").strip()]
        empty_message = "No submissions with a primary_medium value found."
    else:
        target_rows = [row for row in rows if row.get("status", "").strip().lower() == "research_pending"]
        empty_message = "No research_pending submissions found."

    if not target_rows:
        print(empty_message)
        return 0

    seen_counts: dict[str, int] = {}
    for index, row in enumerate(target_rows, start=1):
        submission_id = row.get("submission_id", "")
        seen_counts[submission_id] = seen_counts.get(submission_id, 0) + 1
        row["research_brief"] = build_brief(row)
        path = write_brief_file(row, duplicate_index=seen_counts[submission_id])
        row["research_brief_path"] = str(path.relative_to(ROOT))
        print(f"Wrote brief: {path}")
        print()
        print(build_brief(row))
        if index < len(target_rows):
            print("\n---\n")
    write_rows(SUBMISSIONS_CSV, SUBMISSION_COLUMNS, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
