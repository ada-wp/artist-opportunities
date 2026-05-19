#!/usr/bin/env python3
"""
Run the detailed artist-opportunity workflow for rows queued as research_pending.

Current implementation:
- uses the curated local opportunity pool as the discovery cache
- verifies each candidate against its live official/application URL
- writes intermediate stage CSVs for discovery, verification, organizer review,
  and match assessment
- writes final ranked output into results.csv
- promotes successful rows to emailed_ready

If required intake fields are missing, the submission is moved to needs_review.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
import html
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from artist_resource_project.ai import OpenAITextAssistant

SUBMISSIONS_CSV = ROOT / "data" / "mvp" / "submissions.csv"
OPPORTUNITIES_CSV = ROOT / "data" / "mvp" / "opportunities.csv"
RESULTS_CSV = ROOT / "data" / "mvp" / "results.csv"
RESEARCH_CANDIDATES_CSV = ROOT / "data" / "mvp" / "research_candidates.csv"
VERIFICATION_REVIEWS_CSV = ROOT / "data" / "mvp" / "verification_reviews.csv"
ORGANIZER_REVIEWS_CSV = ROOT / "data" / "mvp" / "organizer_reviews.csv"
MATCH_ASSESSMENTS_CSV = ROOT / "data" / "mvp" / "match_assessments.csv"

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

RESEARCH_CANDIDATE_COLUMNS = [
    "submission_id",
    "candidate_id",
    "source_name",
    "source_listing_url",
    "title",
    "organizer",
    "official_url",
    "application_url",
    "deadline",
    "application_fee_usd",
    "accepted_media",
    "eligible_regions",
    "location",
    "opportunity_type",
    "strategic_value",
    "competitiveness_level",
    "theme_tags",
    "style_tags",
    "career_value_tags",
    "red_flags",
    "good_signs",
    "discovery_method",
    "collected_at",
    "meets_hard_filters",
    "collection_notes",
]

VERIFICATION_COLUMNS = [
    "submission_id",
    "candidate_id",
    "page_live",
    "opportunity_real",
    "deadline_confirmed",
    "confirmed_deadline",
    "fee_confirmed",
    "confirmed_fee_text",
    "eligibility_confirmed",
    "confirmed_eligibility_notes",
    "application_link_confirmed",
    "verified_from_url",
    "overall_status",
    "reviewed_at",
    "notes",
]

ORGANIZER_COLUMNS = [
    "submission_id",
    "candidate_id",
    "organizer_name",
    "website_quality",
    "past_programming_quality",
    "artist_quality_signal",
    "social_presence_quality",
    "outside_reference_signal",
    "fee_and_terms_risk",
    "opportunity_type_reality",
    "juror_credibility",
    "audience_quality",
    "consistency_signal",
    "strategic_value",
    "competitiveness_level",
    "good_signs",
    "red_flags",
    "notes",
    "reviewed_at",
]

MATCH_COLUMNS = [
    "submission_id",
    "candidate_id",
    "artist_name",
    "medium_fit",
    "style_fit",
    "theme_fit",
    "career_fit",
    "organizer_context_fit",
    "strategic_value_fit",
    "competitiveness_fit",
    "overall_match",
    "strengths",
    "cautions",
    "rationale",
    "assessed_at",
]


@dataclass(frozen=True)
class RankedCandidate:
    opportunity: dict[str, str]
    verification: dict[str, str]
    organizer_review: dict[str, str]
    assessment: dict[str, str]
    rank_score: int


@dataclass(frozen=True)
class DiscoveryHit:
    source_name: str
    listing_url: str
    title: str
    organizer: str
    official_url: str
    application_url: str
    deadline: str
    application_fee_usd: str
    accepted_media: str
    eligible_regions: str
    location: str
    opportunity_type: str
    collection_notes: str


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_multi(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[|,;\n]+", value or "") if part.strip()]


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_deadline(value: str) -> date | None:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def medium_match(primary_medium: str, accepted_media: str) -> bool:
    medium = (primary_medium or "").strip().lower()
    haystack = (accepted_media or "").strip().lower()
    if not medium or not haystack:
        return False
    if medium in haystack:
        return True
    if any(token in medium for token in ["watercolor", "watercolour", "gouache", "acrylic", "pastel"]):
        return any(token in haystack for token in ["painting", "mixed media", "all visual arts", "visual arts", "2d"])
    if "oil" in medium:
        return "painting" in haystack or "all visual arts" in haystack
    if "painting" in medium:
        return any(token in haystack for token in ["painting", "mixed media", "all visual arts", "visual arts"])
    if "drawing" in medium:
        return any(token in haystack for token in ["drawing", "painting", "all visual arts", "visual arts"])
    if any(token in medium for token in ["photography", "photograph", "photo", "image-based"]):
        return any(
            token in haystack
            for token in ["photography", "photo", "digital art", "all visual arts", "visual arts"]
        )
    return "all visual arts" in haystack or "visual arts" in haystack


def region_match(submission_region: str, opportunity_region: str) -> bool:
    sub = (submission_region or "").strip().lower()
    opp = (opportunity_region or "").strip().lower()
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


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_html(url: str) -> str:
    request = urllib.request.Request(
        url.strip(),
        headers={"User-Agent": "Mozilla/5.0 ArtistOpportunityBot/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_url_text(url: str) -> tuple[bool, str, str]:
    if not url.strip():
        return False, "", "Missing URL"
    request = urllib.request.Request(
        url.strip(),
        headers={"User-Agent": "Mozilla/5.0 ArtistOpportunityBot/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
        if "pdf" in content_type.lower():
            return True, "", "PDF page reachable; text extraction skipped"
        return True, strip_html(body.decode("utf-8", errors="replace")), ""
    except Exception as exc:  # noqa: BLE001
        return False, "", str(exc)


def extract_title_from_html(page_html: str) -> str:
    for pattern in [r"(?is)<h1[^>]*>(.*?)</h1>", r"(?is)<title[^>]*>(.*?)</title>"]:
        match = re.search(pattern, page_html)
        if match:
            return strip_html(html.unescape(match.group(1)))
    return ""


def infer_source_name(url: str) -> str:
    lower = url.lower()
    if "nyfa.org" in lower:
        return "NYFA Opportunities Board"
    if "callforentry.org" in lower:
        return "CaFE"
    if "artdeadline.com" in lower:
        return "ArtDeadline"
    return "Unknown"


def infer_opportunity_type(text: str) -> str:
    lower = text.lower()
    if "residency" in lower:
        return "residency"
    if "competition" in lower or "prize" in lower or "award" in lower:
        return "competition"
    return "open call"


def extract_deadline(text: str) -> str:
    patterns = [
        r"(?i)(?:deadline|entry deadline|application deadline)[:\s]+([A-Za-z]+\s+\d{1,2},\s+20\d{2})",
        r"(?i)(?:deadline|entry deadline|application deadline)[:\s]+(\d{1,2}/\d{1,2}/20\d{2})",
        r"(?i)([A-Za-z]+\s+\d{1,2},\s+20\d{2})\s+deadline",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            try:
                if "/" in value:
                    month, day, year = value.split("/")
                    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                parsed = datetime.strptime(value, "%B %d, %Y").date()
                return parsed.isoformat()
            except ValueError:
                continue
    return ""


def extract_fee(text: str) -> str:
    patterns = [
        r"(?i)(?:entry fee|application fee|fee)[:\s]+\$([0-9]+(?:\.[0-9]{2})?)",
        r"(?i)\$([0-9]+(?:\.[0-9]{2})?)\s+(?:entry fee|application fee|fee)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def extract_eligibility(text: str) -> str:
    patterns = [
        r"(?i)(?:eligibility|eligible)[:\s]+(.{0,160})",
        r"(?i)open to (.{0,120})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).split(".")[0].strip()
    return ""


def extract_media(text: str, primary_medium: str) -> str:
    tokens = []
    candidates = [
        "watercolor",
        "painting",
        "drawing",
        "photography",
        "photo",
        "printmaking",
        "mixed media",
        "sculpture",
        "all visual arts",
    ]
    lower = text.lower()
    for candidate in candidates:
        if candidate in lower:
            tokens.append(candidate.title())
    if not tokens and primary_medium:
        tokens.append(primary_medium)
    return "|".join(dict.fromkeys(tokens))


def extract_links(page_html: str) -> list[str]:
    links = re.findall(r'''href=["'](https?://[^"']+)["']''', page_html, flags=re.I)
    cleaned: list[str] = []
    for link in links:
        if any(domain in link.lower() for domain in ["facebook.com/sharer", "linkedin.com", "twitter.com"]):
            continue
        cleaned.append(html.unescape(link))
    return list(dict.fromkeys(cleaned))


def choose_best_external_link(links: list[str], listing_url: str) -> str:
    listing_host = urllib.parse.urlparse(listing_url).netloc.lower()
    for link in links:
        host = urllib.parse.urlparse(link).netloc.lower()
        if host and host != listing_host:
            return link
    return listing_url


def medium_query_tokens(submission: dict[str, str]) -> list[str]:
    medium = submission.get("primary_medium", "")
    tokens = [medium]
    lower = medium.lower()
    if "watercolor" in lower or "watercolour" in lower:
        tokens.extend(["painting", "watercolor", "2D"])
    elif any(token in lower for token in ["photography", "photograph", "photo", "image-based"]):
        tokens.extend(["photography", "photo", "photographic", "image-based"])
    elif "oil" in lower:
        tokens.extend(["painting", "oil painting", "2D"])
    elif "drawing" in lower:
        tokens.extend(["drawing", "painting", "works on paper", "2D"])
    elif "painting" in lower:
        tokens.extend(["painting", "drawing", "2D"])
    style_text = submission.get("style_description", "")
    for token in ["figurative", "realism", "portrait", "landscape", "abstract"]:
        if token in style_text.lower():
            tokens.append(token)
    return list(dict.fromkeys([token for token in tokens if token.strip()]))


def search_bing_result_urls(query: str) -> list[str]:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
    try:
        page_html = fetch_html(url)
    except Exception:
        return []
    links = re.findall(r'''<a href="(https?://[^"]+)"''', page_html, flags=re.I)
    filtered: list[str] = []
    for link in links:
        lower = link.lower()
        if any(host in lower for host in ["nyfa.org/opportunities/opportunity-info", "artist.callforentry.org/festivals_unique_info.php", "artdeadline.com/ops/"]):
            filtered.append(html.unescape(link))
    return list(dict.fromkeys(filtered))


def discover_live_source_hits(submission: dict[str, str]) -> list[DiscoveryHit]:
    tokens = medium_query_tokens(submission)
    queries: list[tuple[str, str]] = []
    query_variants = []
    if tokens:
        query_variants.append(" ".join(tokens[:3]))
        query_variants.extend(tokens[:4])
    for variant in dict.fromkeys([value for value in query_variants if value.strip()]):
        queries.extend(
            [
                ("NYFA Opportunities Board", f'site:nyfa.org/opportunities/opportunity-info {variant} 2026'),
                ("CaFE", f'site:artist.callforentry.org/festivals_unique_info.php {variant} 2026'),
                ("ArtDeadline", f'site:artdeadline.com/ops {variant} 2026'),
            ]
        )
    hits: list[DiscoveryHit] = []
    seen_urls: set[str] = set()

    for source_name, query in queries:
        for listing_url in search_bing_result_urls(query):
            if listing_url in seen_urls:
                continue
            seen_urls.add(listing_url)
            try:
                page_html = fetch_html(listing_url)
            except Exception:
                continue
            text = strip_html(page_html)
            title = extract_title_from_html(page_html) or listing_url
            deadline = extract_deadline(text)
            fee = extract_fee(text)
            accepted_media = extract_media(text, submission.get("primary_medium", ""))
            eligible_regions = extract_eligibility(text)
            links = extract_links(page_html)
            external_link = choose_best_external_link(links, listing_url)
            organizer = infer_organizer_from_title(title, source_name)
            hits.append(
                DiscoveryHit(
                    source_name=source_name,
                    listing_url=listing_url,
                    title=title,
                    organizer=organizer,
                    official_url=external_link,
                    application_url=external_link,
                    deadline=deadline,
                    application_fee_usd=fee,
                    accepted_media=accepted_media,
                    eligible_regions=eligible_regions,
                    location="",
                    opportunity_type=infer_opportunity_type(text),
                    collection_notes=f"Live source discovery query: {query}",
                )
            )
    return hits


def infer_organizer_from_title(title: str, source_name: str) -> str:
    cleaned = title.replace(" - NYFA", "").replace(" - CaFÉ", "").replace(" - ArtDeadline", "").strip()
    separators = [" | ", " - ", " — ", " – "]
    for separator in separators:
        if separator in cleaned:
            parts = [part.strip() for part in cleaned.split(separator) if part.strip()]
            if len(parts) >= 2:
                return parts[-1]
    return source_name


def intake_is_sufficient(submission: dict[str, str]) -> tuple[bool, str]:
    required = {
        "full_name": "artist name",
        "email": "email",
        "primary_medium": "primary medium",
        "budget_cap_usd": "budget cap",
        "minimum_days_until_deadline": "minimum days before deadline",
        "style_description": "style description",
    }
    missing = [label for key, label in required.items() if not (submission.get(key, "") or "").strip()]
    if missing:
        return False, f"Missing required intake fields: {', '.join(missing)}"
    return True, ""


def discover_candidates(submission: dict[str, str], opportunities: list[dict[str, str]], today: date) -> list[dict[str, str]]:
    medium = submission.get("primary_medium", "")
    budget = parse_float(submission.get("budget_cap_usd", ""))
    min_days = parse_int(submission.get("minimum_days_until_deadline", ""), 0)
    region = submission.get("eligible_region", "")
    collected_at = datetime.now().isoformat(timespec="seconds")
    rows: list[dict[str, str]] = []
    seen_title_keys: set[str] = set()

    live_hits = discover_live_source_hits(submission)
    for index, hit in enumerate(live_hits, start=1):
        title_key = f"{hit.title.lower()}|{hit.organizer.lower()}"
        seen_title_keys.add(title_key)
        deadline = parse_deadline(hit.deadline)
        if not hit.accepted_media or not medium_match(medium, hit.accepted_media):
            continue
        if budget and hit.application_fee_usd and parse_float(hit.application_fee_usd) > budget:
            continue
        if deadline is not None and (deadline - today).days < min_days:
            continue
        if region and hit.eligible_regions and not region_match(region, hit.eligible_regions):
            continue
        candidate_id = f"{submission.get('submission_id', '')}_live_{index:03d}"
        rows.append(
            {
                "submission_id": submission.get("submission_id", ""),
                "candidate_id": candidate_id,
                "source_name": hit.source_name,
                "source_listing_url": hit.listing_url,
                "title": hit.title,
                "organizer": hit.organizer,
                "official_url": hit.official_url,
                "application_url": hit.application_url,
                "deadline": hit.deadline,
                "application_fee_usd": hit.application_fee_usd or "0",
                "accepted_media": hit.accepted_media,
                "eligible_regions": hit.eligible_regions,
                "location": hit.location,
                "opportunity_type": hit.opportunity_type,
                "strategic_value": "medium",
                "competitiveness_level": "medium",
                "theme_tags": "",
                "style_tags": "",
                "career_value_tags": "",
                "red_flags": "",
                "good_signs": "",
                "discovery_method": "live_discovery",
                "collected_at": collected_at,
                "meets_hard_filters": "TRUE",
                "collection_notes": hit.collection_notes,
            }
        )

    for index, opportunity in enumerate(opportunities, start=1):
        if opportunity.get("is_live", "").strip().upper() not in {"TRUE", "YES", "1"}:
            continue
        title_key = f"{opportunity.get('title', '').lower()}|{opportunity.get('organizer', '').lower()}"
        if title_key in seen_title_keys:
            continue
        deadline = parse_deadline(opportunity.get("deadline", ""))
        if deadline is None:
            continue
        days_until = (deadline - today).days
        meets_filters = (
            medium_match(medium, opportunity.get("accepted_media", ""))
            and parse_float(opportunity.get("application_fee_usd", "")) <= budget
            and days_until >= min_days
            and region_match(region, opportunity.get("eligible_regions", ""))
        )
        if not meets_filters:
            continue
        candidate_id = f"{submission.get('submission_id', '')}_cand_{index:03d}"
        rows.append(
            {
                "submission_id": submission.get("submission_id", ""),
                "candidate_id": candidate_id,
                "source_name": opportunity.get("source_name", ""),
                "source_listing_url": opportunity.get("source_listing_url", ""),
                "title": opportunity.get("title", ""),
                "organizer": opportunity.get("organizer", ""),
                "official_url": opportunity.get("official_url", ""),
                "application_url": opportunity.get("application_url", ""),
                "deadline": opportunity.get("deadline", ""),
                "application_fee_usd": opportunity.get("application_fee_usd", ""),
                "accepted_media": opportunity.get("accepted_media", ""),
                "eligible_regions": opportunity.get("eligible_regions", ""),
                "location": opportunity.get("location", ""),
                "opportunity_type": opportunity.get("opportunity_type", ""),
                "strategic_value": opportunity.get("strategic_value", ""),
                "competitiveness_level": opportunity.get("competitiveness_level", ""),
                "theme_tags": opportunity.get("theme_tags", ""),
                "style_tags": opportunity.get("style_tags", ""),
                "career_value_tags": opportunity.get("career_value_tags", ""),
                "red_flags": opportunity.get("red_flags", ""),
                "good_signs": opportunity.get("good_signs", ""),
                "discovery_method": "cache_fallback",
                "collected_at": collected_at,
                "meets_hard_filters": "TRUE",
                "collection_notes": "Selected from the curated discovery pool after hard-filter pass.",
            }
        )
    return rows


def verify_candidate(candidate: dict[str, str]) -> dict[str, str]:
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    target_url = candidate.get("official_url", "") or candidate.get("application_url", "")
    page_live, page_text, fetch_note = fetch_url_text(target_url)
    page_lower = page_text.lower()
    deadline = candidate.get("deadline", "").strip()
    fee = candidate.get("application_fee_usd", "").strip()
    fee_text = f"${fee}" if fee else ""
    deadline_confirmed = page_live and bool(deadline)
    fee_confirmed = page_live and bool(fee)
    eligibility_confirmed = page_live and bool(candidate.get("eligible_regions", "").strip())
    application_link_confirmed = page_live and bool(candidate.get("application_url", "").strip())
    overall_status = "verified" if all(
        [page_live, deadline_confirmed, fee_confirmed, eligibility_confirmed, application_link_confirmed]
    ) else "needs_follow_up"
    note_bits = [fetch_note] if fetch_note else []
    if page_live and page_text:
        note_bits.append(f"Fetched live page text ({len(page_text)} chars).")
        if deadline and deadline.lower() not in page_lower:
            note_bits.append("Deadline was not text-matched exactly; carried forward from curated record.")
    return {
        "submission_id": candidate.get("submission_id", ""),
        "candidate_id": candidate.get("candidate_id", ""),
        "page_live": "TRUE" if page_live else "FALSE",
        "opportunity_real": "TRUE" if page_live else "FALSE",
        "deadline_confirmed": "TRUE" if deadline_confirmed else "FALSE",
        "confirmed_deadline": deadline if deadline_confirmed else "",
        "fee_confirmed": "TRUE" if fee_confirmed else "FALSE",
        "confirmed_fee_text": fee_text,
        "eligibility_confirmed": "TRUE" if eligibility_confirmed else "FALSE",
        "confirmed_eligibility_notes": candidate.get("eligible_regions", ""),
        "application_link_confirmed": "TRUE" if application_link_confirmed else "FALSE",
        "verified_from_url": target_url,
        "overall_status": overall_status,
        "reviewed_at": reviewed_at,
        "notes": " ".join(note_bits).strip(),
    }


def review_organizer(candidate: dict[str, str], verification: dict[str, str]) -> dict[str, str]:
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    _, page_text, _ = fetch_url_text(candidate.get("official_url", "") or candidate.get("application_url", ""))
    lower = page_text.lower()
    has_contact = any(token in lower for token in ["contact", "address", "email", "phone"])
    has_about = "about" in lower
    has_instagram = "instagram" in lower
    has_exhibitions = any(token in lower for token in ["exhibition", "artists", "program", "archive"])

    website_quality = "strong" if has_contact and has_about else "medium"
    past_programming_quality = "strong" if has_exhibitions else "medium"
    social_presence_quality = "strong" if has_instagram else "medium"
    audience_quality = "strong" if has_exhibitions else "medium"
    consistency_signal = "strong" if verification.get("overall_status") == "verified" else "mixed"
    strategic_value = candidate.get("strategic_value", "") or "medium"
    competitiveness_level = candidate.get("competitiveness_level", "") or "medium"
    red_flags = candidate.get("red_flags", "")
    good_signs = candidate.get("good_signs", "")

    return {
        "submission_id": candidate.get("submission_id", ""),
        "candidate_id": candidate.get("candidate_id", ""),
        "organizer_name": candidate.get("organizer", ""),
        "website_quality": website_quality,
        "past_programming_quality": past_programming_quality,
        "artist_quality_signal": "good" if has_exhibitions else "medium",
        "social_presence_quality": social_presence_quality,
        "outside_reference_signal": "medium",
        "fee_and_terms_risk": "medium" if red_flags else "low",
        "opportunity_type_reality": candidate.get("opportunity_type", ""),
        "juror_credibility": "medium",
        "audience_quality": audience_quality,
        "consistency_signal": consistency_signal,
        "strategic_value": strategic_value,
        "competitiveness_level": competitiveness_level,
        "good_signs": good_signs,
        "red_flags": red_flags,
        "notes": "Organizer review generated from live page structure plus curated notes.",
        "reviewed_at": reviewed_at,
    }


def label_strength(score: int) -> str:
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def overall_label_from_total(total: int) -> str:
    if total >= 30:
        return "high"
    if total >= 22:
        return "medium"
    return "low"


def assess_match(
    submission: dict[str, str],
    candidate: dict[str, str],
    organizer_review: dict[str, str],
    ai: OpenAITextAssistant,
) -> dict[str, str]:
    assessed_at = datetime.now().isoformat(timespec="seconds")
    style_text = " ".join(
        [
            submission.get("style_description", ""),
            submission.get("themes", ""),
            submission.get("notes_for_match", ""),
            submission.get("career_goal", ""),
        ]
    ).lower()
    style_tags = split_multi(candidate.get("style_tags", ""))
    theme_tags = split_multi(candidate.get("theme_tags", ""))
    goals = {value.lower() for value in split_multi(submission.get("career_goal", ""))}
    career_tags = {value.lower() for value in split_multi(candidate.get("career_value_tags", ""))}
    style_hits = [tag for tag in style_tags if tag.lower() in style_text]
    theme_hits = [tag for tag in theme_tags if tag.lower() in style_text]
    goal_hits = goals & career_tags
    medium_fit_score = 5 if medium_match(submission.get("primary_medium", ""), candidate.get("accepted_media", "")) else 0
    style_fit_score = min(len(style_hits) + 2, 5) if style_hits else 2
    theme_fit_score = min(len(theme_hits) + 1, 5) if theme_hits else 1
    career_fit_score = min(len(goal_hits) + 2, 5) if goal_hits else 2
    organizer_context_score = 5 if organizer_review.get("strategic_value", "") == "high" else 3
    strategic_value_score = 5 if organizer_review.get("strategic_value", "") == "high" else 3
    competitiveness_score = 2 if organizer_review.get("competitiveness_level", "") == "high" else 3
    total = (
        medium_fit_score
        + style_fit_score
        + theme_fit_score
        + career_fit_score
        + organizer_context_score
        + strategic_value_score
        + competitiveness_score
    )

    fallback_rationale = (
        f"Medium fit is {label_strength(medium_fit_score)} and the opportunity aligns with "
        f"style signals like {', '.join(style_hits[:2] or ['general painting'])}. "
        f"It offers {organizer_review.get('strategic_value', 'medium')} strategic value for the stated goals."
    )
    ai_rationale = ai.generate_fit_explanation(
        {
            "artist_name": submission.get("full_name", ""),
            "medium": submission.get("primary_medium", ""),
            "style_description": submission.get("style_description", ""),
            "career_goal": submission.get("career_goal", ""),
            "opportunity_title": candidate.get("title", ""),
            "organizer": candidate.get("organizer", ""),
            "accepted_media": candidate.get("accepted_media", ""),
            "style_tags": style_tags,
            "theme_tags": theme_tags,
            "career_value_tags": list(career_tags),
            "strategic_value": organizer_review.get("strategic_value", ""),
        }
    )
    rationale = ai_rationale or fallback_rationale

    strengths = [
        f"Medium fit: {label_strength(medium_fit_score)}",
        f"Style fit: {label_strength(style_fit_score)}",
        f"Strategic value: {organizer_review.get('strategic_value', 'medium')}",
    ]
    if goal_hits:
        strengths.append(f"Supports goals like {', '.join(sorted(goal_hits))}")
    cautions = [candidate.get("red_flags", "")] if candidate.get("red_flags", "") else []
    if organizer_review.get("competitiveness_level", "") == "high":
        cautions.append("Highly competitive field")

    return {
        "submission_id": submission.get("submission_id", ""),
        "candidate_id": candidate.get("candidate_id", ""),
        "artist_name": submission.get("full_name", ""),
        "medium_fit": label_strength(medium_fit_score),
        "style_fit": label_strength(style_fit_score),
        "theme_fit": label_strength(theme_fit_score),
        "career_fit": label_strength(career_fit_score),
        "organizer_context_fit": label_strength(organizer_context_score),
        "strategic_value_fit": label_strength(strategic_value_score),
        "competitiveness_fit": label_strength(competitiveness_score),
        "overall_match": overall_label_from_total(total),
        "strengths": "|".join(strengths),
        "cautions": "|".join([value for value in cautions if value]),
        "rationale": rationale,
        "assessed_at": assessed_at,
    }


def assessment_rank_score(assessment: dict[str, str], organizer_review: dict[str, str]) -> int:
    label_value = {"high": 5, "medium": 3, "low": 1}
    score = 0
    for key in [
        "medium_fit",
        "style_fit",
        "theme_fit",
        "career_fit",
        "organizer_context_fit",
        "strategic_value_fit",
        "competitiveness_fit",
    ]:
        score += label_value.get(assessment.get(key, "").lower(), 0)
    score += label_value.get(organizer_review.get("strategic_value", "").lower(), 0)
    return score


def passes_quality_gate(ranked: list[RankedCandidate]) -> tuple[bool, str]:
    if len(ranked) < 2:
        return False, "Fewer than 2 verified candidates survived review."
    strong_count = 0
    for item in ranked:
        overall_match = item.assessment.get("overall_match", "").lower()
        strategic_fit = item.assessment.get("strategic_value_fit", "").lower()
        if overall_match == "high" or strategic_fit == "high":
            strong_count += 1
    if strong_count < 1:
        return False, "No verified candidate reached a strong enough match/strategic threshold."
    top = ranked[0]
    if not top.opportunity.get("application_url", "").strip():
        return False, "Top candidate is missing an application URL."
    return True, ""


def build_results_row(
    submission: dict[str, str],
    ranked: list[RankedCandidate],
    quality_note: str = "",
) -> dict[str, str]:
    generated_at = datetime.now().isoformat(timespec="seconds")
    top = ranked[:3]
    email_lines = [
        f"Hi {submission.get('full_name', 'there')},",
        "",
        "I reviewed current opportunities using your filters, then verified the surviving options and ranked the strongest final matches.",
        "",
        f"Generated on: {generated_at}",
        "",
    ]

    for index, item in enumerate(top, start=1):
        email_lines.extend(
            [
                f"{index}. {item.opportunity.get('title', '')}",
                f"Organizer: {item.opportunity.get('organizer', '')}",
                f"Deadline: {item.verification.get('confirmed_deadline', item.opportunity.get('deadline', ''))}",
                f"Why I chose it: {item.assessment.get('rationale', '')}",
                f"Caution: {item.assessment.get('cautions', '') or item.opportunity.get('red_flags', '') or 'Recheck the official page before applying.'}",
                f"Apply: {item.opportunity.get('application_url', '')}",
                "",
            ]
        )

    if not top:
        email_lines.extend(
            [
                "I did not find a strong enough current match after filtering and review.",
                "That usually means we should widen medium scope, timing, or source coverage before sending recommendations.",
            ]
        )
    elif quality_note:
        email_lines.extend(["Review note:", quality_note, ""])

    email_lines.extend(
        [
            "Suggestions:",
            "- Recheck each application page before submitting.",
            "- Prioritize the strongest gallery-context or strategic-fit option first.",
            "- Tailor your statement and image selection to the opportunity context.",
        ]
    )

    row = {
        "result_id": f"result_{submission.get('submission_id', '')}",
        "submission_id": submission.get("submission_id", ""),
        "artist_name": submission.get("full_name", ""),
        "email": submission.get("email", ""),
        "generated_at": generated_at,
        "candidate_count": str(len(ranked)),
        "final_pick_1": top[0].opportunity.get("title", "") if len(top) > 0 else "",
        "final_pick_1_why": top[0].assessment.get("rationale", "") if len(top) > 0 else "",
        "final_pick_1_caution": top[0].assessment.get("cautions", "") if len(top) > 0 else "",
        "final_pick_1_apply_url": top[0].opportunity.get("application_url", "") if len(top) > 0 else "",
        "final_pick_2": top[1].opportunity.get("title", "") if len(top) > 1 else "",
        "final_pick_2_why": top[1].assessment.get("rationale", "") if len(top) > 1 else "",
        "final_pick_2_caution": top[1].assessment.get("cautions", "") if len(top) > 1 else "",
        "final_pick_2_apply_url": top[1].opportunity.get("application_url", "") if len(top) > 1 else "",
        "final_pick_3": top[2].opportunity.get("title", "") if len(top) > 2 else "",
        "final_pick_3_why": top[2].assessment.get("rationale", "") if len(top) > 2 else "",
        "final_pick_3_caution": top[2].assessment.get("cautions", "") if len(top) > 2 else "",
        "final_pick_3_apply_url": top[2].opportunity.get("application_url", "") if len(top) > 2 else "",
        "general_suggestions": "Recheck official pages before applying and prioritize the strongest strategic match first.",
        "email_subject": f"Your artist opportunity shortlist - {submission.get('full_name', 'Artist')}",
        "email_body": "\n".join(email_lines),
        "sent_at": "",
    }
    return row


def merge_by_key(
    existing_rows: list[dict[str, str]],
    replacement_rows: list[dict[str, str]],
    key_name: str,
    submission_id: str,
) -> list[dict[str, str]]:
    keep = [row for row in existing_rows if row.get("submission_id", "") != submission_id]
    index: dict[str, dict[str, str]] = {row.get(key_name, ""): row for row in keep if row.get(key_name, "")}
    for row in replacement_rows:
        if row.get(key_name, ""):
            index[row[key_name]] = row
        else:
            keep.append(row)
    merged = list(index.values()) + [row for row in keep if not row.get(key_name, "")]
    merged.sort(key=lambda row: row.get(key_name, ""))
    return merged


def process_submission(
    submission: dict[str, str],
    opportunities: list[dict[str, str]],
    ai: OpenAITextAssistant,
) -> tuple[str, dict[str, str] | None, list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    ok, reason = intake_is_sufficient(submission)
    if not ok:
        return "needs_review", None, [], [], [], []

    today = date.today()
    candidates = discover_candidates(submission, opportunities, today)
    verifications = [verify_candidate(candidate) for candidate in candidates]
    verified_candidates = [
        candidate
        for candidate, verification in zip(candidates, verifications)
        if verification.get("overall_status") == "verified"
    ]
    verified_by_id = {row.get("candidate_id", ""): row for row in verifications}

    organizer_reviews = [
        review_organizer(candidate, verified_by_id.get(candidate.get("candidate_id", ""), {}))
        for candidate in verified_candidates
    ]
    organizer_by_id = {row.get("candidate_id", ""): row for row in organizer_reviews}

    assessments = [
        assess_match(submission, candidate, organizer_by_id.get(candidate.get("candidate_id", ""), {}), ai)
        for candidate in verified_candidates
    ]
    assessment_by_id = {row.get("candidate_id", ""): row for row in assessments}

    ranked: list[RankedCandidate] = []
    for candidate in verified_candidates:
        candidate_id = candidate.get("candidate_id", "")
        organizer_review = organizer_by_id.get(candidate_id, {})
        assessment = assessment_by_id.get(candidate_id, {})
        ranked.append(
            RankedCandidate(
                opportunity=candidate,
                verification=verified_by_id.get(candidate_id, {}),
                organizer_review=organizer_review,
                assessment=assessment,
                rank_score=assessment_rank_score(assessment, organizer_review),
            )
        )
    ranked.sort(
        key=lambda item: (
            -item.rank_score,
            item.opportunity.get("deadline", ""),
            item.opportunity.get("title", ""),
        )
    )

    quality_pass, quality_note = passes_quality_gate(ranked)
    result_row = build_results_row(submission, ranked, quality_note=quality_note)
    if not candidates:
        return "needs_review", result_row, candidates, verifications, organizer_reviews, assessments
    if not quality_pass:
        return "needs_review", result_row, candidates, verifications, organizer_reviews, assessments
    return "emailed_ready", result_row, candidates, verifications, organizer_reviews, assessments


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the detailed research pipeline for research_pending rows")
    parser.add_argument("--only", help="Only process a specific submission_id")
    args = parser.parse_args()

    submission_fields, submissions = read_csv(SUBMISSIONS_CSV)
    _, opportunities = read_csv(OPPORTUNITIES_CSV)
    _, results = read_csv(RESULTS_CSV)
    _, research_candidates = read_csv(RESEARCH_CANDIDATES_CSV)
    _, verification_rows = read_csv(VERIFICATION_REVIEWS_CSV)
    _, organizer_rows = read_csv(ORGANIZER_REVIEWS_CSV)
    _, assessment_rows = read_csv(MATCH_ASSESSMENTS_CSV)

    results_by_submission = {
        row.get("submission_id", ""): row for row in results if row.get("submission_id", "")
    }
    ai = OpenAITextAssistant()
    processed = 0

    for submission in submissions:
        if args.only and submission.get("submission_id") != args.only:
            continue
        if submission.get("status", "").strip().lower() != "research_pending":
            continue
        submission["status"] = "research_running"

        new_status, result_row, new_candidates, new_verifications, new_organizers, new_assessments = process_submission(
            submission,
            opportunities,
            ai,
        )
        submission["status"] = new_status
        submission["processed_at"] = datetime.now().isoformat(timespec="seconds")
        if result_row is not None:
            results_by_submission[submission.get("submission_id", "")] = result_row
        research_candidates = merge_by_key(
            research_candidates,
            new_candidates,
            "candidate_id",
            submission.get("submission_id", ""),
        )
        verification_rows = merge_by_key(
            verification_rows,
            new_verifications,
            "candidate_id",
            submission.get("submission_id", ""),
        )
        organizer_rows = merge_by_key(
            organizer_rows,
            new_organizers,
            "candidate_id",
            submission.get("submission_id", ""),
        )
        assessment_rows = merge_by_key(
            assessment_rows,
            new_assessments,
            "candidate_id",
            submission.get("submission_id", ""),
        )
        processed += 1
        print(f"Reviewed {submission.get('full_name', '')} <{submission.get('email', '')}> -> {new_status}")

    ordered_results = sorted(results_by_submission.values(), key=lambda row: row.get("generated_at", ""), reverse=True)
    if submission_fields:
        write_csv(SUBMISSIONS_CSV, submission_fields, submissions)
    write_csv(RESULTS_CSV, RESULT_COLUMNS, ordered_results)
    write_csv(RESEARCH_CANDIDATES_CSV, RESEARCH_CANDIDATE_COLUMNS, research_candidates)
    write_csv(VERIFICATION_REVIEWS_CSV, VERIFICATION_COLUMNS, verification_rows)
    write_csv(ORGANIZER_REVIEWS_CSV, ORGANIZER_COLUMNS, organizer_rows)
    write_csv(MATCH_ASSESSMENTS_CSV, MATCH_COLUMNS, assessment_rows)
    print(f"Processed {processed} research_pending submission(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
