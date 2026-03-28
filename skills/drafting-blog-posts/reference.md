# Drafting Blog Posts

> Output: Obsidian `$OBSIDIAN_VAULT/3-Resources/Blog Drafts/` or Google Docs (BB/AITB)
> Cadence: **On-demand**

## Overview

Draft blog posts from Aaron's ideas, transcripts, voice memos, and notes. Gathers source material, interviews Aaron to capture his perspective, then delegates to the **Quill** writing agent to produce 3 distinct draft versions for Aaron to choose from and refine.

**Use cases:**
- "Draft a blog post about the Agile Manifesto vs AI Manifesto"
- "Write a post about our approach to AI agent orchestration"
- "Turn my notes on X into a blog post"
- "Write up my thoughts on Y for the BB blog"

---

## Phase 1: Understand the Topic

Input is a topic (e.g., "draft a blog post about the Agile Manifesto vs AI Manifesto").

Determine:

| Parameter | Options | Default |
|-----------|---------|---------|
| **Context** | Personal (aaroneden.com), BB (BrainBridge), AITB (AI Trailblazers) | Ask if ambiguous |
| **Post type** | Standard (800-1200 words), Case study (1500-2000 words) | Standard |
| **Target audience** | Who is this for? | Ask Aaron |

---

## Phase 2: Gather Source Material

Search all relevant sources using existing tools:

### 1. Meeting Transcripts

Run the existing transcript search script:

```bash
python3 ~/.openclaw/skills/maintaining-relationships/scripts/searching-meeting-transcripts/search_transcripts.py \
  --query "{topic}" --account both
```

Then read relevant transcripts via `gog docs cat {fileId} --account {email}`.

### 2. Airtable Tasks

Run the existing task search script:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/search_tasks.py \
  --base all --query "{topic}" --max 10
```

Pulls task name, description, and notes for context.

### 3. Voice Memo Transcripts

Search Obsidian `$OBSIDIAN_VAULT/3-Resources/Voice Memos/` for files matching the topic using Glob/Grep/Read.

### 4. Obsidian Vault

Search the broader vault for related notes (daily notes, SOPs, etc.) via Glob/Grep/Read.

### 5. YouTube Transcripts

Extract transcripts from relevant YouTube videos as source material:

```bash
~/.openclaw/skills/_shared/scripts/extract-youtube-transcript.sh "<url>" /tmp/yt-source.txt
```

See `_shared/references/extracting-youtube-transcripts.md`.

### 6. Web Research (Optional)

Search the web for current data, stats, or references to support the post.

### Compile Source Brief

Organize all gathered material into a **source brief**, a summary organized by source with key quotes and data points highlighted.

If insufficient source material is found, flag to Aaron and ask for direction before proceeding.

---

## Phase 3: Interview Aaron

Conduct a structured interview to draw out Aaron's unique perspective and insights on the topic. This is the critical phase that ensures the post captures his authentic voice and original thinking.

**Interview flow:**

1. Present the source brief from Phase 2, what was found across transcripts, memos, notes, and web
2. Ask about Aaron's **core thesis**, what's the main argument or insight?
3. Ask about **specific experiences**, real stories, meetings, or conversations that illustrate the point
4. Ask about **the audience**, who needs to hear this and why it matters to them
5. Ask about **contrarian or surprising angles**, what would most people get wrong about this topic?
6. Ask about **the call to action**, what should the reader do differently after reading?

Continue asking follow-up questions until Aaron feels the topic has been fully explored. Summarize the interview findings before proceeding.

**APPROVAL GATE:** Present interview summary + proposed outline direction. Do NOT proceed to drafting without Aaron's approval.

---

## Phase 4: Draft 3 Versions (via Quill Agent)

Delegate to the **Quill** writing agent to produce 3 distinct draft versions:

| Version | Style | Lead |
|---------|-------|------|
| **A** | Direct and practical | Leads with the actionable insight, minimal setup |
| **B** | Story-driven | Opens with a specific anecdote or experience from the interview |
| **C** | Provocative/contrarian | Leads with a bold claim or question that challenges conventional thinking |

Each version should:
- Use Aaron's conversational, first-person style
- Hit the target word count (800-1200 standard, 1500-2000 case study)
- Include real examples from interview + source material with attribution
- Include frontmatter: `title`, `subtitle`, `target_audience`, `seo_keywords`, `word_count`, `post_type`

---

## Phase 5: Feedback & Revision

Present all 3 versions to Aaron. For each version, ask:
- What works well?
- What doesn't land?
- What's missing?

Aaron may:
- Pick one version to refine
- Mix elements from multiple versions
- Request a different angle entirely

Iterate with Quill based on Aaron's feedback until the final version is approved.

---

## Phase 6: Deliver

Route the final approved draft based on context:

### Personal → Obsidian

Write markdown with YAML frontmatter to:
`$OBSIDIAN_VAULT/3-Resources/Blog Drafts/{YYYY-MM-DD}--{title-slug}.md`

```yaml
---
title: "{title}"
subtitle: "{subtitle}"
date: {YYYY-MM-DD}
target_audience: "{audience}"
seo_keywords: [{keywords}]
word_count: {count}
post_type: "{standard|case_study}"
status: draft
---
```

### BB → Google Docs

```bash
gog docs create --account aaron@brainbridge.app --title "{title}" --parent {marketing_blog_folder_id}
```

Include frontmatter block at top of doc.

### AITB → Google Docs

```bash
gog docs create --account aaron@aitrailblazers.org --title "{title}" --parent {marketing_blog_folder_id}
```

Present the link (Obsidian URI or Google Docs URL) to Aaron.

---

## Guardrails

- **Never publish directly**, always create as drafts
- **Phase 3 approval gate**, Aaron must approve interview summary + outline before drafting
- **Phase 5 approval gate**, Aaron must approve final version before delivery
- **Source attribution**, always attribute quotes from transcripts and voice memos
- **Insufficient material**, flag to Aaron and ask for direction rather than guessing
- **Ambiguous topic**, ask Aaron to clarify context and audience before searching
