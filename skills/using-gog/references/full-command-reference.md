# gog Full Command Reference (v0.11.0)

Complete reference for all `gog` commands and flags. See `SKILL.md` for core usage patterns and approval rules.

---

## Top-Level Aliases

```
gog send [flags]                          Alias for 'gmail send'
gog ls [flags]                            Alias for 'drive ls'
gog search <query> [flags]                Alias for 'drive search'
gog download <fileId> [flags]             Alias for 'drive download'
gog upload <localPath> [flags]            Alias for 'drive upload'
gog login <email> [flags]                 Alias for 'auth add'
gog logout <email> [flags]                Alias for 'auth remove'
gog status [flags]                        Alias for 'auth status'
gog me [flags]                            Alias for 'people me'
gog open <target> [--type TYPE]           Print web URL for a Google URL/ID (offline)
                                          Types: auto|drive|folder|docs|sheets|slides|gmail-thread
```

---

## Auth

```
gog auth credentials set <credentials>       Store OAuth client credentials
gog auth credentials list                     List stored OAuth client credentials
gog auth add <email> --services <svc,...>     Authorize and store a refresh token
gog auth services                             List supported auth services and scopes
gog auth list                                 List stored accounts
gog auth status                               Show auth config and keyring backend
gog auth remove <email>                       Remove a stored refresh token
gog auth manage                               Open accounts manager in browser
gog auth keyring [<backend>]                  Configure keyring backend
gog auth alias                                Manage account aliases
gog auth tokens                               Manage stored refresh tokens
gog auth service-account                      Configure service account (Workspace)
gog auth keep --key=STRING <email>            Configure service account for Keep
```

---

## Gmail

### Search & Read

```
gog gmail search <query> [--max N] [--page TOKEN] [--oldest] [--timezone TZ]
    [--all] [--fail-empty]
gog gmail messages search <query> [--max N] [--page TOKEN]
gog gmail get <messageId> [--format full|metadata|raw] [--headers STRING]
gog gmail thread get <threadId>
gog gmail thread attachments <threadId>
gog gmail attachment <messageId> <attachmentId> [--out PATH] [--name FILENAME]
gog gmail url <threadId>
gog gmail history
```

### Send

```
gog gmail send
  --to STRING          Recipients (comma-separated; required unless --reply-all)
  --cc STRING          CC recipients (comma-separated)
  --bcc STRING         BCC recipients (comma-separated)
  --subject STRING     Subject (required)
  --body STRING        Body (plain text; required unless --body-html is set)
  --body-file STRING   Body file path (plain text; '-' for stdin)
  --body-html STRING   Body (HTML)
  --reply-to-message-id STRING   Reply to Gmail message ID
  --thread-id STRING   Reply within a Gmail thread
  --reply-all          Auto-populate recipients from original message
  --reply-to STRING    Reply-To header address
  --attach PATH,...    Attachment file path (repeatable)
  --from STRING        Send from verified alias
  --track              Enable open tracking
  --track-split        Send tracked messages separately per recipient
```

### Drafts

```
gog gmail drafts list
gog gmail drafts get <draftId>
gog gmail drafts create [same flags as send, except --reply-all/--thread-id/--track]
gog gmail drafts update <draftId> [same flags as create]
gog gmail drafts send <draftId>
gog gmail drafts delete <draftId>
```

### Labels

```
gog gmail labels list
gog gmail labels get <labelIdOrName>
gog gmail labels create <name>
gog gmail labels modify <threadId> ... [--add-labels STRING] [--remove-labels STRING]
```

### Thread Operations

```
gog gmail thread get <threadId>
gog gmail thread modify <threadId> [--add-labels STRING] [--remove-labels STRING]
gog gmail thread attachments <threadId>
```

### Batch Operations

```
gog gmail batch delete <messageId> ...
gog gmail batch modify <messageId> ... [--add-labels STRING] [--remove-labels STRING]
```

### Tracking

```
gog gmail track setup
gog gmail track opens [<tracking-id>]
gog gmail track status
```

### Settings

```
gog gmail settings [subcommands]
```

---

## Calendar

### List & Search

```
gog calendar calendars                        List all calendars
gog calendar events [<calendarId>]            List events (calendarId defaults to primary)
  --from STRING        Start time (RFC3339, date, or relative: today, tomorrow, monday)
  --to STRING          End time (RFC3339, date, or relative)
  --today              Today only
  --tomorrow           Tomorrow only
  --week               This week (uses --week-start, default Mon)
  --days N             Next N days
  --all                Fetch from all calendars
  --query STRING       Free text search
  --max N              Max results (default 10)
  --weekday            Include day-of-week columns
  --fields STRING      Comma-separated fields to return
gog calendar event <calendarId> <eventId>     Get single event
gog calendar search <query>                   Search events
  --from/--to/--today/--tomorrow/--week/--days (same as events)
  --calendar STRING    Calendar ID (default: primary)
  --max N              Max results (default 25)
gog calendar acl <calendarId>                 List calendar ACL
gog calendar freebusy <calendarIds>           Get free/busy
  --from STRING --to STRING
gog calendar conflicts                        Find scheduling conflicts
  --from STRING --to STRING
gog calendar time                             Show server time
```

### Create

```
gog calendar create <calendarId>
  --summary STRING               Event title
  --from STRING                  Start time (RFC3339)
  --to STRING                    End time (RFC3339)
  --description STRING           Description
  --location STRING              Location
  --attendees STRING             Comma-separated attendee emails
  --all-day                      All-day event (use date-only --from/--to)
  --rrule STRING,...             Recurrence rules (repeatable)
  --reminder METHOD:DURATION,... Custom reminders (e.g., popup:30m, email:1d; max 5)
  --event-color STRING           Event color ID (1-11)
  --visibility STRING            default|public|private|confidential
  --transparency STRING          opaque (busy) | transparent (free)
  --send-updates STRING          Notification: all|externalOnly|none (default: all)
  --with-meet                    Create Google Meet conference
  --guests-can-invite            Allow guests to invite others
  --guests-can-modify            Allow guests to modify event
  --guests-can-see-others        Allow guests to see other guests
  --source-url STRING            Source URL
  --source-title STRING          Source title
  --attachment URL,...            File attachment URL (repeatable)
  --private-prop KEY=VALUE,...   Private extended property (repeatable)
  --shared-prop KEY=VALUE,...    Shared extended property (repeatable)
```

### Update

```
gog calendar update <calendarId> <eventId>
  [all create flags, plus:]
  --add-attendee STRING          Add attendees (preserves existing)
  --scope STRING                 For recurring: single|future|all
  --original-start STRING        Original start time (required for scope=single/future)
```

### Other

```
gog calendar delete <calendarId> <eventId> [--scope STRING] [--original-start STRING]
gog calendar respond <calendarId> <eventId> --status accepted|declined|tentative|needsAction [--comment STRING]
gog calendar propose-time <calendarId> <eventId>    Generate URL to propose new time
gog calendar colors                                  Show available event colors
```

| ID | Hex | ID | Hex | ID | Hex |
|----|---------|----|---------|----|---------|
| 1  | #a4bdfc | 5  | #fbd75b | 9  | #5484ed |
| 2  | #7ae7bf | 6  | #ffb878 | 10 | #51b749 |
| 3  | #dbadff | 7  | #46d6db | 11 | #dc2127 |
| 4  | #ff887c | 8  | #e1e1e1 |    |         |

```
gog calendar users                                   List workspace users
gog calendar team <group-email>                      Show events for group members
  --from STRING --to STRING
```

### Workspace Event Types

```
gog calendar focus-time --from STRING --to STRING [<calendarId>]
gog calendar out-of-office --from STRING --to STRING [<calendarId>]
gog calendar working-location --from STRING --to STRING --type home|office|custom [<calendarId>]
```

---

## Drive

### List & Search

```
gog drive ls [--parent FOLDER_ID] [--max N] [--query STRING] [--page TOKEN]
gog drive search <query> [--max N] [--raw-query] [--[no-]all-drives]
gog drive get <fileId>
gog drive url <fileId> ...
gog drive drives                   List shared drives
```

### Download & Upload

```
gog drive download <fileId> [--out PATH] [--format pdf|csv|xlsx|pptx|txt|png|docx]
gog drive upload <localPath> [--name STRING] [--parent FOLDER_ID]
```

### Organize

```
gog drive mkdir <name> [--parent FOLDER_ID]
gog drive copy <fileId> <name> [--parent FOLDER_ID]
gog drive move <fileId> [--parent FOLDER_ID]
gog drive rename <fileId> <newName>
gog drive delete <fileId>
```

### Sharing

```
gog drive share <fileId> [--email STRING] [--role reader|writer] [--anyone] [--discoverable]
gog drive unshare <fileId> <permissionId>
gog drive permissions <fileId>
```

### Comments

```
gog drive comments list <fileId>
gog drive comments get <fileId> <commentId>
gog drive comments create <fileId> <content>
gog drive comments update <fileId> <commentId> <content>
gog drive comments delete <fileId> <commentId>
gog drive comments reply <fileId> <commentId> <content>
```

---

## Docs

### Read & Export

```
gog docs cat <docId> [--tab TAB_ID]           Print as plain text
gog docs info <docId>                          Get metadata
gog docs list-tabs <docId>                     List all tabs
gog docs export <docId> [--format pdf|docx|txt] [--out PATH]
```

### Create & Copy

```
gog docs create <title> [--parent FOLDER_ID]
gog docs copy <docId> <title> [--parent FOLDER_ID]
```

### Edit

```
gog docs write <docId> [<content>]             Write content (default: append)
  --file STRING          Read content from file (use - for stdin)
  --replace              Replace all content (default: append)
  --markdown             Convert markdown to Docs formatting (requires --replace)

gog docs insert <docId> [<content>]            Insert text at position
  --index INT            Character index (1 = beginning)
  --file STRING          Read from file (use - for stdin)

gog docs delete <docId>                        Delete text range
  --start INT            Start index (>= 1)
  --end INT              End index (> start)

gog docs find-replace <docId> <find> <replace> Find and replace text
  --match-case           Case-sensitive matching

gog docs update <docId>                        Update content
  --content STRING       Text to insert
  --content-file STRING  File containing text
  --format plain|markdown
  --append               Append instead of replace
  --debug                Debug markdown formatter
```

### Comments

```
gog docs comments list <docId> [--max N]
gog docs comments get <docId> <commentId>
gog docs comments add <docId> <content> [--quoted-text STRING]
gog docs comments reply <docId> <commentId> <content>
gog docs comments resolve <docId> <commentId> [--reopen]
gog docs comments delete <docId> <commentId>
```

---

## Sheets

```
gog sheets get <spreadsheetId> <range> [--json]
gog sheets metadata <spreadsheetId>
gog sheets update <spreadsheetId> <range> [<values>]
  --values-json STRING           Values as JSON 2D array
  --input USER_ENTERED|RAW       Value input option (default: USER_ENTERED)
  --copy-validation-from STRING  Copy data validation from range
gog sheets append <spreadsheetId> <range> [<values>]
  --values-json STRING
  --input USER_ENTERED|RAW
  --insert OVERWRITE|INSERT_ROWS
  --copy-validation-from STRING
gog sheets clear <spreadsheetId> <range>
gog sheets format <spreadsheetId> <range>
  --format-json STRING           CellFormat JSON
  --format-fields STRING         Field mask (e.g., textFormat.bold)
gog sheets create <title>
gog sheets copy <spreadsheetId> <title>
gog sheets export <spreadsheetId> [--format pdf|xlsx|csv] [--out PATH]
```

Inline values: comma-separated rows, pipe-separated cells (e.g., `"A|B" "1|2"`).

---

## Slides

```
gog slides export <presentationId> [--format pdf|pptx] [--out PATH]
gog slides info <presentationId>
gog slides create <title>
gog slides copy <presentationId> <title>
```

---

## Chat

### Spaces

```
gog chat spaces list
gog chat spaces find <name>
```

### Messages

```
gog chat messages send <space> --text STRING [--thread THREAD_NAME]
gog chat messages list <space> [--max N]
```

### Threads

```
gog chat threads [subcommands]
```

### DMs

```
gog chat dm send <email> --text STRING [--thread THREAD_NAME]
gog chat dm space <email>
```

---

## Tasks

```
gog tasks lists list                          List task lists
gog tasks list <tasklistId>                   List tasks
gog tasks get <tasklistId> <taskId>           Get task details
gog tasks add <tasklistId>                    Add a task
  --title STRING         Task title (required)
  --notes STRING         Task notes/description
  --due STRING           Due date (RFC3339 or YYYY-MM-DD)
  --parent STRING        Parent task ID (create as subtask)
  --previous STRING      Previous sibling task ID (controls ordering)
  --repeat STRING        Repeat: daily|weekly|monthly|yearly
  --repeat-count INT     Number of occurrences (requires --repeat)
  --repeat-until STRING  Repeat until date (requires --repeat)
gog tasks update <tasklistId> <taskId>        Update a task
gog tasks done <tasklistId> <taskId>          Mark completed
gog tasks undo <tasklistId> <taskId>          Mark needs action
gog tasks delete <tasklistId> <taskId>        Delete a task
gog tasks clear <tasklistId>                  Clear completed tasks
```

---

## Contacts

```
gog contacts list [--max N]
gog contacts search <query> [--max N]
gog contacts get <resourceName>
gog contacts create
  --given STRING         Given name (required)
  --family STRING        Family name
  --email STRING         Email address
  --phone STRING         Phone number
gog contacts update <resourceName> [--given/--family/--email/--phone]
gog contacts delete <resourceName>
gog contacts directory list                   Workspace directory
gog contacts directory search <query>         Search Workspace directory
gog contacts other [subcommands]              Other contacts
```

---

## People

```
gog people me                                 Your profile
gog people get <userId>                       Get user profile by ID
gog people search <query> [--max N]           Search Workspace directory
gog people relations [<userId>]               Get user relations
```

---

## Groups

```
gog groups list                               List groups you belong to
gog groups members <groupEmail>               List group members
```

---

## Keep (Workspace only)

```
gog keep list                                 List notes
gog keep get <noteId>                         Get a note
gog keep search <query>                       Search notes (client-side)
gog keep attachment <attachmentName>          Download attachment
```

Requires `--service-account` and `--impersonate` flags for service account auth.

---

## Forms

```
gog forms get <formId>                        Get a form
gog forms create --title=STRING               Create a form
gog forms responses list <formId> [--max N]   List form responses
gog forms responses get <formId> <responseId> Get a form response
```

---

## Apps Script

```
gog appscript get <scriptId>                  Get project metadata
gog appscript content <scriptId>              Get project content (source files)
gog appscript run <scriptId> <function>       Run a deployed function
  --params STRING        JSON array of parameters (default: [])
  --dev-mode             Run latest saved code if you own the script
gog appscript create --title=STRING           Create a project
  --parent-id STRING     Drive file ID to bind to
```

---

## Classroom

```
gog classroom courses [list|get|create|update|delete]
gog classroom students [list|get|add|remove]
gog classroom teachers [list|get|add|remove]
gog classroom roster <courseId>
gog classroom coursework [list|get|create|update|delete]
gog classroom materials [list|get|create|update|delete]
gog classroom submissions [list|get|grade|return|reclaim]
gog classroom announcements [list|get|create|update|delete]
gog classroom topics [list|get|create|update|delete]
gog classroom invitations [list|get|create|delete|accept]
gog classroom guardians [list|get|delete]
gog classroom guardian-invitations [list|get|create]
gog classroom profile [get]
```

---

## Agent Helpers

```
gog agent exit-codes                          Print stable exit codes for automation
gog schema [<command> ...]                    Machine-readable command/flag schema
  --include-hidden       Include hidden commands and flags
```

---

## Config

```
gog config get <key>                          Get a config value
gog config set <key> <value>                  Set a config value
gog config unset <key>                        Unset a config value
gog config list                               List all config values
gog config keys                               List available config keys
gog config path                               Print config file path
```

---

## Global Flags

These flags work with any command:

```
--account STRING       Account email to use (shorthand: -a)
--client STRING        OAuth client name
--json / -j            JSON output (best for scripting)
--plain / -p           TSV output (stable, parseable)
--results-only         Strip pagination envelope, return just results
--select STRING        Cherry-pick fields from JSON (comma-separated, dot paths)
--dry-run / -n         Preview without making changes
--force / -y           Skip confirmations
--no-input             Never prompt; fail instead (CI mode)
--fail-empty           Exit code 3 when no results
--verbose / -v         Enable verbose logging
--color auto|always|never
--enable-commands STRING   Restrict available top-level commands
```
