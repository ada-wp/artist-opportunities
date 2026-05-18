from __future__ import annotations

from pathlib import Path


PROTOTYPE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Artist Opportunity Workflow Prototype</title>
  <style>
    :root {
      --bg: #f3efe6;
      --panel: rgba(255, 250, 242, 0.92);
      --ink: #1f1a17;
      --muted: #64584f;
      --line: rgba(31, 26, 23, 0.12);
      --accent: #b6572f;
      --accent-soft: rgba(182, 87, 47, 0.14);
      --shadow: 0 24px 70px rgba(53, 39, 26, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(182, 87, 47, 0.18), transparent 28%),
        radial-gradient(circle at right 15%, rgba(52, 95, 77, 0.15), transparent 25%),
        linear-gradient(180deg, #efe8dd 0%, var(--bg) 48%, #eee7db 100%);
      min-height: 100vh;
    }

    .shell {
      width: min(1180px, calc(100% - 40px));
      margin: 32px auto 56px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.35fr 0.9fr;
      gap: 22px;
      margin-bottom: 24px;
    }

    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }

    .hero-main {
      padding: 34px 34px 26px;
      position: relative;
      overflow: hidden;
    }

    .hero-main::after {
      content: "";
      position: absolute;
      width: 260px;
      height: 260px;
      right: -40px;
      top: -70px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(182, 87, 47, 0.18), transparent 68%);
      pointer-events: none;
    }

    .eyebrow {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 20px;
    }

    h1 {
      margin: 0;
      font-size: clamp(34px, 5vw, 58px);
      line-height: 0.95;
      font-weight: 600;
      max-width: 10ch;
    }

    .hero-copy {
      margin: 18px 0 0;
      max-width: 58ch;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.7;
    }

    .hero-side {
      padding: 28px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .metric {
      padding: 16px 18px;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.45);
    }

    .metric strong {
      display: block;
      font-size: 22px;
      margin-bottom: 4px;
    }

    .metric span {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    .layout {
      display: grid;
      grid-template-columns: 0.95fr 1.25fr;
      gap: 22px;
      align-items: start;
    }

    .stack {
      display: grid;
      gap: 22px;
    }

    .section {
      padding: 24px;
    }

    .section h2 {
      margin: 0 0 8px;
      font-size: 24px;
      font-weight: 600;
    }

    .section p {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 15px;
    }

    .field-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 18px;
    }

    .field, .textarea, .upload-box, .candidate-card, .review-card, .match-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.52);
    }

    .field {
      padding: 14px 14px 16px;
      min-height: 108px;
    }

    .field-label {
      display: block;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .chip {
      padding: 8px 12px;
      border-radius: 999px;
      background: white;
      border: 1px solid rgba(31, 26, 23, 0.08);
      font-size: 14px;
    }

    .textarea {
      margin-top: 14px;
      padding: 18px;
    }

    .upload-box {
      margin-top: 14px;
      padding: 18px;
    }

    .upload-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      margin-top: 14px;
    }

    .upload-tile {
      aspect-ratio: 1 / 1;
      border-radius: 16px;
      background:
        linear-gradient(135deg, rgba(182, 87, 47, 0.22), rgba(255, 255, 255, 0.8)),
        linear-gradient(45deg, rgba(31, 26, 23, 0.06), transparent);
      border: 1px solid rgba(31, 26, 23, 0.08);
      display: flex;
      align-items: end;
      justify-content: center;
      padding: 10px;
      color: var(--muted);
      font-size: 12px;
    }

    .list {
      display: grid;
      gap: 14px;
      margin-top: 18px;
    }

    .candidate-card, .review-card, .match-card {
      padding: 18px;
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 10px;
    }

    .card-top h3 {
      margin: 0;
      font-size: 19px;
      line-height: 1.2;
    }

    .muted {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
    }

    .flag {
      border-radius: 999px;
      padding: 8px 12px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      white-space: nowrap;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .meta span {
      background: white;
      border: 1px solid rgba(31, 26, 23, 0.08);
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 13px;
    }

    .split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 14px;
    }

    .mini-list {
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 14px;
    }

    .ranking {
      counter-reset: rank;
      display: grid;
      gap: 16px;
      margin-top: 18px;
    }

    .rank-card {
      position: relative;
      padding: 20px 20px 20px 78px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.6);
    }

    .rank-card::before {
      counter-increment: rank;
      content: counter(rank);
      position: absolute;
      left: 20px;
      top: 18px;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: var(--ink);
      color: white;
      font-size: 18px;
    }

    .rank-card h3 {
      margin: 0 0 10px;
      font-size: 22px;
    }

    .footer-note {
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }

    @media (max-width: 980px) {
      .hero, .layout {
        grid-template-columns: 1fr;
      }
      .upload-grid {
        grid-template-columns: repeat(3, 1fr);
      }
    }

    @media (max-width: 700px) {
      .shell {
        width: min(100% - 22px, 100%);
        margin-top: 18px;
      }
      .hero-main, .hero-side, .section {
        padding: 20px;
      }
      .field-grid, .split {
        grid-template-columns: 1fr;
      }
      .upload-grid {
        grid-template-columns: repeat(2, 1fr);
      }
      .rank-card {
        padding-left: 20px;
        padding-top: 72px;
      }
      .rank-card::before {
        left: 20px;
        top: 18px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <article class="card hero-main">
        <div class="eyebrow">Prototype Workflow</div>
        <h1>Artist Opportunity Match Review</h1>
        <p class="hero-copy">
          This prototype reflects the current 7-step process: collect hard filters, gather every matching candidate,
          verify the shortlist, review the organizer, collect the artist's deeper profile, assess fit, and only then
          produce a final top 3.
        </p>
      </article>
      <aside class="card hero-side">
        <div class="metric">
          <strong>Step 1</strong>
          <span>Structured filter form with multi-select mediums, opportunity types, regions, and timing constraints.</span>
        </div>
        <div class="metric">
          <strong>Step 4</strong>
          <span>Organizer review is analyst-led and follows the organizer review checklist, not user input.</span>
        </div>
        <div class="metric">
          <strong>Step 7</strong>
          <span>Final ranking is limited to a strategic top 3 after verification and fit assessment.</span>
        </div>
      </aside>
    </section>

    <section class="layout">
      <div class="stack">
        <section class="card section">
          <h2>Step 1. Search Filters</h2>
          <p>The artist controls practical constraints only. The form supports multiple values where real artists need them.</p>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">Medium Preferences</span>
              <div class="chips">
                <span class="chip">Oil Painting</span>
                <span class="chip">Drawing</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Opportunity Types</span>
              <div class="chips">
                <span class="chip">Open Call</span>
                <span class="chip">Residency</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Budget Cap</span>
              <div class="chips">
                <span class="chip">$100</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Minimum Days Before Deadline</span>
              <div class="chips">
                <span class="chip">10 days</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Eligible Regions</span>
              <div class="chips">
                <span class="chip">US</span>
                <span class="chip">International</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Format / Scope</span>
              <div class="chips">
                <span class="chip">In Person</span>
                <span class="chip">National</span>
              </div>
            </div>
          </div>
        </section>

        <section class="card section">
          <h2>Step 5. Artist Intake</h2>
          <p>This is where the artist gives the richer information needed for Step 6 matching.</p>
          <div class="textarea">
            <span class="field-label">Style Description</span>
            <p class="muted">
              Contemporary figurative painting with an atelier foundation, shaped by tonal sensitivity,
              painterly editing, atmosphere, and selective ambiguity.
            </p>
          </div>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">Themes</span>
              <div class="chips">
                <span class="chip">Figure</span>
                <span class="chip">Psychology</span>
                <span class="chip">Atmosphere</span>
                <span class="chip">Quiet Tension</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Career Goal</span>
              <div class="chips">
                <span class="chip">Get Into Galleries</span>
                <span class="chip">Build Reputation</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Target Visibility</span>
              <div class="chips">
                <span class="chip">Gallery Exposure</span>
                <span class="chip">Reputation Building</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label">Preferred Contexts</span>
              <div class="chips">
                <span class="chip">Commercial Gallery</span>
                <span class="chip">Nonprofit</span>
              </div>
            </div>
          </div>
          <div class="upload-box">
            <span class="field-label">Upload Up To 10 Works</span>
            <div class="upload-grid">
              <div class="upload-tile">Work 1</div>
              <div class="upload-tile">Work 2</div>
              <div class="upload-tile">Work 3</div>
              <div class="upload-tile">Work 4</div>
              <div class="upload-tile">Work 5</div>
              <div class="upload-tile">Work 6</div>
              <div class="upload-tile">Work 7</div>
              <div class="upload-tile">Work 8</div>
              <div class="upload-tile">Work 9</div>
              <div class="upload-tile">Work 10</div>
            </div>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="card section">
          <h2>Step 2. Candidate Pool</h2>
          <p>This screen stores every opportunity that passes the hard filters. No ranking happens here.</p>
          <div class="list">
            <article class="candidate-card">
              <div class="card-top">
                <div>
                  <h3>2026 National Juried Exhibition</h3>
                  <div class="muted">First Street Gallery • NYFA lead</div>
                </div>
                <span class="flag">Candidate</span>
              </div>
              <div class="meta">
                <span>Deadline: Apr 15, 2026</span>
                <span>Fee: $40</span>
                <span>US eligible</span>
                <span>Painting / Oils</span>
              </div>
            </article>
            <article class="candidate-card">
              <div class="card-top">
                <div>
                  <h3>2026 Juried Exhibition with Sharon Butler</h3>
                  <div class="muted">Prince Street Gallery • NYFA lead</div>
                </div>
                <span class="flag">Candidate</span>
              </div>
              <div class="meta">
                <span>Deadline: Apr 21, 2026</span>
                <span>Fee: $45</span>
                <span>US eligible</span>
                <span>Painting</span>
              </div>
            </article>
            <article class="candidate-card">
              <div class="card-top">
                <div>
                  <h3>NIGHT MOVES</h3>
                  <div class="muted">Art Fluent • NYFA lead</div>
                </div>
                <span class="flag">Candidate</span>
              </div>
              <div class="meta">
                <span>Deadline: Apr 17, 2026</span>
                <span>Fee: $25</span>
                <span>Worldwide</span>
                <span>Painting / Drawing</span>
              </div>
            </article>
          </div>
        </section>

        <section class="card section">
          <h2>Step 4. Organizer Review</h2>
          <p>This section is analyst-only. It follows the organizer review checklist instead of asking the artist to judge organizer quality.</p>
          <div class="list">
            <article class="review-card">
              <div class="card-top">
                <div>
                  <h3>First Street Gallery</h3>
                  <div class="muted">Chelsea gallery with deep exhibition history and clear institutional signals.</div>
                </div>
                <span class="flag">Strong Signal</span>
              </div>
              <div class="split">
                <div>
                  <span class="field-label">Good Signs</span>
                  <ul class="mini-list">
                    <li>Real physical address and active gallery program</li>
                    <li>Long exhibition history and artist roster</li>
                    <li>Linked social and press references</li>
                  </ul>
                </div>
                <div>
                  <span class="field-label">Watchouts</span>
                  <ul class="mini-list">
                    <li>Need prospectus review for final accepted-artist costs</li>
                    <li>High competitiveness</li>
                  </ul>
                </div>
              </div>
            </article>
            <article class="review-card">
              <div class="card-top">
                <div>
                  <h3>Art Fluent</h3>
                  <div class="muted">Legitimate but clearly more fee-driven and online-exhibition-based than the gallery-led options.</div>
                </div>
                <span class="flag">Mixed Signal</span>
              </div>
              <div class="split">
                <div>
                  <span class="field-label">Good Signs</span>
                  <ul class="mini-list">
                    <li>Clear website and recurring call structure</li>
                    <li>Visible prospectuses and accepted artists</li>
                  </ul>
                </div>
                <div>
                  <span class="field-label">Red Flags</span>
                  <ul class="mini-list">
                    <li>Online exhibition context has lower strategic value</li>
                    <li>Fee-driven call model needs caution</li>
                  </ul>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="card section">
          <h2>Step 6 + 7. Match And Final Top 3</h2>
          <p>Only verified, organizer-reviewed candidates move into the final fit assessment and ranking.</p>
          <div class="list">
            <article class="match-card">
              <div class="card-top">
                <div>
                  <h3>Match Assessment Snapshot</h3>
                  <div class="muted">Prince Street Gallery</div>
                </div>
                <span class="flag">Strong Match</span>
              </div>
              <div class="meta">
                <span>Medium Fit: High</span>
                <span>Style Fit: High</span>
                <span>Career Fit: High</span>
                <span>Strategic Value: High</span>
                <span>Competitiveness: High</span>
              </div>
              <p class="footer-note">
                Strong for an emerging figurative painter seeking serious gallery exposure and reputation-building,
                especially in a painting-literate context.
              </p>
            </article>
          </div>

          <div class="ranking">
            <article class="rank-card">
              <h3>Prince Street Gallery</h3>
              <p class="muted">Best strategic fit for an emerging figurative painter trying to enter galleries and build reputation.</p>
            </article>
            <article class="rank-card">
              <h3>First Street Gallery</h3>
              <p class="muted">Strong Chelsea juried context with serious exhibition value and credible organizer signals.</p>
            </article>
            <article class="rank-card">
              <h3>LBIF Plein Air Plus</h3>
              <p class="muted">Credible institution and worthwhile exposure, though less directly aligned than the top gallery-led options.</p>
            </article>
          </div>
        </section>
      </div>
    </section>
  </main>
</body>
</html>
"""


def write_ui_prototype(output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PROTOTYPE_HTML, encoding="utf-8")
    return path
