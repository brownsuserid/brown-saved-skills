# Drafting PR-FAQs

> Output: Obsidian `$OBSIDIAN_VAULT/1-Projects/{initiative}/` or Google Docs (BB/AITB)
> Cadence: **On-demand**

## Overview

Draft Amazon Working Backwards style PR-FAQs for product, service, program, or internal tool proposals. Gathers context from Airtable, transcripts, and notes, interviews Aaron to capture his vision, then delegates to the **Quill** writing agent to produce 3 distinct draft versions for Aaron to choose from and refine.

**Use cases:**
- "Draft a PR-FAQ for AI Teammates"
- "Write a press release FAQ for our new workshop series"
- "Working backwards doc for the new onboarding flow"
- "PR-FAQ for Brain Bridge's consulting packages"

### Core Principle

If you can't describe the product as a compelling press release written on launch day, you don't understand it well enough to build it. The difficulty of writing IS the thinking.

### Five Questions Every PR-FAQ Must Answer

1. **Who is the customer?** Precisely defined, not "everyone."
2. **What problem are you solving?** From their perspective, not yours.
3. **What is your solution?** Stated as a customer benefit, not a technical description.
4. **Will they adopt it?** Given the behavior change required.
5. **Is the TAM large enough?** To justify the investment.

If any answer feels weak while writing, stop writing and do more research. The friction is diagnostic.

### Hard Rules

- Press release: **1 page max.** This is a forcing function, not a suggestion.
- FAQ: No page limit, but proportional to scope.
- Prose over bullets. Bullets hide gaps in logic. Write full sentences.
- No jargon, no buzzwords, no weasel words ("may," "could potentially," "aims to").
- No author name on the document.

---

## Phase 1: Scope the Initiative

Input is an initiative (e.g., "draft a PR-FAQ for AI Teammates").

Determine:

| Parameter | Options | Default |
|-----------|---------|---------|
| **Context** | Personal, BB (BrainBridge), AITB (AI Trailblazers) | Ask if ambiguous |
| **Initiative type** | Product, Service, Program, Internal tool | Infer from topic, ask if unclear |
| **Target customer** | Who benefits? Be specific (role, company size, pain) | Ask Aaron |
| **Time horizon** | When does this launch? (quarter/year) | Ask Aaron |

---

## Phase 2: Gather Context

Search all relevant sources in parallel using existing tools:

### 1. Airtable Tasks

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/search_tasks.py \
  --base all --query "{topic}" --max 10
```

### 2. BB Product Roadmap (BB context only)

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/drafting-pr-faqs/gather_roadmap_context.py \
  --query "{topic}" --max 10
```

Skip this step for Personal and AITB contexts.

### 3. Meeting Transcripts

```bash
python3 ~/.openclaw/skills/maintaining-relationships/scripts/searching-meeting-transcripts/search_transcripts.py \
  --query "{topic}" --account both
```

Then read relevant transcripts via `gog docs cat {fileId} --account {email}`.

### 4. Obsidian Vault

Search `$OBSIDIAN_VAULT/` for related notes, daily notes, and SOPs via Glob/Grep/Read.

### 5. Web Research (Optional)

Search the web for market data, competitor context, or supporting evidence. Only when Aaron requests it or when the initiative clearly needs external validation.

### Compile Context Brief

Organize all gathered material into a **context brief** structured as:

- **Customer problem**: What pain exists today? Evidence from transcripts, tasks, notes
- **Current alternatives**: What do customers use today? Competitors, workarounds, manual processes
- **Proposed solution**: What has Aaron said or implied about the approach?
- **Success metrics**: Any numbers, goals, or KPIs mentioned
- **Market context**: TAM signals, adoption evidence, competitive landscape
- **Dependencies and risks**: Blockers, capability gaps, or concerns surfaced

If insufficient source material is found, flag to Aaron and ask for direction before proceeding.

---

## Phase 3: Interview Aaron

Conduct a structured interview to capture Aaron's vision for the initiative. Questions map directly to PR-FAQ sections.

### Customer & Problem
1. Who is the target customer? (specific role, company size, industry, not "everyone")
2. What specific pain are they experiencing today? Rank the top 3 problems by severity.
3. What do they use today to solve this? (competitor, spreadsheet, manual process, nothing)
4. Why are those workarounds insufficient? What's the cost of the status quo?

### Solution & Benefit
5. In one sentence, what is this initiative?
6. What is the single most important benefit to the customer?
7. Describe the customer's life after this exists. What changes specifically?
8. Why is this better/faster/cheaper than what they use today?

### How It Works
9. Walk me through the customer experience from first touch to value delivered.
10. What are the 3-5 key capabilities?
11. What other approaches did you consider? Why this one?

### Leadership Perspective
12. If you had one quote for the press release, what would you say? (Strategic "why," not feature list)
13. Why now? What makes this the right time?

### Metrics & Ambition
14. What does success look like in 12 months? In 3 years? Be specific with numbers.
15. What's the TAM? How did you estimate it?
16. Is this a base hit (incremental improvement) or home run (category shift)?

### External FAQs (Customer-facing)
17. What objections will customers raise?
18. How will pricing/access work?
19. What does onboarding look like?
20. What happens if it fails or underperforms?

### Internal FAQs (Team-facing)
21. What will this cost to build/deliver? What's the payback timeline?
22. What capability gaps need filling?
23. What are the top 3 risks, and what mitigates each?
24. How does this fit the broader strategy?
25. What's the minimum viable v1 scope?
26. What are the legal/regulatory considerations?
27. What are the cross-team dependencies?

Continue asking follow-up questions until Aaron feels the vision is fully captured. Summarize the interview findings.

**APPROVAL GATE:** Present interview summary + proposed PR-FAQ outline. Do NOT proceed to drafting without Aaron's approval.

---

## Phase 4: Draft 3 Versions (via Quill Agent)

Delegate to the **Quill** writing agent to produce 3 distinct PR-FAQ versions:

| Version | Approach | Lead |
|---------|----------|------|
| **A** | Customer-led | Opens with customer pain, story-driven, empathy-forward |
| **B** | Technology-led | Opens with what's now possible, capability-forward |
| **C** | Impact-led | Opens with measurable outcome, data-driven |

### PR-FAQ Template

Each version must follow this structure:

```yaml
---
title: "{initiative name}"
type: pr-faq
context: "{personal|bb|aitb}"
initiative_type: "{product|service|program|internal_tool}"
target_customer: "{description}"
time_horizon: "{quarter/year}"
version: "{A|B|C}"
date: {YYYY-MM-DD}
status: draft
---
```

**HEADLINE**: One sentence. Names a specific customer segment and a specific benefit (not a feature). Format: `[COMPANY] Announces [THING] to Enable [CUSTOMER] to [BENEFIT]`.

**SUB-HEADLINE**: One sentence adding context. Does not repeat the headline.

**{City, Date}** — Opening paragraph (3-4 sentences). Who launched what, the core customer benefit, and why it matters. Tone varies by version approach.

**Problem Paragraph**: 2-3 sentences written entirely from the customer's perspective. Top 3-4 problems ranked by severity. **No solution language here.** Do not mention the product. Do not mention the company. This paragraph must stand alone as a description of real pain.

**Solution Paragraph**: Describes how the product solves each named problem. Acknowledges what customers use today and articulates why this approach is better. Sufficient detail to understand how it works, not a spec sheet.

**Leadership Quote**: 2-3 sentences from Aaron. Explains why the company decided to tackle this problem at a strategic level. **Not a feature list.**

**How It Works**: 1-2 paragraphs describing the mechanics. Written for a customer, not an engineer.

**Customer Quote**: A realistic (fictional) quote from a named persona. Must name a **specific outcome** ("I used to spend 6 hours a week on X, now it takes 20 minutes"), not a generic endorsement. Litmus test: if the quote could apply to any product, rewrite it.

**Call to Action**: One sentence. How the customer gets started.

**1-page limit.** If the press release exceeds one page, cut. The constraint is the point.

---

### External FAQs (5-8)

Customer-facing questions and answers. Write in prose, not bullets:
- What is {initiative}?
- Who is this for? (Be specific about who it's NOT for, too)
- How much does it cost / how do I access it?
- How is this different from {named competitor or current workaround}?
- What results can I expect? (Anchor to specific outcomes)
- How do I get started?
- What if it doesn't work for my situation?
- When is it available?

### Internal FAQs (5-10)

Team-facing questions and answers. This is where the depth lives. Prose, not bullets:
- What does the customer use today to solve this? Why will they switch?
- What is the TAM? Show the math, not a guess.
- Who are the competitors and how do we differentiate specifically?
- What will this cost to build and operate? What's the payback timeline?
- What capabilities do we need that we don't have?
- What are the top 3 risks? What mitigates each?
- How does this fit our current strategy and objectives?
- What is the v1 scope vs full vision?
- What other solution approaches were considered? Why were they rejected?
- How will we measure success at 1 year and 3 years?
- What are the cross-team dependencies?
- What are the legal/regulatory considerations?
- Label assumptions as assumptions. Do not state hypotheses as facts.

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

**APPROVAL GATE:** Aaron must approve the final version before delivery.

---

## Phase 6: Deliver

Route the final approved PR-FAQ based on context:

### Personal → Obsidian

Write markdown with YAML frontmatter to:
`$OBSIDIAN_VAULT/1-Projects/{initiative-slug}/{YYYY-MM-DD}--pr-faq-{title-slug}.md`

### BB → Google Docs

```bash
gog docs create --account aaron@brainbridge.app --title "PR-FAQ: {title}" --parent {strategy_folder_id}
```

### AITB → Google Docs

```bash
gog docs create --account aaron@aitrailblazers.org --title "PR-FAQ: {title}" --parent {strategy_folder_id}
```

Present the link (Obsidian URI or Google Docs URL) to Aaron.

---

## Quality Check

Run this checklist against each draft before presenting to Aaron. Flag any failures.

### Press Release

- [ ] Headline names a specific customer segment AND a specific benefit (not a feature)
- [ ] Subtitle adds context, does not repeat the headline
- [ ] Launch date is realistic, not aspirational
- [ ] Problem paragraph is written entirely from the customer's perspective, zero solution language
- [ ] Problems are ranked by severity, 3-4 maximum
- [ ] Solution paragraph references each named problem
- [ ] Solution acknowledges what customers use today and explains specific differentiation
- [ ] Leadership quote explains the strategic "why," not a feature list
- [ ] Customer quote names a specific, measurable outcome
- [ ] Customer quote could NOT apply to any other product (if it could, rewrite)
- [ ] How-it-works section is written for a customer, not an engineer
- [ ] Entire press release fits on 1 page
- [ ] No jargon, buzzwords, or weasel words
- [ ] Written in prose, not bullet lists

### FAQ

- [ ] All five core questions are answered (who, what problem, what solution, will they adopt, is TAM sufficient)
- [ ] TAM is calculated with data or explicitly flagged as an estimate
- [ ] Competitors are named and differentiation is specific
- [ ] What customers use today is explicitly described
- [ ] Top risks are named with mitigations, not buried or ignored
- [ ] Multiple solution options were considered; rejected options noted with rationale
- [ ] Success metrics defined at 1-year and 3-year horizons
- [ ] Assumptions are labeled as assumptions
- [ ] FAQ answers are written in prose, not bullet lists
- [ ] All numerical claims are anchored to a source or flagged as estimates

### Common Anti-Patterns to Catch

- **Capabilities-first thinking**: Built from "what can we do" instead of "what do customers need." The problem paragraph exposes this immediately.
- **"Our product is for everyone"**: Failure to define a specific customer segment.
- **Solution language in the problem paragraph**: Mentioning the product before the customer quote section.
- **Generic customer quote**: "This product really helped me!" is a failure. Rewrite.
- **Burying competition**: Saying competitors don't exist signals the team hasn't done research.
- **Bullet-heavy FAQ**: Signals shallow reasoning. Convert to prose.

---

## Guardrails

- **Never publish directly**: always create as drafts
- **Phase 3 approval gate**: Aaron must approve interview summary + outline before drafting
- **Phase 5 approval gate**: Aaron must approve final version before delivery
- **Source attribution**: always attribute quotes from transcripts and notes
- **Insufficient material**: flag to Aaron and ask for direction rather than guessing
- **Ambiguous initiative**: ask Aaron to clarify context, customer, and time horizon before searching
- **BB roadmap**: only query the Product Roadmap table for BB context initiatives
