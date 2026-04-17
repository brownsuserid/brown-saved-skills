# Engagement Patterns

Standard defaults for sequences, authority levels, reply handling, task formats, and content constraints. These are starting points — override them in the Campaign Plan when the campaign requires it.

---

## Default Sequence Structure

5-touch sequence across 12 days. Modify touch count, days, and channels in Section 8 of the Campaign Plan.

| Step | Day | Channel | Content Strategy | Default CTA |
|------|-----|---------|-----------------|-------------|
| 1 | 1 | Email | Personalized cold outreach — establish relevance with a specific company or role observation | Ask for a 15-min call |
| 2 | 3 | LinkedIn | Connection request with a brief context note — reference the email without repeating it | Connect |
| 3 | 5 | Email | Value-add follow-up — different angle, share a relevant insight or result | Ask for a reaction |
| 4 | 8 | Phone | Direct outreach — use talking points from Campaign Plan; leave a voicemail if no answer | Ask for a 15-min call |
| 5 | 12 | Email | Final touch — clear CTA, acknowledge it may not be the right time, leave door open | Explicit yes/no ask |

**Personalization requirements for Touch 1:** Look up company news, recent hires, LinkedIn activity, or job postings before writing. Do not send a generic opener.

**CTA progression logic:** Start soft (reaction/opinion), move to medium (short call), end direct (yes or no). Never open with a hard ask.

---

## Authority Levels

Used in reply handling and task routing to determine who acts and whether approval is needed.

| Level | Name | Definition |
|-------|------|------------|
| A | Autonomous | Execute without review or notification |
| B | Autonomous + Notify | Execute immediately, then notify the owner |
| C | Propose and Wait | Draft the action and wait for human approval before executing |
| D | Assign to Human | Create a task for the human; do not execute |
| S | System / Automation | Handled by system or automation; no task created |

**Default authority levels by reply type:**

| Reply Type | Authority Level | Rationale |
|------------|----------------|-----------|
| Interest | Level A | Standard advancement; no approval needed |
| Objection | Level B | Execute with judgment; notify owner of the objection |
| Confusion | Level A | Clarification is low-risk; send and move on |
| Hostile | Level D | Human must handle; do not respond |
| Out-of-Office | Level S | Handled by sequence pause logic |

---

## Reply Handling Patterns

Full handling strategy for each reply type. Override in Section 15 of the Campaign Plan.

### Interest
**Signal:** Prospect asks to learn more, requests a call, or responds positively.
**Action:** Advance qualification. Use the F.L.O.O.R. framework to qualify in the next message. Propose a specific meeting time.
**Tone:** Warm, confident, not overly eager.
**Do not:** Forward to a full demo or proposal until 40% qualification is confirmed.

### Objection
**Signal:** Prospect pushes back ("not the right time", "we already have something", "budget is frozen").
**Action:** Acknowledge the concern genuinely. Ask one clarifying question to understand it better. Do not rebut immediately.
**Tone:** Empathetic, curious, not defensive.
**Do not:** Send a list of counter-arguments.

### Confusion
**Signal:** Prospect doesn't understand what was offered or why it's relevant ("what do you do?", "how did you find me?").
**Action:** Clarify relevance in 4 sentences or fewer. Reconnect to a specific problem. Re-establish why this outreach was relevant to them specifically.
**Tone:** Direct, clear, no jargon.
**Do not:** Send the full company pitch or a brochure.

### Hostile
**Signal:** Prospect responds with anger, a threat, or demands to be removed.
**Action:** Do not respond. Create a task assigned to the owner. Flag the contact record in Airtable. Add to DNC list.
**Tone:** N/A — no response sent.
**Do not:** Attempt to de-escalate via additional messages.

### Out-of-Office
**Signal:** Auto-reply indicating the prospect is unavailable.
**Action:** Note the return date. Pause the sequence. Resume on the first business day after return. Do not advance to the next touch while they are away.
**Tone:** N/A — no message sent.
**Do not:** Advance the sequence during the OOO window.

---

## Definition of Done Formats

Use these formats when logging completed outreach actions in Airtable or reporting to the owner.

### Send Email
```
From: [sender name] <[sender email]>
To: [prospect name] <[prospect email]>
Subject: [subject line]
Body: [full message text]
```

### LinkedIn Message
```
To: [prospect name]
Profile: [LinkedIn URL]
Message: [full message text]
```

### Phone Call
```
To: [prospect name]
Phone: [phone number]
Talking Points:
- [point 1]
- [point 2]
- [point 3]
Voicemail Left: yes/no
```

### Human Communication (Task for Owner)
```
To: [owner name]
Type: [Email / Slack / Call]
Message: [what to communicate and why]
Context: [relevant deal or contact record link]
```

---

## Content Constraints Defaults

Apply these to every message in the sequence unless the Campaign Plan overrides them in Section 7.

| Constraint | Default |
|------------|---------|
| Word count per message | 75–100 words |
| Questions per message | 1 max |
| Subject line length | 3–5 words |
| Paragraphs per message | 2–3 max |
| Bullet lists in cold email body | Not allowed |
| HTML formatting | Not allowed |
| Embedded images | Not allowed |
| Attachments on first touch | Not allowed |

**Subject line guidance:**
- Short and specific beats clever
- Avoid spam triggers: "free", "guaranteed", "limited time", "!!!"
- Reference something real about the prospect or their company when possible
- Examples: "growth team scale", "RevOps at [Company]", "question re: SDR ramp"

**Opening line guidance:**
- Do not open with "I hope this finds you well" or any filler phrase
- Open with an observation about the prospect's company, role, or situation
- Make the first sentence earn its place
