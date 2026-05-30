# Workflow Reference

## Current working flow

1. Run:

```powershell
py scripts\sync_mailchimp_and_generate_briefs.py --all-with-medium
```

2. This:
- syncs Mailchimp into `data/mvp/submissions.csv`
- generates brief files in `data/mvp/research_briefs/`

3. Use the brief file as the research source of truth.

4. Research the artist thoroughly:
- search NYFA, CaFE, ArtDeadline
- verify official pages
- review organizer quality
- match to the artist
- rank the top 3

5. Write/update:
- `data/mvp/research_candidates.csv`
- `data/mvp/verification_reviews.csv`
- `data/mvp/organizer_reviews.csv`
- `data/mvp/match_assessments.csv`
- `data/mvp/results.csv`

6. Set `submissions.csv -> status`:
- `emailed_ready` if the recommendation is strong
- `needs_review` if not

7. Bulk send only after that:

```powershell
py scripts\send_result_emails.py
```

## Important rules

- Brief files are canonical. CSV brief fields are optional convenience fields.
- The highest-value part of the product is AI-assisted opportunity review and artist matching, not just filtering.
- Discovery should be live and source-aware, not just cache-based.
- Do not trust snippets alone. Verify deadlines, fees, eligibility, and application URLs on official pages.
- Do not force a weak third pick just to fill the email.

## Key files

- `scripts/sync_mailchimp_and_generate_briefs.py`
- `scripts/generate_research_brief.py`
- `scripts/run_research_pipeline.py`
- `scripts/send_result_emails.py`
- `docs/daily_checklist.md`
- `docs/research_pending_workflow.md`
- `docs/email_strategy.md`
- `SESSION_NOTES.md`

## Current validated example

The most recent successful full pre-email case is:

- submission id: `mc_adaw-artco-gmail-com`
- artist: `TEST WENG`
- medium: `Watercolor`

Its researched result was written to the stage CSVs and `results.csv`, and the submission was left in:

- `status = emailed_ready`
- `results.csv -> sent_at = blank`

This is the correct state before bulk send.
