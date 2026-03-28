# Tracking Website Analytics

> Output: Formatted Markdown report to console; optionally saved to Obsidian
> Cadence: **On-demand** ("how is aaroneden.com doing?", "show me site analytics")

## Overview

Queries Google Analytics 4 and Google Search Console to produce a traffic report for aaroneden.com. Covers sessions, users, top pages, traffic sources, and top search queries.

**Use cases:**
- "How is aaroneden.com doing?"
- "Show me site analytics"
- "What are my top blog posts?"
- "What search queries drive traffic?"
- "How much organic traffic am I getting?"

---

## Phase 1: Fetch GA4 Analytics

Run the GA4 fetch script to get traffic overview, top pages, and traffic sources:

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/tracking-website-analytics/fetch_analytics.py \
  --config ~/.openclaw/skills/maintaining-systems/data/website-analytics/config.yaml \
  > /tmp/ga4.json
```

**Date range options:** `last_7_days` | `last_28_days` (default) | `last_90_days`

```bash
# Override date range:
python3 fetch_analytics.py --date-range last_7_days > /tmp/ga4.json
```

**Output JSON:**
```json
{
  "period": { "start": "2026-01-21", "end": "2026-02-17", "range": "last_28_days" },
  "overview": { "sessions": 1247, "users": 892, "pageviews": 2104, "bounce_rate": 0.58 },
  "top_pages": [ { "page": "/blog/agile-ai-manifesto/", "sessions": 234, "pageviews": 298 } ],
  "top_sources": [ { "source": "google", "medium": "organic", "sessions": 612 } ]
}
```

---

## Phase 2: Fetch Search Console Data

Run the Search Console fetch script to get top queries and their performance:

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/tracking-website-analytics/fetch_search_console.py \
  --config ~/.openclaw/skills/maintaining-systems/data/website-analytics/config.yaml \
  > /tmp/sc.json
```

**Output JSON:**
```json
{
  "period": { "start": "2026-01-18", "end": "2026-02-14", "range": "last_28_days" },
  "top_queries": [ { "query": "ai automation consultant phoenix", "clicks": 45, "impressions": 234, "ctr": 0.19, "position": 4.2 } ],
  "top_pages": [ { "page": "https://aaroneden.com/blog/...", "clicks": 38, "impressions": 89 } ]
}
```

---

## Phase 3: Generate Report

Combine both data sources into a readable Markdown report:

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/tracking-website-analytics/generate_report.py \
  --ga4-file /tmp/ga4.json \
  --sc-file /tmp/sc.json
```

**Output to console (default):**
```
## aaroneden.com Analytics, Jan 21 – Feb 17, 2026 (28 days)

### Traffic Overview
Sessions:    1,247
Users:         892
Pageviews:   2,104
Bounce rate:  58.0%

### Top Pages (GA4)
 1. /blog/agile-ai-manifesto/    234 sessions  (18.7%)
 2. /coaching-programs/          198 sessions  (15.9%)
...

### Traffic Sources
 1. google / organic    612  (49.1%)
 2. direct              287  (23.0%)
...

### Top Search Queries (Search Console)
Query                                               Clicks    Impr    Pos
---------------------------------------------------------------
ai automation consultant phoenix                        45     234    4.2
brainbridge ai                                          38      89    1.1
```

**Save to Obsidian instead:**
```bash
python3 generate_report.py --ga4-file /tmp/ga4.json --sc-file /tmp/sc.json --output obsidian
```

**Both console and Obsidian:**
```bash
python3 generate_report.py --ga4-file /tmp/ga4.json --sc-file /tmp/sc.json --output both
```

Obsidian note path: `$OBSIDIAN_VAULT/2-Areas/Personal Site/Analytics - {date}.md`

---

## Full Pipeline (One-liner)

```bash
cd ~/.openclaw/skills/maintaining-systems/scripts/tracking-website-analytics && \
python3 fetch_analytics.py > /tmp/ga4.json && \
python3 fetch_search_console.py > /tmp/sc.json && \
python3 generate_report.py --ga4-file /tmp/ga4.json --sc-file /tmp/sc.json
```

---

## Interpreting Results

**Traffic Overview:**
- Sessions trending up → content or SEO is working
- High bounce rate (>70%) on key pages → investigate content/UX
- Users vs sessions ratio → repeat visitors if sessions > users

**Top Pages:**
- High-traffic pages with few SC clicks = good internal/direct traffic, low search visibility
- Low-traffic pages with high Search Console impressions = ranking opportunity

**Traffic Sources:**
- Organic > 50% is healthy for a personal brand site
- "direct" traffic often means email list or bookmarks, a positive signal
- Social spikes usually correspond to a specific post or share

**Search Queries:**
- Position 4–10 = "striking distance", worth optimizing for first page
- High impressions, low CTR = title/description isn't compelling
- Branded queries (your name) confirm brand awareness growth

---

## One-Time Setup

### 1. Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. "Aaron Analytics")
3. Enable APIs:
   - **Google Analytics Data API** (for GA4)
   - **Google Search Console API**
4. Go to **IAM & Admin → Service Accounts** → Create service account
5. Grant no project roles (not needed)
6. Create a JSON key: Actions → Manage Keys → Add Key → JSON
7. Save to: `~/.openclaw/secrets/ga4-service-account.json`
8. Protect it: `chmod 600 ~/.openclaw/secrets/ga4-service-account.json`

### 2. Grant GA4 Access

1. In GA4: **Admin → Account Access Management**
2. Click **+** → Add users
3. Paste the service account email (from the JSON file, `client_email` field)
4. Role: **Viewer**

### 3. Grant Search Console Access

1. In Search Console: **Settings → Users and permissions**
2. Add user → paste the service account email
3. Permission: **Full** (required to query analytics data)

### 4. Configure `config.yaml`

Edit `~/.openclaw/skills/maintaining-systems/data/website-analytics/config.yaml`:

```yaml
# GA4 property ID: GA4 Admin → Property Settings → Property ID
property_id: "properties/123456789"

# Search Console property (check console for exact format)
site_url: "sc-domain:aaroneden.com"

credentials_file: "~/.openclaw/secrets/ga4-service-account.json"
```

**Finding your GA4 Property ID:**
GA4 → Admin → Property Settings → look for "Property ID" (numeric only, e.g. `123456789`)
Config value: `"properties/123456789"`

**Finding your Search Console site URL:**
Search Console → left sidebar shows your property URL exactly as it should appear in config.
Domain properties appear as `sc-domain:yourdomain.com`.

### 5. Install Dependencies

```bash
uv pip install google-analytics-data google-api-python-client google-auth pyyaml
```

### 6. Test the Setup

```bash
python3 ~/.openclaw/skills/maintaining-systems/scripts/tracking-website-analytics/fetch_analytics.py \
  --date-range last_7_days --json
```

Expected: JSON with overview, top_pages, top_sources.

---

## Config Reference

Location: `~/.openclaw/skills/maintaining-systems/data/website-analytics/config.yaml`

| Key | Description |
|-----|-------------|
| `property_id` | GA4 property ID in format `properties/XXXXXXXXX` |
| `site_url` | Search Console property (e.g. `sc-domain:aaroneden.com`) |
| `credentials_file` | Path to service account JSON key |
| `defaults.date_range` | Default period: `last_7_days`, `last_28_days`, or `last_90_days` |
| `limits.top_pages` | Max pages to return (default: 10) |
| `limits.top_queries` | Max queries to return (default: 20) |
| `limits.top_sources` | Max sources to return (default: 10) |

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `fetch_analytics.py` | Query GA4 Data API for overview, top pages, and traffic sources → JSON |
| `fetch_search_console.py` | Query Search Console API for top queries and pages → JSON |
| `generate_report.py` | Combine GA4 + SC JSON into formatted Markdown report |

---

## Guardrails

- **Read-only**, these scripts never modify GA4, Search Console, or any site data
- **No data stored**, results are not persisted unless `--output obsidian` is used
- **Credentials stay local**, service account JSON never leaves `~/.openclaw/secrets/`
- **On-demand only**, no automated sending; Aaron reviews the report directly
- If an API call fails (quota, auth, network), the script exits with a clear error, do not retry in a loop
