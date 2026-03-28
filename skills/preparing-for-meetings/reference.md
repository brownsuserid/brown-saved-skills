# Pre-Meeting Prep Skill

Gathers context for meetings starting in 45-75 minutes and sends prep to Telegram group chat (1586059256:208299).

## What It Does

1. **Query calendars** for meetings in 45-75 minute window
2. **Skip duplicates** (tracks prepped meetings via state file)
3. **Research attendees** using Contact Research SOP
4. **Gather context** from Airtable deals, Obsidian notes, tasks
5. **Send prep summary** to Telegram
6. **Update state** with prepped event IDs

## Calendars Checked

| Account | Type |
|---------|------|
| `aaron@brainbridge.app` | Business |
| `aaroneden77@gmail.com` | Personal |
| `aaron@aitrailblazers.org` | Nonprofit |

**Skips:** Work/Intuit calendar

## Usage

### Via Agent

**SKILL:** `~/.openclaw/skills/maintaining-relationships/`

**Steps:**
1. Read SKILL.md
2. Run prep script:
   ```
   ~/.openclaw/skills/maintaining-relationships/scripts/preparing-for-meetings/prep-meeting.sh
   ```
3. For each `MEETING|` line in output:
   - Run Contact Research SOP for attendees
   - Search past meeting transcripts with each attendee:
     ```
     python3 ~/.openclaw/skills/maintaining-relationships/scripts/searching-meeting-transcripts/search_transcripts.py \
       --query "Attendee Name" --max 3
     ```
     Then `gog docs cat <fileId>` the most recent transcript to get context from the last conversation.
   - Search local file archives for historical context (old Slack messages, LinkedIn connections, past business docs):
     ```
     python3 ~/.openclaw/skills/maintaining-relationships/scripts/searching-local-files/search_local_files.py \
       --query "Attendee Name" --max 5
     ```
   - Search Airtable/Obsidian for context
   - Build prep summary
4. Send to Telegram group chat (1586059256:208299)
   (State file is updated automatically by the script)

### State Management

**File:** `~/clawd/memory/prep-state.json`
```json
{
  "prepared": ["eventId1", "eventId2"],
  "lastRun": "2026-02-07T10:15:00Z"
}
```

The script automatically appends new event IDs to the state file after outputting them.

## Cron Job

**Schedule:** Every 20 minutes during working hours (5 AM - 8 PM)
**Expression:** `*/20 5-20 * * *`

## Output Format

The script outputs `MEETING|calendar|eventId|summary|startTime` lines. The agent formats each as:

```
PRE-MEETING PREP

**Meeting:** [Title]
**Time:** [Start] (in ~X minutes)
**Calendar:** [Calendar Name]

**Attendees:**
- [Name] - [Context from contact research]

**Last Meeting:**
- [Date], [Summary of key discussion points from transcript]
- Action items from last time: [any commitments made]

**Context:**
- [Related deal/project]
- [Open tasks]
- [Previous notes]

**Focus:**
- [Key points to address]
```

## Files

- `scripts/prep-meeting.sh` - Main script (finds meetings, updates state)
- `SKILL.md` - This documentation

## Notes

- Silent if no meetings (no spam)
- Requires `gog` CLI with calendar access
- Uses Contact Research SOP for attendee lookup
