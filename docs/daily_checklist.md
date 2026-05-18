# Daily Checklist

Use this workflow for the current low-traffic operating model.

## Principle

The highest-value part of the product is not basic filtering. It is the AI-assisted review work:

- opportunity review
- official-page verification
- organizer or gallery review
- artist-to-opportunity matching
- final strategic ranking

The goal each day is to make sure AI does that work thoroughly for every serious queued submission before any recommendation email is sent.

## Daily Workflow

1. Open the project folder.

```powershell
cd "C:\Users\pweng\Documents\Artist opportunities"
```

2. Sync new submissions if needed.

```powershell
py scripts\sync_mailchimp.py --only-new
```

3. Open `data/mvp/submissions.csv`.

4. Find rows where:

- `status = research_pending`

5. For each queued row, generate a research brief.

```powershell
py scripts\generate_research_brief.py --only <submission_id>
```

6. Use that brief in Codex and have AI do the full review work:

- search current live public sources:
  - NYFA
  - CaFE
  - ArtDeadline
- collect all plausible candidates that match the artist's criteria
- verify each surviving candidate on the official page
- review organizer or gallery quality
- assess fit to the artist's medium, style, themes, and goals
- rank the final top 3

7. Write or update the review outputs:

- `data/mvp/research_candidates.csv`
- `data/mvp/verification_reviews.csv`
- `data/mvp/organizer_reviews.csv`
- `data/mvp/match_assessments.csv`
- `data/mvp/results.csv`

8. Only after the review is strong enough, update `data/mvp/submissions.csv`:

- `status = emailed_ready`

If the result is weak, incomplete, or not trustworthy, use:

- `status = needs_review`

9. Send ready emails.

```powershell
py scripts\send_result_emails.py
```

10. Confirm:

- `sent_at` is filled in `data/mvp/results.csv`
- the recommendation is real, current, and strategically defensible

## Standard

Do not send an email just because a few matches exist.

Send only when the AI-assisted review has done these things well:

- found current opportunities
- verified the facts on live pages
- judged the organizer context credibly
- matched the opportunity to the artist thoughtfully
- produced a top 3 that is strategically worth receiving

## Status meanings

- `research_pending` = waiting for live research
- `research_running` = currently being worked
- `needs_review` = not strong enough yet
- `emailed_ready` = reviewed and safe to send
- `emailed` = sent
