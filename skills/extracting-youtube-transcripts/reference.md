# Extracting YouTube Transcripts

> **Dependencies:** `yt-dlp` (brew install yt-dlp), `python3`
> **Script:** `_shared/scripts/extract-youtube-transcript.sh`
> Cadence: **On-demand**

## Overview

Extract clean, plain-text transcripts from YouTube videos using auto-generated subtitles. Useful as input for content creation, sales follow-ups, social media posts, blog drafts, and meeting prep.

**Use cases:**
- "Pull the transcript from this YouTube video"
- "What did [creator] say about [topic]?" (extract then search/summarize)
- "Find shareable nuggets from my recent YouTube watches"
- "Get transcript for a video I want to reference in outreach"

---

## Quick Usage

```bash
# Print transcript to stdout
~/.openclaw/skills/_shared/scripts/extract-youtube-transcript.sh "https://www.youtube.com/watch?v=VIDEO_ID"

# Save to file
~/.openclaw/skills/_shared/scripts/extract-youtube-transcript.sh "https://www.youtube.com/watch?v=VIDEO_ID" /tmp/transcript.txt
```

Handles `&t=` timestamp parameters automatically (strips them, they don't affect transcripts).

---

## Extracting Watch History via Playwright

To find videos Aaron has recently watched, use the Playwright MCP browser:

1. `browser_navigate` -> `https://www.youtube.com/feed/history`
2. `browser_snapshot` -> check for login wall
   - If login required: tell Aaron and stop
3. `browser_snapshot` -> read video titles, URLs, channels, and watch dates
4. Scroll for more:
   - `browser_evaluate` -> `() => window.scrollBy(0, 1000)`
   - `browser_wait_for` -> time=2
   - `browser_snapshot` -> read more entries
   - Repeat 2-3 times
5. For each video of interest, extract the URL and run:
   ```bash
   ~/.openclaw/skills/_shared/scripts/extract-youtube-transcript.sh "<url>" /tmp/<slug>.txt
   ```

**Filtering tips:**
- Focus on AI, business, leadership, and tech topics (Aaron's domains)
- Skip music, shorts, and entertainment unless explicitly requested
- Note watch dates for recency context

---

## Workflow: Shareable Nuggets for Social Media

1. Pull watch history (Playwright, see above)
2. Extract transcripts for relevant videos
3. For each transcript, identify 2-3 quotable insights or surprising data points
4. Draft social posts via Quill agent with:
   - The nugget/insight
   - Aaron's take or commentary
   - Attribution to the creator
   - Link to the video
5. Queue approved posts via flagging-social-queue workflow

See also: `maintaining-relationships/references/flagging-social-queue.md`

---

## Workflow: Sales Follow-up Content

1. Extract transcript from a video relevant to a prospect's industry or pain point
2. Identify the most relevant segment (search transcript for keywords)
3. Draft a follow-up message via Quill agent:
   - Reference the video with a specific insight
   - Connect it to the prospect's situation
   - Include the video link with a timestamp if relevant (append `&t=XXs` to URL)
4. Present draft for Aaron's approval

See also: `maintaining-relationships/references/managing-outreach.md`

---

## Workflow: Blog Post Source Material

When drafting blog posts, YouTube transcripts serve as source material alongside meeting transcripts, voice memos, and notes.

1. Extract transcript from relevant video(s)
2. Include in the source brief during Phase 2 of the blog drafting workflow
3. Attribute quotes and ideas to the original creator

See also: `maintaining-relationships/references/drafting-blog-posts.md`

---

## Output Format

The script produces a single block of plain text with:
- No timestamps
- No VTT formatting tags
- Deduplicated lines (auto-subs repeat text across overlapping cue segments)
- Typical size: 20-40K chars for a 30 min video

---

## Limitations

- Only works with videos that have auto-generated or uploaded English subtitles
- Auto-generated subs may have transcription errors (names, technical terms)
- Some videos have subtitles disabled by the creator
- Live streams may not have subtitles available immediately

---

## Guardrails

- **Read-only**: never interact with YouTube (no likes, comments, subscribes)
- Transcripts are for internal use. If sharing publicly, attribute the creator.
- If a video has no subtitles, report to Aaron rather than trying to work around it.
