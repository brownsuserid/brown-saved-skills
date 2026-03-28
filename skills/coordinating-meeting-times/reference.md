# Coordinating Meeting Times

Orchestrate the back-and-forth of scheduling a meeting: resolve the contact, check availability, respect weekday meeting limits, and draft a proposal with a Calendly link.

> Dependencies: `finding-calendar-availability`, `looking-up-contacts`, `sending-meeting-invitations`, `using-beeper`, `using-gog`

---

## Phase 1: Understand the Request

Extract from the conversation or inbox item:

- **Who:** Name, company, relationship (prospect, client, collaborator, friend, family)
- **Why:** Sales call, project sync, intro, catch-up, urgent issue
- **Duration:** Default 30 min. Sales intros default 45 min. Quick syncs default 20 min.
- **Urgency context:** Is this tied to a deal in the pipeline, an active project with a deadline, or an urgent issue? If so, mark as **high priority**.

### Resolve the contact

```bash
python3 ~/.openclaw/skills/maintaining-relationships/scripts/looking-up-contacts/search_contacts.py "<name>"
```

From the result, note: email, timezone (if available), preferred channel (Beeper vs email), relationship to Aaron (BB client, AITB volunteer, personal contact).

If timezone is unknown, check their company location or ask Aaron.

---

## Phase 2: Check Availability with Limits

### Weekday meeting budget

Aaron has a **2-hour daily cap** for non-Intuit meetings on weekdays (Monday through Friday). Before proposing times, check what's already booked.

```bash
python3 ~/.openclaw/skills/finding-calendar-availability/scripts/find_availability.py \
  --start <date> --end <date> --duration <minutes>
```

For each candidate weekday, also run:

```bash
gog calendar events <calendarId> --from <date>T00:00:00 --to <date>T23:59:59 --account <email>
```

across BB, AITB, and personal calendars. Sum the duration of non-Intuit meetings already on that day. Only propose times on days where the remaining budget accommodates the meeting duration.

**Exception:** If Aaron's Intuit/Work calendar shows an all-day "OOO", "PTO", "Vacation", or "Time Off" event for that day, the 2-hour cap does not apply. He has the full day available.

**Weekends:** No cap. Propose freely if the meeting type warrants it (family, personal, AITB events).

### Prioritize timing

| Priority | Context | Slot preference |
|----------|---------|-----------------|
| High | Active deal, urgent project, deadline this week | Soonest available day, morning slots |
| Normal | General sync, intro, catch-up | Next week or later, afternoon slots |
| Low | "Sometime", no urgency | 2+ weeks out, whatever's open |

For high-priority meetings, start searching from tomorrow. For normal, start from next week. For low, start from 2 weeks out.

---

## Phase 2b: Sales Lead Routing

When booking a meeting for a **sales lead at an early stage**, check whether Aaron should take it or route to a teammate.

### When this applies

The meeting is a sales call AND the deal is at stage **05-Empathy Interview or earlier**:
- 00-Backlog
- 01-Identified
- 02-Contacted
- 03-Qualification
- 04-Interest Expressed
- 05-Empathy Interview

If the deal is at **06-Aligning Scope or later**, skip this section. Aaron takes those meetings regardless of availability.

### Routing logic

1. **Check Aaron's availability** in the next **3 business days** using `find_availability.py`:
   ```bash
   python3 ~/.openclaw/skills/finding-calendar-availability/scripts/find_availability.py \
     --start <today> --end <today+3_business_days> --duration <meeting_duration>
   ```
   If Aaron has availability, proceed to Phase 3 as normal (Aaron takes the meeting).

2. **If Aaron has no availability**, check **Josh's calendar** next:
   ```bash
   gog calendar events brown@brainbridge.app --account aaron@brainbridge.app \
     --from <today> --to <today+3_business_days> --json
   ```
   Look for open slots during business hours (9 AM - 5 PM Arizona time). If Josh has availability, route to Josh and use his booking link in Phase 3.

3. **If Josh also has no availability**, check **Sven's calendar**:
   ```bash
   gog calendar events sven@brainbridge.app --account aaron@brainbridge.app \
     --from <today> --to <today+3_business_days> --json
   ```
   If Sven has availability, route to Sven and use his booking link in Phase 3.

4. **If nobody is available** within 3 business days, expand the window to 5 business days and repeat the same order (Aaron, Josh, Sven). If still no availability, flag to Aaron for manual resolution.

### Team booking links

| Person | Booking Link | Notes |
|--------|-------------|-------|
| **Aaron** | `calendly.com/aaroneden/1-on-1-call-45m-pri` | Sales Calendly (45 min) |
| **Josh** | [Google Appointment Schedule](https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ1-SVgsR9zL9tny3xEJ6RGqJz5X8Qzh2k5woPC9zVfLx7b74w8BQwZFpYhRo-6kxnTT9h0jn9bh) | "Book An AI Jam Session" |
| **Sven** | TBD | Needs to create a Google Appointment Schedule |

### Adjusting the proposal

When routing to Josh or Sven instead of Aaron:
- Use the teammate's booking link (not Aaron's Calendly)
- Adjust the email voice per `bb-email-style-guide.md` if the email comes from that person
- If Juan is sending the outreach on Aaron's behalf, frame it as: "Aaron's calendar is packed this week, but Josh/Sven on our team would love to connect with you. They're deeply involved in [relevant context]."
- Always position the teammate as a peer, not a fallback

---

## Phase 3: Draft the Proposal

Always include a Calendly link so the other person can self-schedule. Pick the right link based on context:

| Context | Calendly link |
|---------|---------------|
| First meeting / intro | `calendly.com/aaroneden/20min` |
| General 1-on-1 | `calendly.com/aaroneden/1-on-1` |
| Sales / consulting | `calendly.com/aaroneden/1-on-1-call-45m-pri` |

### Default approach: Calendly-first

For most scheduling, draft a message that leads with the Calendly link. This avoids back-and-forth entirely.

```
Hey [Name],

Would love to connect on [topic]. Grab a time that works for you:
[Calendly link]

If none of those work, let me know a few times on your end and I'll make it happen.

Aaron
```

### When to propose specific times instead

Only propose specific times (instead of Calendly) when:
- The contact doesn't do Calendly (Aaron says so, or they've pushed back before)
- It's a group meeting (3+ people) where Calendly won't work
- Aaron specifically asks to propose times

When proposing times, offer 2-3 options spread across different days. Always show Aaron's timezone with a conversion:

```
Here are a few options:
- Tuesday 3/18 at 2pm Arizona (4pm ET)
- Wednesday 3/19 at 10am Arizona (12pm ET)
- Thursday 3/20 at 3pm Arizona (5pm ET)
```

### Channel selection

| Contact type | Channel | Method |
|---|---|---|
| External / formal | Email | `gog gmail drafts create` via `using-gog` |
| Close contact / family | Beeper | `beeper-find.sh` + `beeper-read.sh focus_app` with `draftText` |
| Existing email thread | Reply to thread | `gog gmail drafts create --reply-to-message-id` |

Follow `sending-meeting-invitations.md` for formatting (subject line, purpose, agenda, logistics).

---

## Phase 4: Handle the Response

When Aaron comes back with a confirmed time (either "they booked via Calendly" or "they said Tuesday at 2 works"):

1. **Create the calendar event:**
   ```bash
   gog calendar create primary --summary "<Meeting title>" \
     --from <iso_start> --to <iso_end> \
     --attendees <email> \
     --account <aaron_account>
   ```
   Use the account that matches the relationship: `aaron@brainbridge.app` for BB, `aaron@aitrailblazers.org` for AITB, `aaroneden77@gmail.com` for personal.

2. **Draft a confirmation message** to the attendee (same channel as the proposal).

If the contact counter-proposes a different time, loop back to Phase 2: check if it falls within the daily budget and confirm or offer alternatives.

---

## Guardrails

- **Draft first, send never.** All messages are drafts for Aaron to review and send.
- **Calendar event creation requires Aaron's approval.** Present the event details and wait for confirmation.
- **Never assume timezone.** Always display times with timezone labels. If the contact's timezone is unknown, ask Aaron.
- **Respect the 2-hour weekday cap.** Do not propose times that would exceed it unless Aaron is on PTO that day.
- **Calendly is the default.** Only fall back to manual time proposals when Calendly won't work for the situation.

---

## Integration

This reference is called by:
- **Inbox processing** (`airtable-inbox-review.md`): When an email or Beeper message requests a meeting with Aaron, route to this skill instead of creating a generic scheduling task.
- **Direct request:** "Schedule a meeting with X", "find a time to meet X", "coordinate with X on a call"

This reference calls:
- `finding-calendar-availability` (Phase 2)
- `looking-up-contacts` (Phase 1)
- `sending-meeting-invitations` (Phase 3 formatting)
- `using-gog` (calendar events, email drafts)
- `using-beeper` (message drafts for close contacts)
