# Project Overview

## Product Goal

Help painting artists find the best-fit opportunities through a repeatable human-guided review process, not just an automatic ranking pass over a static pool.

## Current 7-Step Workflow

1. Collect hard filters
   - medium
   - budget
   - eligible region
   - minimum time before deadline
2. Collect all candidate opportunities that meet those filters
3. Verify the candidate list
   - live page
   - real opportunity
   - confirmed deadline, fee, eligibility, and application link
4. Review the organizer or gallery
   - website
   - past programming
   - artists they have shown
   - social presence
   - outside references
   - fee and terms risk
   - juror credibility
5. Collect richer artist information
   - style description
   - themes
   - career stage
   - career goal
   - up to 10 artwork images
6. Assess fit
   - medium fit
   - style fit
   - theme fit
   - career fit
   - organizer-context fit
   - strategic value fit
   - competitiveness fit
7. Rank the final top 3

## Why This Structure Matters

The important judgment in this product is not only whether an opportunity technically allows painting. The hard part is deciding:
- whether the opportunity is real
- whether the organizer is credible
- whether the organizer's context matches the artist's work and goals
- whether the opportunity is strategically worth applying to

That is why Steps 4, 5, and 6 are first-class parts of the workflow.

## Quality Control For Steps 4, 5, And 6

Step 4 is guided by the [organizer review](C:\Users\pweng\Documents\Artist opportunities\organizer review) checklist.

Step 5 uses a dedicated artist-intake record instead of mixing hard filters and subjective fit data into one form.

Step 6 uses a structured match record so the reasoning is explicit and repeatable instead of ad hoc.

## Technical Direction

The current codebase keeps:
- file-based seed fixtures for prototyping
- a filtering and scoring prototype for baseline testing
- structured records for the newer criteria-driven workflow

The near-term direction is:
- keep source discovery flexible
- keep verification manual or assisted
- hard-code the workflow before expanding automation
