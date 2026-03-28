# Ingesting Gmail Digests

> Scripts: `~/.openclaw/skills/maintaining-relationships/scripts/ingesting-gmail-digests/`
> Cadence: **Weekly** (part of Friday curation workflow)
> Account: `aaroneden77@gmail.com`

## Overview

Pull AI newsletter digest emails from Gmail using the `gog` CLI, extract article links and summaries, and create individual content item notes in Obsidian. Emails are identified by the Gmail label `digest` which Aaron applies to his AI newsletter subscriptions.

**Use cases:**
- Weekly ingestion as part of the full curation workflow
- "Pull this week's AI newsletters"
- "Check my digest emails"

---

## Phase 1: Gather Digest Emails

Run the gather script to search Gmail for recent digest-labeled emails:

```bash
source ~/.openclaw/skills/_shared/config.sh
bash ~/.openclaw/skills/maintaining-relationships/scripts/ingesting-gmail-digests/gather-ai-digests.sh [days]
```

- Default: last 7 days
- Optional argument: number of days to look back
- Output: JSON file path with email metadata and bodies

The script uses `gog gmail messages search` with the query `label:digest newer_than:{days}d` to find digest emails.

---

## Phase 2: Check Dedup Manifest

Before creating content items, check the dedup manifest:

```bash
source ~/.openclaw/skills/_shared/config.sh
cat "$CLAWD_MEMORY/ai-content-manifest.json" 2>/dev/null || echo '{"youtube_ids":[],"gmail_ids":[]}'
```

Skip any email whose `message_id` is already in the `gmail_ids` array.

---

## Phase 3: Extract Content Items

For each new digest email, extract individual articles/items:

1. Read the email body from the gathered JSON
2. Parse out individual article entries -- look for:
   - Headlines with URLs
   - Brief descriptions or summaries
   - Author/source attributions
3. For each extracted article, create an Obsidian content item note

### Content Item Format

Create files at: `$OBSIDIAN_AI_CONTENT/{YYYY-Www}--{slug}.md`

Where `{slug}` is a kebab-case version of the article title (max 50 chars).

```markdown
---
source: gmail-digest
source_id: "{gmail_message_id}"
newsletter: "{newsletter name}"
title: "{article title}"
url: "{article url}"
creator: "{author or publication}"
published: {YYYY-MM-DD}
ingested: {YYYY-MM-DD}
score: null
score_breakdown: null
status: ingested
social_flagged: false
---

## Summary

{1-2 sentence summary extracted from the newsletter description}

## Source Context

From **{newsletter name}** ({date}): {brief context of how the newsletter described this item}
```

---

## Phase 4: Update Dedup Manifest

After processing all emails, add their message IDs to the manifest:

```bash
source ~/.openclaw/skills/_shared/config.sh
# Read current manifest, add new IDs, write back
```

Use `jq` to merge new gmail_ids into the existing array. The manifest lives at `$CLAWD_MEMORY/ai-content-manifest.json`.

---

## Common Newsletters

Aaron subscribes to AI newsletters including (but not limited to):
- The Neuron
- TLDR AI
- Ben's Bites
- The Rundown AI
- Import AI
- AI Tool Report

The label `digest` on Gmail is the authoritative filter -- don't hardcode newsletter names.

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `gather-ai-digests.sh` | Search Gmail for digest-labeled emails | `[days]` (default 7) |

Also uses:
| Tool | Purpose |
|------|---------|
| `gog gmail messages search` | Search emails by label and date |
| `gog gmail get {id}` | Read full email body |
| `jq` | Parse JSON output and update manifest |

---

## Guardrails

- **Read-only on Gmail** -- never modify, delete, or send emails
- Always check dedup manifest before creating content items
- If a newsletter format is unrecognizable (can't extract articles), log a warning and skip -- don't create malformed items
- Content items should have `status: ingested` -- scoring happens in a separate step
- Keep summaries factual -- extracted from the newsletter text, not generated
