---
description: Scrapes weekly engagement metrics from Aaron's LinkedIn accounts (Personal, BB, AITB) using MCP browser tools and logs them to a Google Sheet.
---

# Scraping LinkedIn Metrics

> **Browser automation:** Uses Playwright MCP tools. See `_shared/references/using-playwright-mcp.md`.

This skill uses MCP browser tools to navigate LinkedIn, scrape weekly page metrics for Aaron's three primary profiles, and append the results to a Google Sheet.

## 1. Prerequisites

- The `gog sheets` CLI must be configured for `aaroneden77@gmail.com` to write to the tracking sheet.

## 2. Scraping Process

### Open LinkedIn

1. `browser_navigate` → `https://www.linkedin.com/`
2. `browser_snapshot` → check if login is required
   - If login wall: tell user "LinkedIn needs authentication. Please sign in."
   - `browser_snapshot` → wait for login to complete

### Scrape Personal Profile

1. `browser_navigate` → `https://www.linkedin.com/in/aaroneden/` (then find analytics link)
2. `browser_snapshot` → find the analytics section or "Show all analytics" link
3. `browser_click` → ref for analytics link
4. `browser_snapshot` → extract last 7 days metrics:
   - Post Impressions
   - Profile Viewers
   - Search Appearances

### Scrape Brain Bridge (BB) Page

1. `browser_navigate` → `https://www.linkedin.com/company/brainbridgeapp/admin/analytics/`
2. `browser_snapshot` → check for admin access
3. `browser_snapshot` → extract metrics:
   - Unique visitors
   - New followers
   - Post impressions

### Scrape AI Trailblazers (AITB) Page

1. `browser_navigate` → `https://www.linkedin.com/company/aitrailblazers/admin/analytics/`
2. `browser_snapshot` → extract metrics:
   - Unique visitors
   - New followers
   - Post impressions

**Tip:** If metrics aren't visible in the initial snapshot, look for tab controls (e.g., "Visitors", "Followers", "Content") and click through each to extract the relevant numbers.

## 3. Data Formatting

Format the collected data into a clean structure:

Date | Account | Impressions | Views/Visitors | New Followers/Searches
--- | --- | --- | --- | ---
[Today] | Personal | [X] | [Y] | [Z]
[Today] | Brain Bridge | [X] | [Y] | [Z]
[Today] | AI Trailblazers | [X] | [Y] | [Z]

## 4. Logging to Google Sheets

Append these rows to the tracking sheet (`1COfdpZV_Q26N2THTqBZ6bktcAmuv--pekvYhcsq50uU`) using the `gog` CLI.

1. **Format the Command:**
   Construct a `gog sheets append` command. You can pass multiple rows as arguments, where cells are separated by the pipe character `|`.

   *Example:*
   ```bash
   gog sheets append 1COfdpZV_Q26N2THTqBZ6bktcAmuv--pekvYhcsq50uU Sheet1 \
       "2026-02-21|Personal|1500|300|15" \
       "2026-02-21|Brain Bridge|800|120|5" \
       "2026-02-21|AI Trailblazers|2000|500|20" \
       --account aaroneden77@gmail.com
   ```

2. **Execute the Command:**
   Run the command in your available terminal environments to commit the data.

## 5. Reporting

Send a brief summary of the week's metrics to Aaron via Telegram so he knows the job ran successfully.
