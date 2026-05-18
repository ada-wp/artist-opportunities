from __future__ import annotations

import json


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Top Open Call Recommendations",
        "",
        f"Artist ID: `{payload['artist_id']}`",
        f"Generated on: `{payload['generated_on']}`",
        "",
    ]

    for item in payload["top_recommendations"]:
        lines.extend(
            [
                f"## {item['rank']}. {item['title']}",
                f"- Organizer: {item['organizer']}",
                f"- Deadline: {item['deadline']}",
                f"- Fee: ${item['application_fee_usd']}",
                f"- Media: {', '.join(item['accepted_media'])}",
                f"- Location / Eligibility: {item['location']}",
                f"- Source: {item['source_name']}",
                f"- Score: {item['score']}",
                f"- Why it fits: {item['fit_summary']}",
                f"- Caution: {item['caution_note']}",
                f"- Apply: {item['application_url']}",
                "",
            ]
        )

    return "\n".join(lines)


def render_intake_email_text(payload: dict[str, object]) -> str:
    artist_name = payload.get("artist_name", "there")
    lines = [
        f"Hi {artist_name},",
        "",
        "Thanks for submitting your artist intake. Below is a draft shortlist of open calls",
        "that match your filters and practice signals in our current verified database.",
        "",
        "Important:",
        "- This is an automated draft, not a final curator review.",
        "- Always confirm deadline, fee, and eligibility on the official listing before applying.",
        "",
        f"Generated on: {payload.get('generated_on', '')}",
        "",
    ]

    recommendations = payload.get("top_recommendations", [])
    if not recommendations:
        lines.extend(
            [
                "We did not find any current matches in the verified database for your criteria.",
                "Try widening your budget cap, regions, or minimum days before deadline.",
                "",
            ]
        )
    else:
        for item in recommendations:
            lines.extend(
                [
                    f"{item['rank']}. {item['title']}",
                    f"   Organizer: {item['organizer']}",
                    f"   Deadline: {item['deadline']}",
                    f"   Fee: ${item['application_fee_usd']}",
                    f"   Location: {item['location']}",
                    f"   Why it fits: {item['fit_summary']}",
                    f"   Caution: {item['caution_note']}",
                    f"   Apply: {item['application_url']}",
                    "",
                ]
            )

    lines.append("Reply to this email if you want a deeper organizer review pass.")
    return "\n".join(lines)


def render_intake_email_html(payload: dict[str, object]) -> str:
    artist_name = payload.get("artist_name", "there")
    recommendations = payload.get("top_recommendations", [])

    if not recommendations:
        body = (
            "<p>We did not find any current matches in the verified database for your criteria.</p>"
            "<p>Try widening your budget cap, eligible regions, or minimum days before deadline.</p>"
        )
    else:
        cards = []
        for item in recommendations:
            cards.append(
                "<article style='margin:0 0 20px;padding:16px;border:1px solid #ddd;border-radius:12px;'>"
                f"<h3 style='margin:0 0 8px;'>{item['rank']}. {item['title']}</h3>"
                f"<p style='margin:0 0 6px;'><strong>Organizer:</strong> {item['organizer']}</p>"
                f"<p style='margin:0 0 6px;'><strong>Deadline:</strong> {item['deadline']}</p>"
                f"<p style='margin:0 0 6px;'><strong>Fee:</strong> ${item['application_fee_usd']}</p>"
                f"<p style='margin:0 0 6px;'><strong>Location:</strong> {item['location']}</p>"
                f"<p style='margin:0 0 6px;'><strong>Why it fits:</strong> {item['fit_summary']}</p>"
                f"<p style='margin:0 0 6px;'><strong>Caution:</strong> {item['caution_note']}</p>"
                f"<p style='margin:0;'><a href='{item['application_url']}'>View application</a></p>"
                "</article>"
            )
        body = "".join(cards)

    return (
        "<div style='font-family:Georgia,serif;color:#1f1a17;line-height:1.5;max-width:640px;'>"
        f"<p>Hi {artist_name},</p>"
        "<p>Thanks for submitting your artist intake. Below is a <strong>draft shortlist</strong> "
        "based on your filters and our current verified opportunity database.</p>"
        "<p><strong>Important:</strong> This is an automated draft, not a final curator review. "
        "Always confirm deadline, fee, and eligibility on the official listing before applying.</p>"
        f"{body}"
        "<p style='margin-top:24px;'>Reply if you want a deeper organizer review pass.</p>"
        "</div>"
    )

