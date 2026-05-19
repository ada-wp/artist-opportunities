#!/usr/bin/env python3
"""
Run the operator intake prep in one step:
1. Sync Mailchimp contacts into submissions.csv
2. Generate research brief files for all research_pending rows

Usage:
  python scripts/sync_mailchimp_and_generate_briefs.py
  python scripts/sync_mailchimp_and_generate_briefs.py --status subscribed --only-new
  python scripts/sync_mailchimp_and_generate_briefs.py --all-with-medium
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(args: list[str]) -> int:
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Mailchimp contacts and generate research brief files in one command"
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
        help="Pass --only-new to Mailchimp sync before generating briefs",
    )
    parser.add_argument(
        "--all-with-medium",
        action="store_true",
        help="Generate briefs for every submission row with a primary_medium value",
    )
    args = parser.parse_args()

    sync_args = ["scripts/sync_mailchimp.py", "--status", args.status]
    if args.only_new:
        sync_args.append("--only-new")

    print("== Syncing Mailchimp into submissions.csv ==")
    sync_code = run_step(sync_args)
    if sync_code != 0:
        return sync_code

    print("\n== Generating research briefs for research_pending submissions ==")
    brief_args = ["scripts/generate_research_brief.py"]
    if args.all_with_medium:
        brief_args.append("--all-with-medium")
    return run_step(brief_args)


if __name__ == "__main__":
    raise SystemExit(main())
