#!/usr/bin/env python3
"""
Pull Mailchimp audience contacts into data/mvp/submissions.csv for Codex matching.

Requires in .env (or environment):
  MAILCHIMP_API_KEY   e.g. xxxxx-us15  (Audience → API keys)
  MAILCHIMP_LIST_ID   e.g. 8204d55dea  (from your subscribe form URL id=...)

Usage:
  python scripts/sync_mailchimp.py
  python scripts/sync_mailchimp.py --status subscribed --only-new
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "mvp" / "submissions.csv"

CSV_COLUMNS = [
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


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def mailchimp_dc(api_key: str) -> str:
    if "-" not in api_key:
        raise ValueError("MAILCHIMP_API_KEY must look like xxxxx-us15")
    return api_key.rsplit("-", 1)[-1]


def mailchimp_request(api_key: str, path: str, query: dict | None = None) -> dict:
    dc = mailchimp_dc(api_key)
    url = f"https://{dc}.api.mailchimp.com/3.0{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    token = base64.b64encode(f"anystring:{api_key}".encode()).decode()
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mailchimp API {exc.code}: {body}") from exc


def fetch_all_members(api_key: str, list_id: str, status: str) -> list[dict]:
    members: list[dict] = []
    offset = 0
    page_size = 100

    while True:
        payload = mailchimp_request(
            api_key,
            f"/lists/{list_id}/members",
            {
                "count": page_size,
                "offset": offset,
                "status": status,
            },
        )
        batch = payload.get("members", [])
        members.extend(batch)
        total = int(payload.get("total_items", len(members)))
        offset += len(batch)
        if offset >= total or not batch:
            break

    return members


def merge_get(merge_fields: dict, *keys: str) -> str:
    for key in keys:
        value = merge_fields.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def slug_email(email: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-")
    return slug[:48] or "contact"


def _has_material_update(prev: dict[str, str], incoming: dict[str, str]) -> bool:
    tracked_fields = [
        "submitted_at",
        "full_name",
        "career_stage",
        "primary_medium",
        "budget_cap_usd",
        "minimum_days_until_deadline",
        "style_description",
    ]
    for field in tracked_fields:
        if (prev.get(field, "") or "").strip() != (incoming.get(field, "") or "").strip():
            return True
    return False


def member_to_row(member: dict, existing: dict[str, dict] | None) -> dict[str, str]:
    merge = member.get("merge_fields") or {}
    email = (member.get("email_address") or "").strip().lower()
    fname = merge_get(merge, "FNAME")
    lname = merge_get(merge, "LNAME")
    full_name = merge_get(merge, "MMERGE8", "MERGE8") or " ".join(
        part for part in [fname, lname] if part
    ).strip()

    timestamp = member.get("timestamp_signup") or member.get("last_changed") or ""
    submitted_at = timestamp.replace("Z", "+00:00") if timestamp else datetime.now(timezone.utc).isoformat()

    prev = (existing or {}).get(email, {})
    submission_id = prev.get("submission_id") or f"mc_{slug_email(email)}"
    candidate_row = {
        "submission_id": submission_id,
        "submitted_at": submitted_at,
        "status": prev.get("status") or "research_pending",
        "full_name": full_name,
        "email": email,
        "career_stage": merge_get(merge, "MMERGE7", "MERGE7"),
        "primary_medium": merge_get(merge, "MMERGE9", "MERGE9"),
        "medium_expansion": prev.get("medium_expansion", ""),
        "budget_cap_usd": merge_get(merge, "MMERGE10", "MERGE10"),
        "eligible_region": prev.get("eligible_region", ""),
        "minimum_days_until_deadline": merge_get(merge, "MMERGE11", "MERGE11"),
        "opportunity_types": prev.get("opportunity_types", ""),
        "location_preference": prev.get("location_preference", ""),
        "lead_source_scope": prev.get("lead_source_scope", ""),
        "style_description": merge_get(merge, "MMERGE12", "MERGE12"),
        "themes": prev.get("themes", ""),
        "career_goal": prev.get("career_goal", ""),
        "target_visibility": prev.get("target_visibility", ""),
        "preferred_contexts": prev.get("preferred_contexts", ""),
        "competitiveness_tolerance": prev.get("competitiveness_tolerance", ""),
        "artist_website": prev.get("artist_website", ""),
        "instagram": prev.get("instagram", ""),
        "artwork_links": prev.get("artwork_links", ""),
        "notes_for_match": prev.get("notes_for_match", "Imported from Mailchimp"),
        "research_brief": prev.get("research_brief", ""),
        "research_brief_path": prev.get("research_brief_path", ""),
        "processed_at": prev.get("processed_at") or "",
        "initial_email_sent_at": prev.get("initial_email_sent_at", ""),
        "last_followup_sent_at": prev.get("last_followup_sent_at", ""),
    }

    if not prev or _has_material_update(prev, candidate_row):
        candidate_row["status"] = "research_pending"
        candidate_row["processed_at"] = ""

    return candidate_row


def read_existing_csv(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        (row.get("email") or "").strip().lower(): row
        for row in rows
        if (row.get("email") or "").strip()
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Mailchimp contacts to submissions.csv")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--status",
        default="subscribed",
        choices=["subscribed", "unsubscribed", "cleaned", "pending", "transactional"],
        help="Mailchimp member status filter",
    )
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="Only list rows with status=research_pending and empty processed_at after sync",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("MAILCHIMP_API_KEY", "").strip()
    list_id = os.getenv("MAILCHIMP_LIST_ID", "").strip() or "8204d55dea"

    if not api_key:
        print(
            "Missing MAILCHIMP_API_KEY. Add it to .env — Mailchimp → Profile → Extras → API keys.",
            file=sys.stderr,
        )
        return 1

    existing = read_existing_csv(args.output)
    members = fetch_all_members(api_key, list_id, args.status)
    rows = [member_to_row(member, existing) for member in members if member.get("email_address")]
    rows.sort(key=lambda row: row.get("submitted_at", ""), reverse=True)
    write_csv(args.output, rows)

    new_count = sum(
        1
        for row in rows
        if row.get("status") == "research_pending" and not row.get("processed_at")
    )
    print(f"Wrote {len(rows)} contact(s) to {args.output}")
    print(f"Queued for detailed review (status=research_pending, not processed): {new_count}")

    if args.only_new and new_count:
        print("\nQueued contacts:")
        for row in rows:
            if row.get("status") == "research_pending" and not row.get("processed_at"):
                print(f"  - {row.get('full_name')} <{row.get('email')}>")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
