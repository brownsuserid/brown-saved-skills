---
name: using-notebooklm
description: Automate Google NotebookLM via Playwright MCP tools. Create notebooks, add sources (websites, YouTube, text, files, Google Drive), ask questions, and generate/download studio outputs (audio overviews, podcasts, video, mind maps, reports, flashcards, quizzes, infographics, slide decks, data tables). Use this skill whenever the user mentions NotebookLM, audio overviews, generating a podcast from content or sources, creating research notebooks, or any task that involves feeding content into NotebookLM for AI-generated summaries, audio, or other outputs.
---

# NotebookLM

> **Browser automation:** Uses Playwright MCP tools. See `_shared/references/using-playwright-mcp.md`.

Automate Google NotebookLM via **Playwright MCP browser tools**. Create notebooks, add sources, ask questions, and generate/download studio outputs.

## Overview

NotebookLM is Google's AI-powered research tool. Using MCP browser tools, Pablo can:
- Create, list, search, and delete notebooks
- Upload sources (websites, pasted text, YouTube URLs, file uploads, Google Drive)
- List and delete sources within a notebook
- Ask questions and get AI-generated answers
- Generate and download Studio outputs (Audio, Video, Mind Map, Reports, Flashcards, Quiz, Infographic, Slide Deck, Data Table)

## Authentication

NotebookLM requires a Google account. On first use (or after session expiry):

1. `browser_navigate` → `https://notebooklm.google.com`
2. `browser_snapshot` → check for sign-in page
3. If sign-in detected: tell the user "NotebookLM needs Google authentication. Please sign in."
4. `browser_snapshot` → wait for user to complete login
5. Verify you're on the NotebookLM homepage before continuing

**Multi-account:** If Aaron needs a different Google account, navigate to the Google account picker (click profile icon top-right) and let Aaron switch accounts.

## Operations

### Create a Notebook

1. `browser_navigate` → `https://notebooklm.google.com`
2. `browser_snapshot` → find the "Create new notebook" or "Create new" button
3. `browser_click` → ref for the create button
4. This navigates directly into the new notebook. A source-add dialog auto-opens.
5. `browser_snapshot` → find the inline notebook name field (shows "Untitled notebook")
6. To rename: `browser_click` → ref for the name field, then `browser_type` → text="My Research"
7. Close the source-add dialog if you don't need it yet (`browser_click` → ref for "Close" button)
8. Record the notebook URL from the browser's current URL

### List / Search Notebooks

1. `browser_navigate` → `https://notebooklm.google.com`
2. `browser_snapshot` → read the list of notebooks (titles and links visible in the tree)
3. To search: look for a search input in the snapshot, type the query, and re-snapshot
4. Extract notebook names and URLs from the accessibility tree

### Delete a Notebook

1. Navigate to the NotebookLM homepage
2. `browser_snapshot` → find the notebook to delete
3. Look for a menu icon (three dots / kebab) on the notebook card
4. `browser_click` → ref for the menu
5. `browser_snapshot` → find "Delete" option
6. `browser_click` → ref for Delete
7. `browser_snapshot` → confirm deletion dialog if present
8. `browser_click` → ref for confirm button

### Add Sources

Navigate to the notebook first, then:

#### Website or YouTube Source
Website and YouTube URLs share the same "Websites" button in the source dialog.

1. `browser_snapshot` → find "Add source" button in the sources panel (or use the auto-opened dialog)
2. `browser_click` → ref for "Add source" (if dialog not already open)
3. `browser_snapshot` → find "Websites" button (handles both website and YouTube URLs)
4. `browser_click` → ref for "Websites"
5. `browser_snapshot` → find the URL input ("Paste any links" placeholder)
6. `browser_type` → ref for URL field, text="https://example.com" (or YouTube URL)
7. `browser_click` → ref for "Insert" button
8. `browser_wait_for` → wait for source to process

#### Pasted Text Source
1. `browser_click` → ref for "Add source" (if dialog not already open)
2. `browser_snapshot` → find "Copied text" button
3. `browser_click` → ref for "Copied text"
4. `browser_snapshot` → find the text area ("Paste text here" placeholder). Note: there is no separate title field; the title is auto-generated from content.
5. `browser_type` → ref for text area, text="Your content here..."
6. `browser_click` → ref for "Insert" button
7. `browser_wait_for` → wait for processing

#### File Upload
1. `browser_click` → ref for "Add source" (if dialog not already open)
2. `browser_snapshot` → find "Upload files" button
3. `browser_click` → ref for "Upload files" (triggers file chooser)
4. `browser_file_upload` → paths=["/absolute/path/to/document.pdf"]
5. `browser_wait_for` → wait for upload and processing

#### Google Drive Source
1. `browser_click` → ref for add source
2. `browser_snapshot` → find "Google Drive" option
3. `browser_click` → ref for Drive option
4. `browser_snapshot` → navigate the Drive picker to select the file
5. Complete the selection flow

### Manage Sources

#### List Sources
1. Navigate to the notebook URL
2. `browser_snapshot` → the sources panel lists all sources with names

#### Delete a Source
1. `browser_snapshot` → find the source to delete in the sources panel
2. `browser_click` → ref for the source's menu (three dots)
3. `browser_snapshot` → find "Delete" or "Remove" option
4. `browser_click` → ref for delete
5. Confirm if prompted

### Ask Questions

For query ideas organized by use case (company research, stakeholder analysis, technical stack, proposals), see `references/query-patterns.md`.

1. Navigate to the notebook URL
2. `browser_snapshot` → find the chat/question input area
3. `browser_click` → ref for the input field
4. `browser_type` → ref for input, text="What are the key findings?", submit=true
5. `browser_wait_for` → wait for "Sources" or response indicator
6. `browser_snapshot` → read the AI-generated answer from the tree

### Generate Studio Outputs

**Studio types:** `audio`, `video`, `mind_map`, `report`, `flashcards`, `quiz`, `infographic`, `slide_deck`, `data_table`

#### Generate
1. Navigate to the notebook URL
2. `browser_snapshot` → find the "Studio" or "Audio Overview" panel
3. `browser_click` → ref for the desired output type (e.g., "Audio Overview")
4. `browser_snapshot` → find generation options (style selector for audio: deep_dive, etc.)
5. If style options exist: `browser_click` → ref for desired style
6. `browser_click` → ref for "Generate" button
7. Generation takes 2-10 minutes. Poll status:
   - `browser_wait_for` → time=30
   - `browser_snapshot` → check if "Ready", "Generated", or still "Generating"
   - Repeat up to 20 times (10 min max)

#### Download
1. Once generation is complete, `browser_snapshot` → find download button/link
2. `browser_click` → ref for download
3. File saves to the default download directory

**Downloadable:** audio (.mp3), video (.mp4), report (.pdf), infographic (.png), slide_deck (.pptx), data_table (.csv)

**View-only (not downloadable):** mind_map, flashcards, quiz

## Workflow Example

```
# 1. Create notebook
browser_navigate → https://notebooklm.google.com
browser_snapshot → find "+ New notebook"
browser_click → create it, name it "Weekly AI Digest"

# 2. Add source content
browser_snapshot → find "Add source"
browser_click → add source → Copied text
browser_type → paste digest content
browser_click → submit

# 3. Generate podcast
browser_snapshot → find "Audio Overview" in Studio panel
browser_click → Generate
# Poll until ready...

# 4. Download
browser_snapshot → find download button
browser_click → download .mp3
```

## Limitations

- Requires one-time manual Google sign-in (interactive)
- Session may expire between runs (re-authenticate if needed)
- Audio/video generation takes 2-10 minutes
- Mind Map, Flashcards, and Quiz are view-only (not downloadable)
- Not suitable for high-volume batch operations
- Interactive audio mode is not supported

## Troubleshooting

**Sign-in required:**
Navigate to NotebookLM, snapshot, detect login wall. Ask user to sign in.

**Element not found after snapshot:**
The page may still be loading. Use `browser_wait_for` with expected text, then re-snapshot.

**Audio/studio output won't download:**
Snapshot to verify the output status is "Ready" or "Generated" before attempting download. If stuck on "Generating", wait longer or report to Aaron.

**Page changed unexpectedly:**
Always re-snapshot after any click or navigation. Never reuse stale ref values.

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `maintaining-relationships` | Generate podcasts from weekly digests |
| `using-gog` | Access original Google Docs/Drive sources |
| `managing-projects` | Add context to tasks and deals |

## Legacy Scripts

Python Playwright scripts exist at `scripts/` but are deprecated. Do not use them. Use MCP tools (`mcp__playwright__browser_*`) for all browser automation. See `_shared/references/using-playwright-mcp.md`.

## Changelog

| Date | Change |
|------|--------|
| 2026-03-02 | Migration: MCP tools as primary, Python scripts as legacy fallback |
| 2026-02-20 | Expand: multi-account, list/delete notebooks, file/drive sources, source management, unified studio outputs |
| 2026-02-20 | Rewrite: Playwright automation replacing manual/API approach |
| 2026-02-19 | Initial skill creation with API and browser methods |
