---
name: using-gog
description: "How to use the gog CLI (v0.12.0, Homebrew 2026-03-24) to interact with Google Workspace: Gmail, Calendar, Drive, Docs, Sheets, Slides, Chat, Tasks, Contacts, People, Groups, Keep, Forms, Classroom, Admin, and Apps Script. Use this skill whenever a task involves reading, searching, creating, or modifying anything in Google Workspace, even if the user doesn't mention gog explicitly. Also use it for drafting emails, searching inboxes, managing calendar events, uploading to Drive, editing Google Docs, reading spreadsheets, or any Google API interaction. If the request touches Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, or any other Google service, this is the skill to consult."
---

# gog

CLI for Google Workspace. For full command/flag details, see `references/full-command-reference.md`.

## Accounts

Aaron has three Google accounts. Pick the right one with `--account <email>`:

| Alias | Email | Use for |
|-------|-------|---------|
| personal | aaroneden77@gmail.com | Personal, family, non-work |
| bb | aaron@brainbridge.app | Brain Bridge business |
| aitb | aaron@aitrailblazers.org | AI Trailblazers nonprofit |

When the context makes the account obvious (e.g., a BB deal follow-up), use it without asking. When ambiguous, ask.

## Approval Required

These actions change external state that Aaron or others can see. Never execute them without confirming first, even when the user's request seems to imply the action. "Decline my early meetings" still requires you to list which specific meetings you found and ask "Want me to decline these?" before running any commands. "Send that email" still requires showing the draft and getting a "yes."

The reason: vague instructions can match the wrong items. A search might return unexpected results, hit the wrong account, or pull stale data. Confirming the specific targets prevents mistakes that are hard to undo (sent emails, declined invites, deleted files). The cost of one extra confirmation is near zero; the cost of acting on the wrong item is high.

**How to confirm:** Show what you found, name the specific items you plan to act on, and wait for explicit approval before executing. One confirmation per batch is fine.

**Example:**
- User: "Decline anything before 9am tomorrow"
- You: Search calendar, then respond: "Found 2 events before 9am: (BBI) Inbox Management at 7:15am and (BBI) Daily Check-in at 8:30am. Want me to decline both?"
- User: "Yes" → now execute

**Actions requiring confirmation:**
- Sending email (`gog gmail send`, `draft_email.py --send`, `gog gmail drafts send`)
- Deleting calendar events (`gog calendar delete`)
- Creating events with attendees (`gog calendar create --attendees`)
- Responding to calendar invites (`gog calendar respond`)
- Sending chat messages/DMs (`gog chat messages send`, `gog chat dm send`)
- Deleting tasks (`gog tasks delete`, `gog tasks clear`)
- Batch-deleting Gmail messages (`gog gmail batch delete`) — permanent, not trash
- Deleting or sharing Drive files (`gog drive delete`, `gog drive share`)
- Deleting contacts (`gog contacts delete`)
- Clearing sheets data (`gog sheets clear`)
- Writing/deleting Google Doc content (`gog docs write --replace`, `gog docs delete`)
- Running Apps Script functions (`gog appscript run`)

Everything else (search, list, read, get, export, append to docs) is safe to run freely.

## Scripting Flags

Always pass `--json` when you need to parse output programmatically. Other useful flags:
- `--results-only` — strips pagination envelope, returns just the data array
- `--select field1,field2` — cherry-pick fields from JSON output
- `--plain` — TSV output for simple parsing
- `--dry-run` / `-n` — preview what would happen without making changes
- `--fail-empty` — exit code 3 when no results (useful in scripts)
- `--no-input` — never prompt; fail instead (CI mode)
- `--access-token` / `$GOG_ACCESS_TOKEN` — use a provided token directly (bypasses stored refresh tokens)
- `--client` — select a named OAuth client (for multi-client setups)
- `--enable-commands` — restrict available top-level commands

---

## Gmail

**Multi-account search:** `python3 scripts/search_email.py "query"` searches all 3 inboxes at once. Supports `--account bb`, `--recent 7`, `--messages`, `--raw`, `--max N`.

Core patterns:
```bash
# Search threads
gog gmail search "newer_than:7d from:example.com" --max 10 --account <email> --json

# Search individual messages (ignores threading)
gog gmail messages search "in:inbox subject:invoice" --max 20 --account <email> --json

# Read a thread or message
gog gmail thread get <threadId> --account <email>
gog gmail get <messageId> --account <email>

# Download attachment
gog gmail attachment <messageId> <attachmentId> --out /tmp/file.pdf --account <email>

# Archive (remove from inbox)
gog gmail archive <messageId> --account <email>

# Mark read / unread
gog gmail mark-read <messageId> --account <email>
gog gmail unread <messageId> --account <email>

# Trash
gog gmail trash <messageId> --account <email>
```

**Drafting email (default, safe):** Use the script for auto-signature:
```bash
python3 scripts/draft_email.py --account [personal|bb|aitb] --to a@b.com --subject "Hi" --body "Body text"
```
Supports `--reply-to-message-id`, `--cc`, `--bcc`, `--no-signature`, `--body-file`, `--body-stdin`.

**Sending with tracking (approval required):** Same script, add `--send --i-have-human-approval`:
```bash
python3 scripts/draft_email.py --account bb --to a@b.com --subject "Hi" --body "Body text" \
    --send --i-have-human-approval
```
This sends via `gog gmail send --track`, enabling open tracking by default. Add `--no-track` to disable.

**CRITICAL:** `--send` will hard-fail without `--i-have-human-approval`. The workflow is:
1. Show the full email (to, subject, body) to the user
2. Get an explicit "yes" / "send it" / equivalent
3. Only then run with `--send --i-have-human-approval`

**Sending directly via gog** (approval required, no auto-signature):
```bash
gog gmail send --to a@b.com --subject "Hi" --body-file ./message.txt --track --account <email>
```
`--body` does not interpret `\n`. Use `--body-file -` with a heredoc for multi-line, or `--body-html` for rich formatting.

**Reply patterns:**
- Reply: `gog gmail send --reply-to-message-id <msgId> --to a@b.com --subject "Re: ..." --body "..."`
- Reply all: `gog gmail send --reply-to-message-id <msgId> --reply-all --body "..."`
- Reply in thread: `gog gmail send --thread-id <threadId> --to a@b.com --subject "Re: ..." --body "..."`

## Calendar

```bash
# Today's events
gog calendar events --today --account <email> --json

# Date range (all calendars)
gog calendar events --from 2025-03-01 --to 2025-03-07 --all --account <email>

# This week / next N days
gog calendar events --week --account <email>
gog calendar events --days 7 --account <email>

# Search
gog calendar search "meeting" --from today --to friday --account <email>

# Free/busy and conflicts
gog calendar freebusy primary --from today --to friday --account <email>
gog calendar conflicts --from today --to friday --account <email>

# Create event
gog calendar create primary --summary "Title" --from <iso> --to <iso> --account <email>
# Add: --attendees a@b.com,c@d.com  --location "Room 1"  --with-meet  --event-color 7

# Update / respond / delete
gog calendar update primary <eventId> --summary "New Title" --account <email>
gog calendar respond primary <eventId> --status accepted --account <email>
gog calendar delete primary <eventId> --account <email>
```

`calendarId` defaults to `primary` when omitted. Use `gog calendar calendars` to list all.

## Drive

**Multi-account search:** `python3 scripts/search_drive.py "query"` searches all 3 drives. Supports `--account bb`, `--type doc|sheet|pdf`, `--recent 7`, `--raw`, `--max N`, `--no-shared`.

```bash
# List / search
gog drive ls --parent <folderId> --account <email> --json
gog drive search "query" --max 10 --account <email> --json
gog drive search "name='Folder' and mimeType='application/vnd.google-apps.folder'" --raw-query --account <email> --json

# Download / upload
gog drive download <fileId> --out /tmp/file.pdf --account <email>
gog drive upload ./file.pdf --parent <folderId> --account <email>

# Organize
gog drive mkdir "Folder Name" --parent <parentId> --account <email>
gog drive move <fileId> --parent <newFolderId> --account <email>
gog drive rename <fileId> "New Name" --account <email>
gog drive copy <fileId> "Copy Name" --account <email>

# Share / permissions
gog drive share <fileId> --email user@example.com --role reader --account <email>
gog drive unshare <fileId> <permissionId> --account <email>
gog drive permissions <fileId> --account <email>

# Web URL (offline, no API call)
gog open <fileId>
gog drive url <fileId>    # also works for multiple IDs

# Comments on Drive files
gog drive comments list <fileId> --account <email>
gog drive comments create <fileId> "Comment text" --account <email>
gog drive comments reply <fileId> <commentId> "Reply text" --account <email>
gog drive comments update <fileId> <commentId> "Updated text" --account <email>
gog drive comments delete <fileId> <commentId> --account <email>

# Shared drives
gog drive drives --account <email>
```

AITB shared drive ID: `0AIkaB4BxP-erUk9PVA`. Use `gog drive ls --parent 0AIkaB4BxP-erUk9PVA --account aaron@aitrailblazers.org`.

## Docs

Docs now supports full in-place editing:

```bash
# Read
gog docs cat <docId> --account <email>
gog docs info <docId> --account <email>

# Create
gog docs create "Title" --parent <folderId> --account <email>

# Write (replaces all content - plain text only)
gog docs write <docId> "Content here" --account <email>
echo "text" | gog docs write <docId> --file - --account <email>

# Write with markdown formatting (converts to Google Docs formatting)
# First write a placeholder, then find-replace with markdown format
echo "PLACEHOLDER" | gog docs write <docId> --file - --account <email>
gog docs find-replace <docId> "PLACEHOLDER" --content-file ./content.md --format=markdown --account <email>

# Append
gog docs write <docId> "More content" --account <email>

# Insert at position
gog docs insert <docId> "Text" --index 1 --account <email>

# Find and replace
gog docs find-replace <docId> "old text" "new text" --account <email>
gog docs find-replace <docId> "old text" --content-file ./content.md --format=markdown --account <email>

# Delete text range
gog docs delete <docId> --start 1 --end 50 --account <email>

# Export
gog docs export <docId> --format txt --out /tmp/doc.txt --account <email>

# Comments
gog docs comments list <docId> --account <email>
gog docs comments add <docId> "Comment text" --account <email>
gog docs comments resolve <docId> <commentId> --account <email>
```

`--markdown` flag on `write` converts markdown to Google Docs formatting (requires `--replace`).

## Sheets

```bash
# Read
gog sheets get <sheetId> "Tab!A1:D10" --json --account <email>
gog sheets metadata <sheetId> --account <email>

# Write
gog sheets update <sheetId> "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]' --account <email>
gog sheets append <sheetId> "Tab!A:C" --values-json '[["x","y","z"]]' --insert INSERT_ROWS --account <email>

# Export
gog sheets export <sheetId> --format csv --out /tmp/data.csv --account <email>

# Create / copy / clear / format
gog sheets create "My Sheet" --account <email>
gog sheets clear <sheetId> "Tab!A2:Z" --account <email>
gog sheets format <sheetId> "Tab!A1:B2" --format-json '{"textFormat":{"bold":true}}' --account <email>
```

`--input` defaults to `USER_ENTERED`; use `--input RAW` for literal values.

## Slides

```bash
gog slides info <presentationId> --account <email>
gog slides create "Title" --account <email>
gog slides copy <presentationId> "New Title" --account <email>
gog slides export <presentationId> --format pdf --out /tmp/deck.pdf --account <email>
```

## Chat

```bash
# Spaces
gog chat spaces list --account <email>
gog chat spaces find "Space Name" --account <email>

# Messages
gog chat messages send <spaceName> --text "Hello" --account <email>
gog chat messages send <spaceName> --text "Reply" --thread <threadName> --account <email>
gog chat messages list <spaceName> --max 20 --account <email>

# DMs
gog chat dm send user@example.com --text "Hello" --account <email>
```

## Tasks

```bash
gog tasks lists list --account <email>
gog tasks list <tasklistId> --account <email>
gog tasks add <tasklistId> --title "Task" --due 2025-03-01 --account <email>
gog tasks done <tasklistId> <taskId> --account <email>
gog tasks update <tasklistId> <taskId> --title "New name" --account <email>
gog tasks delete <tasklistId> <taskId> --account <email>
```

## Contacts & People

```bash
# Contacts
gog contacts search "John" --max 10 --account <email>
gog contacts create --given "John" --family "Doe" --email "john@example.com" --account <email>

# People / directory
gog people me --account <email>
gog people search "Name" --max 10 --account <email>
```

## Forms

```bash
gog forms get <formId> --account <email>
gog forms create --title "Survey" --account <email>
gog forms responses list <formId> --account <email> --json
gog forms responses get <formId> <responseId> --account <email>
```

## Groups

```bash
gog groups list --account <email>
gog groups members <groupEmail> --account <email>
```

## Admin (Workspace)

Requires domain-wide delegation. For managing Workspace users and groups.

```bash
# Users
gog admin users list --account <email>
gog admin users get <userEmail> --account <email>
gog admin users create <email> --given "First" --family "Last" --password "..." --account <email>
gog admin users suspend <userEmail> --account <email>

# Groups
gog admin groups list --account <email>
gog admin groups members list <groupEmail> --account <email>
```

## Keep

Google Keep (Workspace only, requires service account with domain-wide delegation).

```bash
gog keep list --service-account <path> --impersonate <email>
gog keep get <noteId> --service-account <path> --impersonate <email>
gog keep search "query" --service-account <path> --impersonate <email>
gog keep create --title "Note" --body "Content" --service-account <path> --impersonate <email>
gog keep delete <noteId> --service-account <path> --impersonate <email>
gog keep attachment <attachmentName> --service-account <path> --impersonate <email>
```

## Apps Script

```bash
gog appscript get <scriptId> --account <email>
gog appscript content <scriptId> --account <email>
gog appscript run <scriptId> <function> --params '[1, "arg"]' --account <email>
gog appscript create --title "My Script" --parent-id <fileId> --account <email>
```

## Email Tracking

Track email opens via a Cloudflare Worker pixel:
```bash
gog gmail track setup --account <email>    # deploy Cloudflare Worker
gog gmail track status                      # show tracking config
gog gmail track opens [<tracking-id>] --account <email>  # query opens
```

## Top-Level Aliases

These shortcuts work at the `gog` root level:
- `gog send` = `gog gmail send`
- `gog ls` = `gog drive ls`
- `gog search` = `gog drive search`
- `gog download` = `gog drive download`
- `gog upload` = `gog drive upload`
- `gog login` = `gog auth add`
- `gog logout` = `gog auth remove`
- `gog status` = `gog auth status`
- `gog me` = `gog people me`
- `gog open <id>` = resolve any Google ID/URL to a web URL
- `gog whoami` = `gog people me`
- `gog exit-codes` = `gog agent exit-codes` (print stable exit codes for automation)

## Config Management

```bash
gog config list                # show all config values
gog config get <key>           # get a specific value
gog config set <key> <value>   # set a value
gog config unset <key>         # remove a value
gog config keys                # list available config keys
gog config path                # print config file path
```

## Agent Helpers

```bash
gog exit-codes                 # print stable exit codes (0=ok, 1=error, 2=usage, 3=empty, 4=auth, 5=not_found, 6=permission, 7=rate_limited, 8=retryable, 10=config, 130=cancelled)
gog schema [<command>]         # machine-readable JSON schema for any command (useful for tool generation)
gog time now                   # print current time
gog completion <shell>         # generate shell completions (bash|zsh|fish|powershell)
```

---

## Token Refresh

OAuth tokens expire every 7 days (Google Cloud "Testing" mode).

**Guided refresh (run by assistant):**
1. `gog auth list --json` to get accounts
2. For each account, tell the user: "Sign in with **{email}**", wait for "go"
3. Run: `gog auth add {email} --services user --force-consent`

**Manual refresh:** `bash ~/.openclaw/skills/using-gog/scripts/refresh_tokens.sh`

Check status: `gog auth status`

## Email Formatting

- Prefer plain text. Use `--body-file` for multi-paragraph messages.
- `--body` does not unescape `\n`. Use a heredoc with `--body-file -`:
  ```bash
  gog gmail send --to a@b.com --subject "Hi" --body-file - <<'EOF'
  Hi Name,

  Paragraph one.

  Best,
  Aaron
  EOF
  ```
- Use `--body-html` only when rich formatting is needed.

## Notes

- `gog gmail search` returns threads; `gog gmail messages search` returns individual messages.
- Gmail aliases: `gog mail` or `gog email` work.
- Calendar aliases: `gog cal`, Drive: `gog drv`, Docs: `gog doc`, etc.
- `gog schema <command>` returns machine-readable JSON schema for any command.
