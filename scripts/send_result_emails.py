#!/usr/bin/env python3
"""
Send unsent result emails from data/mvp/results.csv.

Requires either:
  RESEND_API_KEY + EMAIL_FROM
or:
  SMTP_HOST + SMTP_PORT + SMTP_USERNAME + SMTP_PASSWORD + EMAIL_FROM

Optional:
  ADMIN_EMAIL
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import smtplib
from email.message import EmailMessage
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RESULTS_CSV = ROOT / "data" / "mvp" / "results.csv"
SUBMISSIONS_CSV = ROOT / "data" / "mvp" / "submissions.csv"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_submission_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def build_html(row: dict[str, str]) -> str:
    cards: list[str] = []
    for index in (1, 2, 3):
        title = row.get(f"final_pick_{index}", "").strip()
        if not title:
            continue
        why = row.get(f"final_pick_{index}_why", "")
        caution = row.get(f"final_pick_{index}_caution", "")
        apply_url = row.get(f"final_pick_{index}_apply_url", "").strip()
        link_html = (
            f"<p style='margin:8px 0 0;'><a href='{apply_url}'>View application</a></p>"
            if apply_url
            else ""
        )
        cards.append(
            "<article style='margin:0 0 18px;padding:16px;border:1px solid #ddd;border-radius:12px;'>"
            f"<h3 style='margin:0 0 8px;'>{index}. {title}</h3>"
            f"<p style='margin:0 0 6px;'><strong>Why I chose it:</strong> {why}</p>"
            f"<p style='margin:0;'><strong>Caution:</strong> {caution}</p>"
            f"{link_html}"
            "</article>"
        )

    body = "".join(cards) or (
        "<p>I did not find a current strong match in the vetted pool for your criteria.</p>"
    )

    return (
        "<div style='font-family:Arial,sans-serif;color:#1f1a17;line-height:1.55;max-width:700px;'>"
        f"<p>Hi {row.get('artist_name', 'there')},</p>"
        "<p>Here are your current top opportunity matches based on your medium, budget, timing, and stated goals.</p>"
        f"{body}"
        f"<p><strong>Suggestions:</strong> {row.get('general_suggestions', '')}</p>"
        "</div>"
    )


def send_email(api_key: str, email_from: str, admin_email: str | None, row: dict[str, str]) -> dict[str, object]:
    payload: dict[str, object] = {
        "from": email_from,
        "to": [row.get("email", "")],
        "subject": row.get("email_subject", "Your artist opportunity shortlist"),
        "text": row.get("email_body", ""),
        "html": build_html(row),
    }
    if admin_email:
        payload["bcc"] = [admin_email]

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def send_email_smtp(
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    email_from: str,
    admin_email: str | None,
    row: dict[str, str],
) -> None:
    message = EmailMessage()
    message["Subject"] = row.get("email_subject", "Your artist opportunity shortlist")
    message["From"] = email_from
    message["To"] = row.get("email", "")
    if admin_email:
        message["Bcc"] = admin_email
    message.set_content(row.get("email_body", ""))
    message.add_alternative(build_html(row), subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send unsent result emails from results.csv")
    parser.add_argument("--only", help="Only send for a specific submission_id")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "0") or "0")
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "").strip() or None

    use_resend = bool(api_key and email_from)
    use_smtp = bool(
        smtp_host and smtp_port and smtp_username and smtp_password and email_from
    )

    if not use_resend and not use_smtp:
        print(
            "Skipping email send: configure either RESEND_API_KEY + EMAIL_FROM or "
            "SMTP_HOST/SMTP_PORT/SMTP_USERNAME/SMTP_PASSWORD + EMAIL_FROM."
        )
        return 0

    fieldnames, rows = read_rows(RESULTS_CSV)
    if not rows:
        print("No results found.")
        return 0
    submission_fieldnames, submission_rows = read_submission_rows(SUBMISSIONS_CSV)
    submissions_by_id = {
        row.get("submission_id", ""): row for row in submission_rows if row.get("submission_id", "")
    }

    sent_count = 0
    for row in rows:
        if args.only and row.get("submission_id") != args.only:
            continue
        if row.get("sent_at", "").strip():
            continue
        if not row.get("email", "").strip():
            continue
        submission = submissions_by_id.get(row.get("submission_id", ""))
        if not submission:
            continue
        if submission.get("status", "").strip().lower() != "emailed_ready":
            continue
        try:
            if use_smtp:
                send_email_smtp(
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    smtp_username=smtp_username,
                    smtp_password=smtp_password,
                    email_from=email_from,
                    admin_email=admin_email,
                    row=row,
                )
            else:
                send_email(api_key, email_from, admin_email, row)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"Failed to send {row.get('email', '')}: {exc.code} {detail}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to send {row.get('email', '')}: {exc}")
            continue
        row["sent_at"] = datetime.now().isoformat(timespec="seconds")
        submission["status"] = "emailed"
        if not submission.get("initial_email_sent_at", "").strip():
            submission["initial_email_sent_at"] = row["sent_at"]
        sent_count += 1
        print(f"Sent {row.get('artist_name', '')} <{row.get('email', '')}>")

    write_rows(RESULTS_CSV, fieldnames, rows)
    if submission_fieldnames and submission_rows:
        write_rows(SUBMISSIONS_CSV, submission_fieldnames, submission_rows)
    print(f"Sent {sent_count} email(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
