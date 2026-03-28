---
name: sending-meeting-confirmations
description: Send friendly confirmation emails to external meeting attendees each morning. Automatically identifies external meetings (non-Intuit, non-Aaron emails) and sends personalized confirmation notes 2-24 hours before the meeting. Integrates with Google Calendars and prevents duplicate confirmations via state tracking.
---

# Sending Meeting Confirmations

Daily cron skill that sends friendly confirmation emails to external meeting attendees. Keeps meetings top-of-mind and reduces no-shows.

## What It Does

1. **Scans calendars** for today's meetings with external attendees
2. **Filters to external** (non-@intuit.com, non-Aaron emails)
3. **Skips duplicates** (tracks confirmed meetings via state file)
4. **Sends confirmations** via Gmail 2-24 hours before meeting
5. **Notifies Aaron** via Telegram with summary

## Calendars Checked

| Account | Label |
|---------|-------|
| `aaron@brainbridge.app` | BB |
| `aaron@aitrailblazers.org` | AITB |
| `aaroneden77@gmail.com` | Personal |

## Usage

### Manual Run

```bash
# Dry run (default) - see what would be sent
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/send_confirmation.py

# Actually send confirmations
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/send_confirmation.py --send

# Or via environment variable
OPENCLAW_CONFIRMATION_SEND=1 python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/send_confirmation.py

# JSON output for scripting
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/send_confirmation.py --json
```

### Check Today's External Meetings

```bash
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/gather_external_meetings.py
```

### Check State

```bash
# List confirmed meetings
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/check_confirmation_state.py --list

# Check if specific event confirmed
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/check_confirmation_state.py --check <event_id>

# Clean up old entries (>30 days)
python3 ~/.openclaw/skills/sending-meeting-confirmations/scripts/check_confirmation_state.py --cleanup
```

## Cron Schedule

**Schedule:** Daily at 7:00 AM Arizona time
**Expression:** `0 7 * * *`

Runs automatically via OpenClaw cron system. See `jobs.json` configuration.

## Confirmation Criteria

A meeting gets a confirmation if:
- Has at least one external attendee (non-Intuit, not Aaron's email)
- Meeting is today
- Meeting starts 2-24 hours from now
- Hasn't been confirmed already (tracked in state file)
- Aaron hasn't declined the invite

## External Attendee Definition

External means:
- Email domain is NOT `intuit.com` or `intuit.net`
- Email is NOT one of Aaron's addresses:
  - aaroneden77@gmail.com
  - aaron@brainbridge.app
  - aaron@aitrailblazers.org
  - aaron_eden@intuit.com

## State Management

**File:** `~/.openclaw/memory/meeting-confirmations.json`

Tracks which meetings have been confirmed to prevent duplicates:
```json
{
  "confirmed": [
    {
      "event_id": "abc123",
      "meeting_title": "Client Call",
      "attendees": ["client@example.com"],
      "confirmed_at": "2026-02-10T07:00:00-07:00"
    }
  ],
  "last_run": "2026-02-10T07:00:00-07:00"
}
```

State automatically cleaned of entries older than 30 days.

## Message Template

Template location: `templates/confirmation-message.md`

Available variables:
- `{{name}}` - Attendee first name
- `{{time}}` - Meeting time (e.g., "2:30 PM")
- `{{date}}` - Meeting date (e.g., "Monday, February 10")
- `{{meeting_title}}` - Meeting title
- `{{location_line}}` - Formatted location line
- `{{location}}` - Raw location

Default template:
```
Hi {{name}},

Quick note to confirm our meeting today at {{time}}.

{{location_line}}

Looking forward to connecting then.

Best,
Aaron
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `send_confirmation.py` | Main entry point - sends confirmations |
| `gather_external_meetings.py` | Query calendars for external meetings |
| `check_confirmation_state.py` | Prevent duplicates, manage state |
| `templates/confirmation-message.md` | Email message template |

## Safety Guardrails

- **Dry run default**: Must explicitly use `--send` or set `OPENCLAW_CONFIRMATION_SEND=1`
- **State deduplication**: Won't confirm same meeting twice
- **Time window**: Only confirms meetings 2-24 hours out
- **Declined events**: Skips meetings Aaron declined
- **External only**: Never confirms internal Intuit meetings

## Integration

This skill integrates with:
- **Google Calendar** (via gog CLI) - reads events
- **Gmail** (via gog CLI) - sends confirmations
- **Telegram** - notifies Aaron of confirmations sent

## Output Format

JSON output includes:
```json
[
  {
    "to": "client@example.com",
    "subject": "Confirming: Client Call today at 2:30 PM",
    "sent": true,
    "dry_run": false,
    "meeting": "Client Call",
    "attendee": "client@example.com",
    "meeting_time": "2:30 PM",
    "status": "sent"
  }
]
```

## Files

- `SKILL.md` - This documentation
- `scripts/send_confirmation.py` - Main confirmation script
- `scripts/gather_external_meetings.py` - Calendar query script
- `scripts/check_confirmation_state.py` - State management script
- `templates/confirmation-message.md` - Email template
