# Managing Outreach

List-based event outreach with contact gathering, spreadsheet tracking, and follow-up drafting. Works for any event, hackathons, meetups, conferences, workshops.

## What It Does

Three-phase outreach pipeline:

1. **Gather**: Scan Beeper conversations (LinkedIn, Telegram, etc.) to find contacts related to the event
2. **Update**: Sync gathered contacts with a Google Sheets spreadsheet, cross-reference Airtable for registrations
3. **Follow-up**: Draft personalized follow-up messages for contacts needing a nudge, NEVER sends automatically

## Config File Structure

Each event gets its own config.json in `maintaining-relationships/data/outreach/<event-slug>/`. The config drives all three phases.

### Schema

```json
{
  "spreadsheet": {
    "id": "<google-sheets-id>",
    "name": "<human-readable name>",
    "developersTab": "<tab name>",
    "columns": "A:F",
    "account": "<gog account email>"
  },
  "event": {
    "name": "<event name>",
    "date": "YYYY-MM-DD",
    "time": "<time range with timezone>",
    "location": "<venue>",
    "price": "<price or 'Free'>",
    "rsvpUrl": "<registration URL>"
  },
  "airtable": {
    "base_id": "<airtable base ID>",
    "table": "<table name>",
    "event_filter": "<filter value to match event>"
  },
  "known_contacts": [
    {"name": "Full Name", "chat_id": "!xxx:beeper.local", "channel": "LinkedIn"}
  ],
  "followup_rules": {
    "days_since_last_contact": 3,
    "priority_order": ["Interested", "No Response", "Invited"]
  },
  "templates": {
    "nudge": "Hi {name},\n\nQuick follow-up on {event_name} on {event_date} at {event_location}. We're down to our final spots and I'd love to have you there.\n\n{event_details}\n\nRSVP here if you can make it: {rsvp_url}\n\nLet me know either way!\n\nBest,\nAaron",
    "interested": "Hi {name},\n\nGreat to hear you're interested in {event_name}! Just wanted to make sure you saw the RSVP link - we're filling up and I want to make sure you get a spot.\n\n{event_date} at {event_location}.\n\nRSVP here: {rsvp_url}\n\nSee you there!\n\nBest,\nAaron"
  }
}
```

### Concrete Example (Hack-AI-Thon Jam 2)

Config lives at: `maintaining-relationships/data/outreach/hackathon-jam-2-2026-02/config.json`

## Status Definitions

- **Invited**: Initial outreach sent, awaiting response
- **Interested**: Expressed interest but hasn't registered
- **Ticket Purchased / RSVPd**: Registered for the event
- **Declined**: Explicitly said they can't attend
- **No Response**: No reply to initial outreach
- **Follow-up Sent**: Nudge message sent, awaiting response
- **Interested - Follow-up Sent**: Was interested, got a nudge about registering

## Workflow

### Phase 1: Gather Contacts from Beeper

Scans Beeper for conversations related to the event. Paginates through all LinkedIn chats (or other channels) and builds a contact list.

**Fields captured:** Name, Company (if available), Channel, Beeper Chat ID, Status (defaults to "Invited"), Notes, Email (if available)

### Phase 2: Update Spreadsheet

Reads the Google Sheets spreadsheet via `gog`, compares with gathered contacts, appends new ones, updates statuses. Cross-references Airtable for ticket/registration status.

Status updates follow a priority ladder, more specific statuses never get overwritten by less specific ones.

### Phase 3: Draft Follow-ups

For contacts needing follow-up (based on `followup_rules.priority_order`):
1. Optionally reads their Beeper conversation for context (`--fetch-context`)
2. Renders a message template from config.json `templates` section
3. Generates a Beeper command to pre-fill the draft
4. Presents everything for user approval

## Writer Agent (Quill)

For personalized follow-up messages that go beyond simple template fills -- especially when the contact needs a custom tone, the context is nuanced, or the message is longer than a quick nudge -- delegate drafting to the writer agent:

```
sessions_spawn({
  task: "Draft a follow-up to [Name] about [event]. Channel: [LinkedIn/WhatsApp/etc]. Context: [relationship details, prior conversation]. Tone: [casual/professional].",
  agentId: "writer",
  label: "outreach-followup"
})
```

**When to use Quill vs templates:**
- **Templates:** Simple nudges, status-based follow-ups where the config.json template fits
- **Quill:** Personalized outreach, context-heavy follow-ups, messages where Aaron's voice matters more than speed

## Safety Rules

**NEVER send messages without explicit user approval.**

Always use one of these approaches:
1. **Draft for review** (default): Use `beeper-read.sh focus_app` with `draftText` to pre-fill message for user to review and send
2. **Explicit approval**: Only use `beeper-send.sh` if user explicitly says "send it" or "go ahead and send"

## Scripts Reference

All scripts live in `maintaining-relationships/scripts/managing-outreach/`.

### Orchestrator

```bash
# Run all phases for a specific event
./run-outreach.sh --config path/to/config.json all

# Run individual phases
./run-outreach.sh --config path/to/config.json gather
./run-outreach.sh --config path/to/config.json update
./run-outreach.sh --config path/to/config.json followup

# Dry run
./run-outreach.sh --config path/to/config.json all --dry-run
```

### Individual Scripts

```bash
# Gather contacts from Beeper
python3 gather_contacts.py --config path/to/config.json

# Update spreadsheet (can pipe from gather)
python3 gather_contacts.py --config path/to/config.json | python3 update_spreadsheet.py --config path/to/config.json

# Draft follow-ups
python3 draft_beeper_followups.py --config path/to/config.json --limit 5
python3 draft_beeper_followups.py --config path/to/config.json --status Interested
python3 draft_beeper_followups.py --config path/to/config.json --fetch-context
```

## Data Storage

Per-event data lives under `maintaining-relationships/data/outreach/<event-slug>/`:

```
maintaining-relationships/data/outreach/
  hackathon-jam-2-2026-02/
    config.json            # Event configuration
    outreach-state.json    # Last run date, contacts processed, status counts
```

To add a new event: create a new directory with its own `config.json`, then point `--config` at it.

## Cron

On-demand. No fixed schedule.

## Usage

```bash
# Full outreach run for a specific event
run-outreach.sh --config ~/.openclaw/skills/maintaining-relationships/data/outreach/hackathon-jam-2-2026-02/config.json all
```

Or invoke via Pablo:
```
Run outreach for [event name].
```

## Related

- **YouTube transcripts for follow-ups:** Extract a video transcript, find a relevant insight, and reference it in outreach. See `_shared/references/extracting-youtube-transcripts.md` (Sales Follow-up workflow).

---

## Troubleshooting

**Beeper API not responding?**
- Check Beeper Desktop is running on localhost:23373
- Verify BEEPER_TOKEN is set

**Spreadsheet access denied?**
- Ensure gog is authenticated: `gog auth status`
- Re-auth if needed: `gog auth add <account> --services sheets`

**Can't find chat?**
- Search by name using `beeper-find.sh`
- Check if conversation is in different network (LinkedIn vs Telegram)
