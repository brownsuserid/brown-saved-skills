---
name: managing-finances-bb
description: BB-scoped financial management. Route BB deal reviews, follow-ups, pitch decks, and email approach requests.
---

# Managing Finances (BB)

BB-scoped router for financial and sales deal requests.

---

## Decision Tree

| Request pattern | Reference to read |
|-----------------|-------------------|
| "BB deal review", "BB deals", "BB pipeline", "open deals" | [sales-deal-review](.claude/skills/sales-deal-review/reference.md) |
| "BB follow-ups", "who haven't I contacted", "stale BB deals", "pipeline tasks" | [managing-sales-followups](.claude/skills/managing-sales-followups/reference.md) |
| "Pitch deck", "create a deck", "slides for client", "proposal", "SOW" | [generating-pitch-decks](.claude/skills/generating-pitch-decks/reference.md) |
| "Look up BB deal", "find BB deal" | [looking-up-deals](.claude/skills/looking-up-deals/reference.md) |
| "Look up BB organization" | [looking-up-organizations](.claude/skills/looking-up-organizations/reference.md) |

When composing emails for deals or follow-ups, also reference:
- [email-style-guide](.claude/skills/email-style-guide/reference.md) — voice, tone, and structure
- [bb-email-approaches](.claude/skills/bb-email-approaches/reference.md) — outreach approach frameworks
- [bb-case-studies](.claude/skills/bb-case-studies/reference.md) — proof points for sales conversations

---

## Guardrails

- Always read the relevant reference file before executing
- **Read-only analysis:** Sub-skills are read-only until explicitly creating tasks or sending commands
- If a step fails mid-workflow, report what succeeded and what failed
