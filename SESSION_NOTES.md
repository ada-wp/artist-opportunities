# Session Notes

## Current Product Direction

The project now follows a 7-step workflow instead of the older "rank a fixed database" prototype.

1. Step 1: hard filters from the artist via a structured form
2. Step 2: collect all candidate opportunities that meet those hard filters
3. Step 3: verify the candidate list against live pages
4. Step 4: organizer/gallery review done by Codex using the `organizer review` checklist plus external research
5. Step 5: richer artist intake with style, themes, career goal, and up to 10 images
6. Step 6: match the artist to the verified opportunities
7. Step 7: rank the final top 3

## Current MVP Process As Of May 18, 2026

The project now has a working CSV-first MVP pipeline for:

1. collecting artist audience leads through Framer
2. syncing those leads from Mailchimp into a local submissions file
3. processing usable submissions against a curated opportunity pool
4. writing recommendation results to a results file
5. sending the recommendation email automatically from Gmail SMTP

This is now the practical operating process, even though the broader 7-step product direction is still the long-term frame.

## Current End-To-End Workflow

### 1. Public Intake

- artist fills out the Framer form
- Framer sends the submission to Mailchimp audience storage
- Mailchimp is being used for audience growth and lead capture

### 2. Audience Sync

- local script:
  - [scripts/sync_mailchimp.py](C:\Users\pweng\Documents\Artist opportunities\scripts\sync_mailchimp.py)
- pulls Mailchimp audience contacts into:
  - [data/mvp/submissions.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\submissions.csv)
- current scheduling intent:
  - run every 3 minutes through Windows Task Scheduler
- new synced records should default to:
  - `research_pending`

### 3. Submission Queueing

Current operating decision:

- new submissions should be queued for detailed review
- they should not be immediately auto-emailed without review logic

### 4. Detailed Review Requirement

For each serious new artist record, the intended process is:

1. apply hard filters
2. search current live sources:
   - NYFA
   - CaFE
   - ArtDeadline
3. collect candidate opportunities
4. verify each candidate on the live official page
5. review the organizer or gallery
6. assess artist fit
7. rank the final top 3
8. then send the email

The current local CSV opportunity pool is useful as a reference cache, but it is not the full source of truth for new user recommendations.

### 5. Automated Research Runner

The repository now includes:

- [scripts/run_research_pipeline.py](C:\Users\pweng\Documents\Artist opportunities\scripts\run_research_pipeline.py)

Current behavior of the research runner:

1. reads rows in `submissions.csv` where `status = research_pending`
2. checks whether the intake is sufficient
3. uses the curated opportunity pool as the current discovery cache
4. verifies candidate URLs live
5. writes intermediate stage files:
   - [data/mvp/research_candidates.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\research_candidates.csv)
   - [data/mvp/verification_reviews.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\verification_reviews.csv)
   - [data/mvp/organizer_reviews.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\organizer_reviews.csv)
   - [data/mvp/match_assessments.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\match_assessments.csv)
6. writes the final ranked output into:
   - [data/mvp/results.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\results.csv)
7. sets the submission status to:
   - `emailed_ready` if recommendation output is ready
   - `needs_review` if intake is insufficient or the result is too weak

AI is optional inside this step:

- if `OPENAI_API_KEY` is configured, the runner can generate richer fit rationale
- if not, deterministic fallback rationale is used

### 6. Submission Processing

- local script:
  - [scripts/process_submissions.py](C:\Users\pweng\Documents\Artist opportunities\scripts\process_submissions.py)
- reads:
  - [data/mvp/submissions.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\submissions.csv)
  - [data/mvp/opportunities.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\opportunities.csv)
- only processes rows where:
  - `status = research_complete`
  - `processed_at` is empty
  - `primary_medium` is non-empty
- writes output into:
  - [data/mvp/results.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\results.csv)
- after processing:
  - marks the submission row `emailed_ready`
  - fills `processed_at`

### 7. Recommendation Output

Each processed row now stores:

- artist name
- artist email
- top 3 selected opportunities
- why each opportunity was selected
- caution for each opportunity
- direct application link for each opportunity
- overall suggestions
- email subject
- email body
- `sent_at`

### 8. Email Delivery

- local script:
  - [scripts/send_result_emails.py](C:\Users\pweng\Documents\Artist opportunities\scripts\send_result_emails.py)
- reads unsent rows from:
  - [data/mvp/results.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\results.csv)
- sends recommendation email directly
- current sending method:
  - Gmail SMTP with app password
- after successful send:
  - fills `sent_at`
- intended timing:
  - only after detailed review is complete

### 9. Full Wrapper Command

- current wrapper:
  - [scripts/sync_then_process.ps1](C:\Users\pweng\Documents\Artist opportunities\scripts\sync_then_process.ps1)
- current order:
  1. sync Mailchimp into `submissions.csv`
  2. run `run_research_pipeline.py` for `research_pending` rows
  3. send email for rows that reach `emailed_ready`

## Current Data Files

- submissions inbox:
  - [data/mvp/submissions.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\submissions.csv)
- curated opportunity pool:
  - [data/mvp/opportunities.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\opportunities.csv)
- research candidates:
  - [data/mvp/research_candidates.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\research_candidates.csv)
- verification reviews:
  - [data/mvp/verification_reviews.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\verification_reviews.csv)
- organizer reviews:
  - [data/mvp/organizer_reviews.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\organizer_reviews.csv)
- match assessments:
  - [data/mvp/match_assessments.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\match_assessments.csv)
- recommendation results:
  - [data/mvp/results.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\results.csv)

## Current Email Template

- canonical template reference:
  - [templates/artist_recommendation_email_template.md](C:\Users\pweng\Documents\Artist opportunities\templates\artist_recommendation_email_template.md)

This is the standalone reference for:

- email subject
- plain-text structure
- HTML structure
- reusable pick block / pick card

## Current Environment Setup

Local `.env` is now the place for:

- `MAILCHIMP_API_KEY`
- `MAILCHIMP_LIST_ID`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `ADMIN_EMAIL`

Reference example:

- [.env.example](C:\Users\pweng\Documents\Artist opportunities\.env.example)

## Current Scheduling Setup

Target scheduler behavior:

- Windows Task Scheduler
- run every 3 minutes
- run:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\pweng\Documents\Artist opportunities\scripts\sync_then_process.ps1"`

Importable task file created:

- [scripts/mailchimp_sync_task.xml](C:\Users\pweng\Documents\Artist opportunities\scripts\mailchimp_sync_task.xml)

Note:
- the XML task currently reflects the sync job structure created during the session
- if needed, it should be updated to point to `sync_then_process.ps1` as the final scheduled action

## Key Principles

- Step 2 is discovery only. Do not trust snippets or memory as final truth.
- Step 3 must re-open the live page and store the confirmed facts.
- If dates or fees conflict, trust the current live listing or organizer page.
- Organizer review and fit analysis are first-class steps, not side notes.

## User Input vs Analyst Work

### Artist Input

- Step 1 form:
  - `lead_sources`
  - `medium_preferences`
  - `budget_cap_usd`
  - `eligible_regions`
  - `minimum_days_until_deadline`
  - `opportunity_types`
  - `location_preferences`
  - `format_preferences`
  - `geographic_scope_preferences`

- Step 5 form:
  - `career_stage`
  - `medium_preferences`
  - `style_description`
  - `themes`
  - `career_goal`
  - `artwork_image_paths` (max 10)
  - `target_visibility`
  - `preferred_contexts`
  - `competitiveness_tolerance`

### Codex / Analyst Work

- Step 4 organizer review
- Step 6 match assessment
- Step 7 final ranking

## Active Lead Sources

- `NYFA Opportunities Board`
  - usable as a discovery source through manual research / assisted browsing
- `CaFE`
  - workable public discovery source
- `ArtDeadline`
  - workable public discovery source
- `Artenda`
  - subscription-limited / incomplete public access
  - do not treat as a dependable public Step 2 source unless paid access is available

## Important Access Lesson

Search snippets can be stale.

Example:
- `Land(Scape): A Call for Works About the Space the Earth Provides`
- older snippet suggested `March 28, 2026`
- live ArtDeadline page showed an extension to `April 19, 2026`

So Step 3 should always store:
- `confirmed_deadline`
- `confirmed_fee_text`
- `confirmed_eligibility_notes`
- `verified_from_url`

## Example Artist Used In Session

- career stage: `emerging`
- medium: `oil painting`
- search expanded to `painting or drawing`
- budget cap: `100`
- region: `US`
- minimum days before deadline: `10`
- style:
  - contemporary figurative painting with an atelier foundation
  - atmospheric, tonal, intimate, psychologically quiet
  - selective ambiguity and painterly editing
- career goal:
  - get into galleries
  - build reputation

## Current Live-Test Submission Used In This Session

The newest usable live submission row during this session was:

- artist name: `jane weng`
- email: `adaw.artco@gmail.com`
- career stage: `Emerging`
- primary medium: `Oil painting`
- budget cap: `60`
- minimum days before deadline: `7`
- style description contained:
  - `Portraiture`
  - `Realism`

This row was used as the live MVP processing example because it had the most useful currently available fields.

## Current Live-Test Top 3

For the current curated MVP pool, the top 3 for `jane weng` were:

1. `OPA 2026 National Juried Salon`
2. `Viridian Artists Summer Juried Exhibition`
3. `Mirroring Reality: Realism Today`

These were selected because:

- they fit `oil painting`
- they stayed within the artist's budget cap
- they met the deadline buffer
- they aligned with realism / portraiture signals where possible
- they had stronger organizer quality and strategic value than weaker alternatives

## Current Opportunity Pool Used For MVP Matching

The current curated sample pool in `data/mvp/opportunities.csv` includes:

- `Viridian Artists Summer Juried Exhibition`
- `OPA 2026 National Juried Salon`
- `Mirroring Reality: Realism Today`
- `MvVO ART SHOW 2026`
- `Homiens Art Prize`

## Important Current Rule For MVP Processing

The MVP processor should not replace full analyst review for serious contacts.

Current practical rule:

- new Mailchimp-synced rows should enter `research_pending`
- recommendation email should happen only after the research runner promotes the row to `emailed_ready`

This keeps the system from sending low-signal outputs from an incomplete or overly narrow opportunity pool.

## Example Final Top 3 From Current Discussion

1. `Bowery Gallery – 35th Annual Art Competition`
2. `Prince Street Gallery – 2026 Juried Exhibition with Sharon Butler`
3. `First Street Gallery – 2026 National Juried Exhibition`

These were ranked based on:
- gallery credibility
- organizer context
- style relevance
- strategic value for getting into galleries and building reputation

## Files Updated During This Session

- [src/artist_resource_project/models.py](C:\Users\pweng\Documents\Artist opportunities\src\artist_resource_project\models.py)
- [src/artist_resource_project/workflow.py](C:\Users\pweng\Documents\Artist opportunities\src\artist_resource_project\workflow.py)
- [src/artist_resource_project/lead_sources.py](C:\Users\pweng\Documents\Artist opportunities\src\artist_resource_project\lead_sources.py)
- [tests/test_recommendation_pipeline.py](C:\Users\pweng\Documents\Artist opportunities\tests\test_recommendation_pipeline.py)
- [data/mvp/submissions.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\submissions.csv)
- [data/mvp/opportunities.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\opportunities.csv)
- [data/mvp/results.csv](C:\Users\pweng\Documents\Artist opportunities\data\mvp\results.csv)
- [scripts/sync_mailchimp.py](C:\Users\pweng\Documents\Artist opportunities\scripts\sync_mailchimp.py)
- [scripts/process_submissions.py](C:\Users\pweng\Documents\Artist opportunities\scripts\process_submissions.py)
- [scripts/send_result_emails.py](C:\Users\pweng\Documents\Artist opportunities\scripts\send_result_emails.py)
- [scripts/sync_then_process.ps1](C:\Users\pweng\Documents\Artist opportunities\scripts\sync_then_process.ps1)
- [scripts/mailchimp_sync_task.xml](C:\Users\pweng\Documents\Artist opportunities\scripts\mailchimp_sync_task.xml)
- [templates/artist_recommendation_email_template.md](C:\Users\pweng\Documents\Artist opportunities\templates\artist_recommendation_email_template.md)
- [.env.example](C:\Users\pweng\Documents\Artist opportunities\.env.example)

## Current Useful Outputs

- prototype UI:
  - [outputs/workflow_prototype.html](C:\Users\pweng\Documents\Artist opportunities\outputs\workflow_prototype.html)
- current public leads CSV:
  - [outputs/current_leads_2026-03-31.csv](C:\Users\pweng\Documents\Artist opportunities\outputs\current_leads_2026-03-31.csv)
- research workflow guide:
  - [docs/research_pending_workflow.md](C:\Users\pweng\Documents\Artist opportunities\docs\research_pending_workflow.md)
- daily operating checklist:
  - [docs/daily_checklist.md](C:\Users\pweng\Documents\Artist opportunities\docs\daily_checklist.md)

## Current Code State

- workflow models exist for Steps 1 through 7
- Step 2 has source-level collection summaries
- Step 3 verification now stores actual confirmed facts and source URL
- tests currently pass
- Framer -> Mailchimp -> local CSV sync path now exists
- local CSV processing now generates recommendation results
- direct email sending now works through Gmail SMTP
- HTML email now includes application links from explicit result columns
- new workflow decision: new submissions now go through the research runner before email send
- discovery is still the weak link; the practical current model is Codex-assisted live research for `research_pending` rows
- helper script exists to generate a research brief for one queued submission:
  - [scripts/generate_research_brief.py](C:\Users\pweng\Documents\Artist opportunities\scripts\generate_research_brief.py)
- the most important product value is now explicitly framed as AI-assisted opportunity review and artist matching, not just fast filtering or email automation

## Resume Prompt Suggestion

When reopening Codex later, use something like:

`Continue from SESSION_NOTES.md. Use the 7-step workflow, keep organizer review analyst-led, and continue expanding Step 2 for CaFE and ArtDeadline.`

For the current MVP automation path, a better resume prompt is:

`Continue from SESSION_NOTES.md. The current MVP flow is Framer -> Mailchimp -> submissions.csv -> run_research_pipeline.py -> results.csv -> send_result_emails.py. Improve discovery quality, verification quality, organizer review quality, and ranking quality without breaking the intermediate CSV stage files.`
