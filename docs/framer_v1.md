# Framer v1: Intake + Automated Email

This guide wires your Framer site to the private intake API so artists receive a **draft shortlist email** after submitting the form.

## Architecture

```text
Framer form submit
    -> Make.com or custom POST (recommended)
    -> POST https://your-api.example.com/v1/intake
    -> rank against verified opportunities in DATA_DIR
    -> Resend sends draft shortlist email to artist
```

Framer does not reliably host long-running backends on its own. The usual pattern is:

1. **Framer** collects the form UI
2. **Make.com** (or similar) forwards the submission to your API
3. **Railway / Render / Fly** runs this Python service from your private GitHub repo

## Required form fields

Use these field names so the webhook parser accepts them without extra mapping:

| Field | Type | Example |
|-------|------|---------|
| `name` | text | Alex Rivera |
| `email` | email | alex@example.com |
| `primary_medium` | text | oil painting |
| `style_description` | long text | contemporary figurative... |
| `themes` | text | memory, portraiture, identity |
| `budget_cap_usd` | number | 100 |
| `minimum_days_until_deadline` | number | 10 |
| `career_goal` | text | exhibition exposure and gallery visibility |
| `eligible_regions` | text | US |
| `career_stage` | text | emerging |

Lists can be comma-separated (`memory, portraiture`) or sent as JSON arrays.

## Framer setup (recommended path)

### 1. Build the form in Framer

- Add a **Form** component or a custom form layout.
- Match the field names in the table above.
- Add a short disclaimer on the page:
  - automated draft shortlist
  - confirm deadlines/fees on official listings
  - not a final curator review

### 2. Connect with Make.com

Because Framer form webhooks vary by plan, Make.com is the most dependable v1 bridge:

1. Create a **Custom webhook** module in Make.com.
2. Connect your Framer form to trigger that scenario (Framer Zapier/Make integration, or form redirect/webhook if available on your plan).
3. Add an **HTTP > Make a request** module:
   - URL: `https://YOUR_HOST/v1/intake`
   - Method: `POST`
   - Headers:
     - `Content-Type: application/json`
     - `X-Intake-Secret: YOUR_SECRET`
   - Body: map Framer fields to the JSON keys listed above.

### 3. Alternative: custom code embed

If you prefer a direct POST from Framer, add a small code component that submits to your API. Keep the secret out of public browser code — use Make.com instead unless you add a server-side proxy.

## Deploy the API (private GitHub -> Railway)

1. Push this repo to a **private** GitHub repository.
2. Create a Railway project from that repo.
3. Set environment variables from `.env.example`.
4. Verify Resend:
   - add and verify your sending domain
   - set `EMAIL_FROM` to an address on that domain
5. Deploy and copy the public URL.

Health check:

```text
GET https://YOUR_HOST/health
```

Test intake without email:

```powershell
curl -X POST https://YOUR_HOST/v1/intake/preview `
  -H "Content-Type: application/json" `
  -H "X-Intake-Secret: YOUR_SECRET" `
  -d "{\"name\":\"Test Artist\",\"email\":\"you@example.com\",\"primary_medium\":\"oil painting\",\"style_description\":\"contemporary figurative painting\",\"themes\":\"memory, portraiture\",\"budget_cap_usd\":100,\"minimum_days_until_deadline\":10,\"career_goal\":\"gallery visibility\",\"eligible_regions\":\"US\",\"career_stage\":\"emerging\"}"
```

Live intake (sends email):

```powershell
curl -X POST https://YOUR_HOST/v1/intake `
  -H "Content-Type: application/json" `
  -H "X-Intake-Secret: YOUR_SECRET" `
  -d "{...same body...}"
```

## What artists receive

- Subject: `Your draft open-call shortlist — {name}`
- Up to `INTAKE_TOP_K` opportunities (default 5)
- Fit summary per listing
- Application link and caution notes
- Clear language that this is an automated draft

## What stays private

Do **not** commit to GitHub:

- `.env`
- artist uploads (add image storage in v2)
- raw submission exports with personal data

Optional: store submissions in Railway volume or Supabase in a later version.

## v2 ideas

- image uploads (Cloudflare R2 / S3)
- admin dashboard for organizer review
- switch `DATA_DIR` to a maintained verified-opportunities dataset updated weekly
