# Artist Resource Project

File-based workflow and API for helping painters find best-fit open calls.

## What it does

- Accepts structured artist intake (Step 1 + Step 5 fields)
- Ranks verified opportunities with deterministic scoring
- Optionally uses OpenAI for fit explanations
- Sends a **draft shortlist email** via Resend (v1 public intake)

## Repository layout

- `docs/project_overview.md` — product and 7-step workflow
- `docs/framer_v1.md` — Framer + Make.com + Railway setup
- `data/seed/` — opportunity fixtures for prototyping
- `schemas/` — JSON schemas
- `src/artist_resource_project/` — pipeline, intake API, email delivery
- `tests/` — ranking and intake tests

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

## v1 deployment (private GitHub)

1. Create a **private** GitHub repo and push this project.
2. Deploy to Railway/Render using `Dockerfile`.
3. Set env vars from `.env.example`.
4. Connect your Framer form through Make.com to `POST /v1/intake`.

See [docs/framer_v1.md](docs/framer_v1.md) for field names and webhook mapping.

## AI integration

Set `OPENAI_API_KEY` for richer fit explanations. Without it, deterministic fallback text is used.

## Data boundaries

- Commit code, schemas, and verified opportunity templates.
- Do **not** commit `.env`, artist submissions, or uploaded artwork.
