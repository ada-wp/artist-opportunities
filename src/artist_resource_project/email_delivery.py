from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .render import render_intake_email_html, render_intake_email_text


@dataclass(frozen=True)
class EmailSettings:
    resend_api_key: str
    email_from: str
    admin_email: str | None = None

    @classmethod
    def from_env(cls) -> EmailSettings:
        api_key = os.getenv("RESEND_API_KEY", "").strip()
        email_from = os.getenv("EMAIL_FROM", "").strip()
        admin_email = os.getenv("ADMIN_EMAIL", "").strip() or None
        if not api_key:
            raise ValueError("RESEND_API_KEY is not set")
        if not email_from:
            raise ValueError("EMAIL_FROM is not set")
        return cls(resend_api_key=api_key, email_from=email_from, admin_email=admin_email)


def send_intake_results_email(
    payload: dict[str, object],
    *,
    settings: EmailSettings | None = None,
) -> dict[str, object]:
    email_settings = settings or EmailSettings.from_env()
    recipient = str(payload.get("recipient_email", "")).strip()
    if not recipient:
        raise ValueError("recipient_email is required to send intake results")

    artist_name = str(payload.get("artist_name", "Artist"))
    subject = f"Your draft open-call shortlist — {artist_name}"
    html = render_intake_email_html(payload)
    text = render_intake_email_text(payload)

    body: dict[str, object] = {
        "from": email_settings.email_from,
        "to": [recipient],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if email_settings.admin_email:
        body["bcc"] = [email_settings.admin_email]

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {email_settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API error ({exc.code}): {detail}") from exc
