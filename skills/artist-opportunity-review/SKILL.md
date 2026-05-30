---
name: artist-opportunity-review
description: Use when working in the Artist opportunities repo to process artist submissions into researched recommendations. Trigger for tasks like syncing Mailchimp submissions, generating research brief files, reviewing brief-driven opportunity matches, searching NYFA/CaFE/ArtDeadline, writing stage CSVs, marking submissions emailed_ready, and preparing recommendation emails before bulk send.
---

# Artist Opportunity Review

Use this skill for the repo workflow that turns artist intake rows into researched opportunity recommendations.

## Use this skill when

- the user wants to process new artist submissions in this repo
- the user wants to run the daily checklist
- the user wants Codex to research a brief file in `data/mvp/research_briefs/`
- the user wants stage CSVs and `results.csv` updated before email send
- the user wants help deciding whether a row should become `emailed_ready` or `needs_review`

## Canonical inputs

- `data/mvp/submissions.csv`
- `data/mvp/research_briefs/`

Treat the brief files in `data/mvp/research_briefs/` as the canonical research documents. `submissions.csv` brief fields are convenience metadata only.

## Operator entry points

For daily bulk prep:

```powershell
py scripts\sync_mailchimp_and_generate_briefs.py --all-with-medium
```

For queue-only prep:

```powershell
py scripts\sync_mailchimp_and_generate_briefs.py --only-new
```

For one submission brief:

```powershell
py scripts\generate_research_brief.py --only <submission_id>
```

## Research standard

For each artist brief:

1. Use the artist criteria as hard filters first:
   - medium
   - budget cap
   - minimum days before deadline
   - eligible region when present
2. Search current live public sources:
   - NYFA
   - CaFE
   - ArtDeadline
3. Collect plausible candidates.
4. Verify each surviving candidate on the official page.
5. Review organizer or gallery quality.
6. Assess fit to the artist's medium, style, themes, and goals.
7. Rank the final top 3.

Do not force weak recommendations. If too few strong results survive, use `needs_review`.

## Write-back targets

After research, update:

- `data/mvp/research_candidates.csv`
- `data/mvp/verification_reviews.csv`
- `data/mvp/organizer_reviews.csv`
- `data/mvp/match_assessments.csv`
- `data/mvp/results.csv`

Then update the matching `submissions.csv` row:

- `status = emailed_ready` if the result is strong enough
- `status = needs_review` if not

Do not send email during the research step unless the user explicitly asks you to.

## Bulk send

Only after results are written and rows are `emailed_ready`, send in bulk:

```powershell
py scripts\send_result_emails.py
```

## References

Read `references/workflow.md` for the current daily flow, file roles, and current product rules.
