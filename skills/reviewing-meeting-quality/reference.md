# Weekly Meeting Quality Review

Review upcoming week's meetings for quality. Ensure each meeting has clear purpose and agenda before it happens.

---

## Trigger

- **Schedule:** Sunday 3:00 PM
- **Manual:** "Review my meetings", "check meeting quality", "prep my week's meetings"

---

## What Pablo Does

1. **Fetch meetings** for upcoming Mon-Sun
2. **Review each meeting** against quality criteria
3. **Research context** for flagged meetings (transcripts, Beeper, Airtable)
4. **Ping Aaron on Telegram** with findings and suggestions
5. **Work interactively** to resolve: clarify agenda together OR draft outreach to attendee

---

## Quality Criteria

Pablo reviews each meeting for:

| Element | Good | Needs Attention |
|---------|------|-----------------|
| **Subject** | Specific purpose ("Q1 planning sync", "Onboarding kickoff") | Vague ("Catch up", "Quick chat", "Meeting", "Call") |
| **Agenda** | In description, or linked doc, or known recurring format | Empty description on non-recurring meeting |
| **Duration** | Matches complexity (15-30 min for check-ins, 45-60 for working sessions) | 60+ min with no agenda |
| **Attendees** | Known contacts or already researched | Unknown external attendees |
| **Organizer** | I organized it (I control the agenda) | Someone else organized, no agenda shared |

### Auto-skip (no review needed)

- Recurring 1:1s with known people (agenda is implicit)
- Meetings I declined
- All-day events (blocks, not meetings)
- Internal team syncs with established format

---

## Workflow

### Phase 1: Fetch Meetings

```bash
python3 ~/.openclaw/skills/maintaining-relationships/scripts/reviewing-meeting-quality/fetch_week_meetings.py
```

Returns JSON with all meetings grouped by day, including:
- Title, description, duration
- Attendees with names/emails
- Whether I'm the organizer
- Calendar (Personal, BB, AITB)

### Phase 2: Review Each Meeting

For each meeting, Pablo assesses:

1. **Is the subject vague?** Check against bad patterns
2. **Is there an agenda?** Check description field
3. **Do I know the attendees?** Cross-reference with contacts
4. **Am I the organizer?** If not, is the purpose clear?

Flag meetings that fail any criteria.

### Phase 3: Research Flagged Meetings

For each flagged meeting:

1. **Search transcripts** for past meetings with same attendees:
   ```bash
   python3 ~/.openclaw/skills/maintaining-relationships/scripts/searching-meeting-transcripts/search_transcripts.py \
     --query "Attendee Name" --max 3
   ```

2. **Check Beeper** for recent conversations:
   ```bash
   ~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-find.sh "Attendee Name"
   ```

3. **Search Airtable** for related deals/contacts:
   ```bash
   python3 ~/.openclaw/skills/maintaining-relationships/scripts/looking-up-contacts/search_contacts.py "Attendee Name"
   python3 ~/.openclaw/skills/maintaining-relationships/scripts/looking-up-deals/search_deals.py "Company Name"
   ```

### Phase 4: Telegram Report

Send findings to Aaron via Telegram with this format:

```
WEEKLY MEETING REVIEW

[X] meetings this week (Mon-Sun)
[Y] need attention

---

1. [TITLE] ([Day] [Time], [Calendar])
   Issue: [specific problem]
   Context: [what I found from research]
   Suggestion: [specific action]

2. ...

---

Ready meetings: [count]
[List titles only]

How would you like to handle the flagged ones?
```

### Phase 5: Interactive Resolution

For each flagged meeting, Aaron chooses:

**Option A: Clarify together**
- Pablo asks clarifying questions
- Aaron provides context
- Pablo updates the calendar event description with agenda

**Option B: Draft outreach**
- Pablo drafts a brief message to the attendee:
  "Hey [Name], looking forward to our call [Day]. What would you like to cover?"
- Aaron approves before sending

**Option C: Skip**
- Mark as reviewed, no action needed

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/reviewing-meeting-quality/fetch_week_meetings.py` | Fetch Mon-Sun meetings from all Google calendars |

---

## Integration

This workflow uses:
- [searching-meeting-transcripts.md](searching-meeting-transcripts.md) - Find past conversations
- [looking-up-contacts.md](looking-up-contacts.md) - Research attendees
- [looking-up-deals.md](looking-up-deals.md) - Find related deals
- [using-beeper.md](using-beeper.md) - Check recent messages
- [sending-meeting-invitations.md](sending-meeting-invitations.md) - Quality standards reference

---

## Guardrails

- **Read-only by default:** Never modify calendar events without Aaron's approval
- **Draft outreach, don't send:** Any attendee messages go through approval
- **Research before asking:** Gather context so Aaron has information to decide
- **Respect Sunday:** Keep the interaction focused, don't drag it out

---

## Cron

**Schedule:** Sunday 3:00 PM Arizona time

**Cron expression:** `0 15 * * 0`
