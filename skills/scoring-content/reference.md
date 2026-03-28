# Scoring Content

> Scripts: `~/.openclaw/skills/maintaining-relationships/scripts/scoring-content/`
> Cadence: **Weekly** (part of Friday curation workflow)

## Overview

Score all ingested content items against Aaron's AI interest profile. Each item gets a composite score (0.0-1.0) that determines its ranking in the weekly digest. Scoring uses LLM assessment for topic relevance (semantic matching, not just keywords) plus deterministic boosts for creator, format, and recency.

**Use cases:**
- Weekly scoring as part of the full curation workflow
- "Score this week's content"
- "Why did this item score high/low?" (explain score breakdown)

---

## Scoring Algorithm

```
final_score = clamp(0.0, 1.0,
    topic_relevance        # 0.0-1.0: best-matching interest weight (LLM-assessed)
  + creator_boost          # 0.0-0.3: if creator is in Preferred Creators
  + format_match           # -0.2 to +0.2: deep dive/tutorial vs listicle/hype
  + recency_boost          # 0.0-0.1: content < 3 days old
  - negative_penalty       # 0.0-0.8: matches Negative Signals
)
```

### Component Details

| Component | Range | How it's determined |
|-----------|-------|---------------------|
| **topic_relevance** | 0.0 - 1.0 | LLM assesses semantic match between item title/summary and each interest topic. Takes the highest-matching topic's weight. |
| **creator_boost** | 0.0 - 0.3 | Lookup creator name in `preferred_creators`. If match, use the `weight_boost` value. |
| **format_match** | -0.2 to +0.2 | LLM classifies content format (deep_dive, tutorial, listicle, etc.) and applies preference weight. |
| **recency_boost** | 0.0 - 0.1 | +0.1 if published < 3 days ago, linear decay to 0 at 14 days. |
| **negative_penalty** | 0.0 - 0.8 | LLM checks if content matches any negative signal topics. If yes, applies the absolute value of that signal's weight. |

---

## Phase 1: Load Inputs

1. Read the interest profile from Obsidian:
   ```bash
   source ~/.openclaw/skills/_shared/config.sh
   cat "$OBSIDIAN_AI_PROFILE"
   ```

2. Find all unscored content items for the current week:
   ```bash
   source ~/.openclaw/skills/_shared/config.sh
   ls "$OBSIDIAN_AI_CONTENT"/{YYYY-Www}--*.md
   ```
   Filter for items where frontmatter `status: ingested` (not yet scored).

---

## Phase 2: Score Each Item

For each unscored item:

1. Read the item's frontmatter and summary
2. Run the scoring script or assess directly:

### Using the scoring script

```bash
uv run ~/.openclaw/skills/maintaining-relationships/scripts/scoring-content/score_content.py \
  --profile "$OBSIDIAN_AI_PROFILE" \
  --item "$OBSIDIAN_AI_CONTENT/{filename}.md"
```

The script outputs a JSON score breakdown.

### LLM-in-the-loop assessment

For topic_relevance and format_match, assess semantically:

**Topic relevance prompt pattern:**
> Given the content item "{title}" with summary "{summary}", which of the following interest topics is the best match? Rate the match quality 0.0-1.0.
> Topics: {list from profile with weights}

**Format classification prompt pattern:**
> Classify this content as one of: deep_dive, tutorial, announcement, comparison, listicle, reaction_video, hype_piece.
> Title: "{title}", Creator: "{creator}", Duration: {duration}

---

## Phase 3: Update Content Items

After scoring, update each item's frontmatter:

```yaml
score: 0.82
score_breakdown:
  topic_relevance: 0.9
  matched_topic: "AI agents and agentic workflows"
  creator_boost: 0.15
  format_match: 0.1
  format_classified: "tutorial"
  recency_boost: 0.07
  negative_penalty: 0.0
status: scored
```

Change `status` from `ingested` to `scored`.

---

## Phase 4: Summary Report

After scoring all items, produce a brief summary:

```
Scoring Complete (Week {YYYY-Www}):
- Total items scored: {N}
- Score distribution: {min} - {max} (mean: {avg})
- Top 5 items: {titles with scores}
- Items with negative penalties: {count}
```

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `score_content.py` | Compute score components for a single item | `--profile --item` |

---

## Guardrails

- **Idempotent:** Re-scoring an already-scored item should produce the same result (unless the profile changed)
- Never modify the interest profile during scoring -- that's a separate step
- If an item can't be scored (missing title, no summary), set `score: null` and `status: error` with a note
- Topic relevance is the dominant signal -- creator boost and format alone shouldn't push a low-relevance item to the top
- Cost is negligible for 30-50 items/week with short LLM assessments
