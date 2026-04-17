---
name: maintaining-relationships-bb
description: BB-scoped relationship management. Route BB contact, deal, outreach, and speaking opportunity requests. Use for BB deals, BB contacts/orgs, speaking gigs, and BB meeting prep.
---

# Maintaining Relationships (BB)

BB-scoped router for relationship and communication requests.

---

## Decision Tree

| Request pattern | Reference to read |
|-----------------|-------------------|
| "Look up BB contact", "who is X at BB", "BB contact" | [looking-up-contacts](.claude/skills/looking-up-contacts/reference.md) |
| "Look up BB organization", "BB company" | [looking-up-organizations](.claude/skills/looking-up-organizations/reference.md) |
| "BB deal", "deal with X", "BB pipeline" | [looking-up-deals](.claude/skills/looking-up-deals/reference.md) |
| "Speaking opportunities", "conferences near trip", "speaking gigs" | [researching-speaking-opportunities](.claude/skills/researching-speaking-opportunities/reference.md) |
| "Run outreach for BB" | [managing-outreach](.claude/skills/managing-outreach/reference.md) |
| "Send a message", "check Beeper" | [using-beeper](.claude/skills/using-beeper/reference.md) |
| "Prep for BB meeting" | [preparing-for-meetings](.claude/skills/preparing-for-meetings/reference.md) |
| "Search BB transcripts" | [searching-meeting-transcripts](.claude/skills/searching-meeting-transcripts/reference.md) |

---

## Guardrails

- Always read the relevant reference file before executing
- **Messaging safety:** NEVER send messages unless the user explicitly asks
- If a step fails mid-workflow, report what succeeded and what failed
