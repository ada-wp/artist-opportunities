# Artist Resource Project

File-based workflow and automation for helping artists find best-fit open calls.

## What it does

- Accepts structured artist intake
- Syncs new records from Mailchimp into local CSV workflow files
- Runs staged research with intermediate CSV outputs
- Optionally uses OpenAI for richer fit explanations
- Sends recommendation emails through Gmail SMTP or Resend

## Repository layout

- `docs/project_overview.md` - product and 7-step workflow
- `docs/framer_v1.md` - Framer + Make.com + Railway setup
- `data/mvp/` - current CSV-based workflow and stage outputs
- `data/seed/` - opportunity fixtures for prototyping
- `schemas/` - JSON schemas
- `scripts/` - Mailchimp sync, research runner, and email automation
- `src/artist_resource_project/` - pipeline, intake API, email delivery
- `templates/` - reusable email template reference
- `tests/` - ranking and intake tests

## Local setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,api]
copy .env.example .env
```

Run tests:

```powershell
pytest
```

Run the intake API locally:

```powershell
$env:INTAKE_WEBHOOK_SECRET="dev-secret"
$env:EMAIL_FROM="you@verified-domain.com"
$env:RESEND_API_KEY="re_xxx"
uvicorn artist_resource_project.api:app --reload --port 8000
```

CLI ranking for seed artists:

```powershell
python -m artist_resource_project.cli --artist-id painter_001
```

Run the current local automation wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\pweng\Documents\Artist opportunities\scripts\sync_then_process.ps1"
```

Prepare the daily research queue in one command:

```powershell
py scripts\sync_mailchimp_and_generate_briefs.py --only-new
```

Generate briefs in bulk for every submission row that already has a medium value:

```powershell
py scripts\sync_mailchimp_and_generate_briefs.py --all-with-medium
```

## v1 deployment (private GitHub)

1. Create a private GitHub repo and push this project.
2. Deploy to Railway/Render using `Dockerfile`.
3. Set env vars from `.env.example`.
4. Connect your Framer form through Make.com to `POST /v1/intake`.

See `docs/framer_v1.md` for field names and webhook mapping.

## Current automation path

The current local flow is:

1. Framer collects artist intake
2. Mailchimp stores the audience record
3. `scripts/sync_mailchimp.py` syncs contacts into `data/mvp/submissions.csv`
4. `scripts/sync_mailchimp_and_generate_briefs.py` can be used as the operator entry point to sync and create brief files for all `research_pending` rows
5. `scripts/run_research_pipeline.py` processes `research_pending` rows and writes:
   - `research_candidates.csv`
   - `verification_reviews.csv`
   - `organizer_reviews.csv`
   - `match_assessments.csv`
   - `results.csv`
6. `scripts/send_result_emails.py` sends emails only for rows that reach `emailed_ready`

## AI integration

Set `OPENAI_API_KEY` for richer fit explanations. Without it, deterministic fallback text is used.

## Data boundaries

- Commit code, schemas, templates, and verified opportunity templates.
- Do not commit `.env`, artist submissions, or uploaded artwork.
