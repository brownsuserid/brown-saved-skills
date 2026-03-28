# Monitoring Job Listings

> **Browser automation:** Uses Playwright MCP tools. See `_shared/references/using-playwright-mcp.md`.
> Output: Weekly Obsidian digest at `$OBSIDIAN_VAULT/2-Areas/Career/Job Search Weekly - {date}.md`
> Cadence: **Weekly cron** (Monday mornings) or on-demand

## Overview

Passively monitors job boards for business systems analyst / automation / AI strategy roles matching Aaron's profile. Scores listings against configurable criteria, deduplicates against previously seen listings, and produces a weekly digest in Obsidian.

**Use cases:**
- "Run this week's job search"
- "Are there any new automation roles this week?"
- "Check for AI strategy positions in Phoenix or remote"

---

## Phase 1: Load Config and Build Queries

Read search configuration from:
```
~/.openclaw/skills/maintaining-systems/data/job-search/config.yaml
```

The config defines job titles, locations, negative keywords, and scoring weights. Generate one search query per title combination:

```
"Business Systems Analyst" Phoenix AZ OR remote -junior -intern -"entry level"
"Automation Engineer" Phoenix AZ OR remote -junior -intern
"AI Operations Lead" remote -junior -intern
```

---

## Phase 2: Search Job Boards

### Primary Method: Scripts

Run the search script to execute queries and collect new listings:

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/monitoring-job-listings/search_jobs.py \
  --config ~/.openclaw/skills/maintaining-systems/data/job-search/config.yaml \
  --seen ~/.openclaw/skills/maintaining-systems/data/job-search/seen-listings.json
```

### Browser Alternative (MCP)

If the script fails or for platforms requiring browser interaction:

#### LinkedIn Jobs
1. `browser_navigate` → `https://www.linkedin.com/jobs/search/?keywords=AI+Automation+Engineer&location=Phoenix+AZ`
2. `browser_snapshot` → check for login wall; if needed, ask user to sign in
3. `browser_snapshot` → read job listing cards (title, company, location, link)
4. `browser_evaluate` → `() => window.scrollBy(0, 800)` to load more
5. `browser_snapshot` → extract additional listings

#### Indeed
1. `browser_navigate` → `https://www.indeed.com/jobs?q=AI+Automation&l=Phoenix+AZ`
2. `browser_snapshot` → read listing cards
3. Extract: title, company, location, link, snippet

#### Built In Arizona
1. `browser_navigate` → `https://www.builtinaz.com/jobs`
2. `browser_snapshot` → find search/filter inputs
3. `browser_type` → search for relevant terms
4. `browser_snapshot` → read results

For each platform, extract listing data and check against `seen-listings.json` for deduplication.

**Sources searched:**
- LinkedIn Jobs (web search)
- Indeed
- Glassdoor
- Built In Arizona
- Wellfound (startup roles)

**Deduplication:** Filter out any listing URLs already in `seen-listings.json`. Only new listings are output for scoring.

**Output JSON:**
```json
{
  "new_listings": [
    {
      "title": "Automation Engineer",
      "company": "Acme Corp",
      "location": "Phoenix, AZ",
      "url": "https://...",
      "source": "indeed",
      "description_snippet": "...",
      "found_date": "2026-02-17"
    }
  ],
  "total_new": 12,
  "total_seen_skipped": 47
}
```

---

## Phase 3: Score and Filter

Run the scoring script on each new listing:

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/monitoring-job-listings/score_listing.py \
  --listing '{"title": "...", "description_snippet": "..."}' \
  --config ~/.openclaw/skills/maintaining-systems/data/job-search/config.yaml
```

Or batch-score all new listings from Phase 2:

```bash
python3 search_jobs.py ... | \
python3 score_listing.py --batch --config config.yaml
```

**Scoring criteria** (from config):
- AI/automation focus in description: +3
- Leadership or strategy role: +2
- Location match (Phoenix metro or remote): +2
- Startup/small company: +1
- Consulting or advisory role: +1
- Salary range match (if disclosed): +1
- Junior/intern/entry-level keyword: -3
- Degree requirement Aaron may not meet: -2

**Threshold:** Only surface listings scoring `min_score` or above (default: 4).

---

## Phase 4: Generate Weekly Digest

Run the digest script to create an Obsidian note and update seen-listings.json:

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/monitoring-job-listings/generate_digest.py \
  --listings scored-listings.json \
  --seen ~/.openclaw/skills/maintaining-systems/data/job-search/seen-listings.json \
  --output "$OBSIDIAN_VAULT/2-Areas/Career"
```

**Creates:** `$OBSIDIAN_VAULT/2-Areas/Career/Job Search Weekly - 2026-02-17.md`

```markdown
---
date: 2026-02-17
type: job-search-digest
listings_found: 12
listings_surfaced: 4
---

# Job Search Weekly, 2026-02-17

| Score | Title | Company | Location | Source |
|-------|-------|---------|----------|--------|
| 7 | Automation Engineer | Acme Corp | Phoenix, AZ | [Indeed](https://...) |
| 6 | AI Strategy Lead | StartupCo | Remote | [LinkedIn](https://...) |
| 5 | Business Systems Analyst | BigCorp | Phoenix, AZ | [Glassdoor](https://...) |
| 4 | Process Automation Specialist | Agency | Remote | [Built In AZ](https://...) |

## Highlights

### Automation Engineer, Acme Corp (Score: 7)
...description snippet...

### AI Strategy Lead, StartupCo (Score: 6)
...
```

**Also updates:** `seen-listings.json` with all newly processed listing URLs (regardless of score) so they are not re-surfaced next week.

---

## Config File

Location: `~/.openclaw/skills/maintaining-systems/data/job-search/config.yaml`

```yaml
search_titles:
  - "Business Systems Analyst"
  - "Automation Engineer"
  - "AI Operations Lead"
  - "Process Automation"
  - "Digital Transformation Lead"
  - "AI Strategy"
  - "Enterprise Automation"

locations:
  - "Phoenix, AZ"
  - "Remote"

salary_min: 120000

negative_keywords:
  - "junior"
  - "intern"
  - "entry level"
  - "entry-level"

scoring_weights:
  ai_automation: 3
  leadership: 2
  location_match: 2
  startup: 1
  consulting: 1
  salary_match: 1

negative_weights:
  junior_role: -3
  degree_mismatch: -2

min_score: 4
```

---

## Guardrails

- **Never apply to jobs automatically**, only surface listings for Aaron's review
- **Never share search activity externally**, all data stays local
- **Never post Aaron's resume or profile** anywhere
- **Deduplication is required**, always check seen-listings.json before surfacing
- **Low-urgency**, if search fails (no internet, API limit), log and skip; do not retry aggressively

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `search_jobs.py` | Load config, generate search queries, collect new listings, deduplicate against seen-listings.json |
| `score_listing.py` | Score a listing (or batch) against config criteria; filter by min_score |
| `generate_digest.py` | Create Obsidian digest note from scored listings; update seen-listings.json |

---

## Integration

- **Trigger:** Weekly cron (Monday mornings) or on-demand
- **Cron:** `0 8 * * 1` (Monday 8 AM MST)
- **Output:** Obsidian note at `2-Areas/Career/`
- **State file:** `maintaining-systems/data/job-search/seen-listings.json`
- **Config:** `maintaining-systems/data/job-search/config.yaml`
- **Depends on:** `OBSIDIAN_VAULT` environment variable
