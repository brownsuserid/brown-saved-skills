# Generating Podcast

> **Browser automation:** Uses Playwright MCP tools. See `_shared/references/using-playwright-mcp.md`.
> Cadence: **Weekly** (after digest is finalized)

## Overview

Upload the weekly digest to Google NotebookLM and generate an Audio Overview (podcast-style summary). The generated audio gives Aaron a hands-free way to absorb the week's AI highlights during commutes or workouts.

**Use cases:**
- Weekly podcast generation as part of the full curation workflow
- "Generate a podcast from this week's digest"
- "Create a NotebookLM episode"

---

## Phase 1: Prepare Digest Content

Read the current week's digest:

```bash
source ~/.openclaw/skills/_shared/config.sh
cat "$OBSIDIAN_AI_DIGESTS/AI-Digest-{YYYY-Www}.md"
```

Prepare a clean version for NotebookLM:
- Include only Top Picks and Notable Mentions (skip the Stats and checklist sections)
- Keep item summaries, scores, and source attributions
- Remove Obsidian-specific frontmatter
- Save to a temp file for upload

```bash
DIGEST_FILE=$(mktemp /tmp/digest-XXXX.md)
# Write cleaned content to $DIGEST_FILE
```

---

## Phase 2: Create or Reuse Notebook

1. `browser_navigate` → `https://notebooklm.google.com`
2. `browser_snapshot` → check for login wall (see SKILL.md Authentication section)
3. If authenticated, `browser_snapshot` → look for existing "AI Weekly Digest" notebooks
4. If reusing: `browser_click` → ref for the existing notebook
5. If creating new:
   - `browser_snapshot` → find "New notebook" or "+" button
   - `browser_click` → ref for create
   - `browser_snapshot` → name the notebook "AI Weekly Digest, Week {W}, {YYYY}"
   - `browser_type` → ref for name field, text="AI Weekly Digest, Week {W}, {YYYY}"
   - `browser_click` → ref for confirm
6. Record the notebook URL for subsequent phases

---

## Phase 3: Upload Digest

1. `browser_snapshot` → find "Add source" button in the sources panel (or use auto-opened dialog)
2. `browser_click` → ref for "Add source" (if dialog not already open)
3. `browser_snapshot` → find "Copied text" button
4. `browser_click` → ref for "Copied text"
5. `browser_snapshot` → find the text area ("Paste text here" placeholder). Note: no separate title field; title is auto-generated.
6. Read the `$DIGEST_FILE` content and `browser_type` → ref for text area, text=<digest content>
7. `browser_click` → ref for "Insert" button
8. `browser_wait_for` → wait for source to finish processing

---

## Phase 4: Generate Audio Overview

1. `browser_snapshot` → find "Audio Overview" or "Studio" panel
2. `browser_click` → ref for Audio Overview
3. `browser_snapshot` → find style option, select "Deep Dive" if available
4. `browser_click` → ref for "Generate" button
5. Poll for completion (2-5 minutes typical, 10 minutes max):
   - `browser_wait_for` → time=30
   - `browser_snapshot` → check for "Ready" or "Generated" status
   - Repeat up to 20 times
6. If generation exceeds 10 minutes, report to Aaron and move on

---

## Phase 5: Download and Share

1. `browser_snapshot` → find the download button for the completed audio
2. `browser_click` → ref for download (saves .mp3 to Downloads)

Report to Aaron:

```
NotebookLM Podcast Ready (Week {W}):
- Notebook: {NOTEBOOK_URL}
- Audio: ~/Downloads/ai-digest-w{W}-{YYYY}.mp3
- Sources: {count} items from this week's digest

Open the notebook to listen or share the episode.
```

---

## Reusing the Notebook

To keep things organized, consider reusing a single "AI Weekly Digest" notebook:
- Add each week's digest as a new source
- Delete sources older than 4 weeks to keep the notebook focused
- Each Audio Overview generation uses only the current sources

---

## Guardrails

- **NEVER delete existing notebooks** unless Aaron explicitly requests it
- If NotebookLM is unavailable or errors, report to Aaron and skip this step, it's not blocking
- Don't generate audio if the digest has fewer than 3 Top Picks (not enough content for a meaningful episode)
- Audio generation is asynchronous, if it takes more than 10 minutes, report and move on
- NotebookLM has usage limits, if rate-limited, try again later or skip for the week
- If auth expires mid-workflow, navigate to NotebookLM and ask the user to sign in again

## Legacy Scripts

Python scripts at `~/.openclaw/skills/using-notebooklm/scripts/` are deprecated. Use MCP tools for all browser automation. See `_shared/references/using-playwright-mcp.md`.
