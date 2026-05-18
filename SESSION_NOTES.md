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

## Current Useful Outputs

- prototype UI:
  - [outputs/workflow_prototype.html](C:\Users\pweng\Documents\Artist opportunities\outputs\workflow_prototype.html)
- current public leads CSV:
  - [outputs/current_leads_2026-03-31.csv](C:\Users\pweng\Documents\Artist opportunities\outputs\current_leads_2026-03-31.csv)

## Current Code State

- workflow models exist for Steps 1 through 7
- Step 2 has source-level collection summaries
- Step 3 verification now stores actual confirmed facts and source URL
- tests currently pass

## Resume Prompt Suggestion

When reopening Codex later, use something like:

`Continue from SESSION_NOTES.md. Use the 7-step workflow, keep organizer review analyst-led, and continue expanding Step 2 for CaFE and ArtDeadline.`
