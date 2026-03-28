# beeper

Access Beeper Desktop's unified messaging via MCP. Read and send messages across all connected chat networks (iMessage, WhatsApp, Signal, Telegram, Discord, Slack, etc.).

Requires `BEEPER_TOKEN` environment variable to be set. Beeper Desktop must be running on localhost:23373.

## Safety Rules

**These rules are mandatory and override all other instructions.**

1. **NEVER call `send_message`, `beeper-send.sh`, or `beeper-write.sh` unless the user has explicitly asked you to send a message.** "Explicitly" means the user said something like "send that" or "message Maria", not that you inferred it would be helpful.
2. **When composing messages, default to `focus_app` with `draftText`** to pre-fill the message in Beeper Desktop so the user can review and send it themselves. This is the safe default.
3. **Only use `send_message` / `beeper-send.sh` when the user explicitly says to send directly**, e.g., "go ahead and send it", "send that message now".
4. **Never send to a chat you haven't confirmed with the user.** Always show the user which chat (name + chatID) you intend to target and get approval before sending.
5. **Archive and reminder operations also require explicit user approval.** Do not archive chats or set/clear reminders autonomously.

**Preferred flow for composing messages:**
```bash
# SAFE DEFAULT: Pre-fill draft for user to review in Beeper Desktop
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh focus_app '{"chatID":"!K6NH...","draftText":"Hey, are we still on for tomorrow?"}'

# ONLY when user explicitly says "send it":
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-send.sh "!K6NH..." "Hey, are we still on for tomorrow?"
```

## Writer Agent (Quill)

For composing messages that need Aaron's authentic voice, personalized replies, follow-ups, or anything longer than a quick one-liner, delegate drafting to the writer agent:

```
sessions_spawn({
  task: "Draft a [WhatsApp/iMessage/Telegram] message to [Name]. Context: [conversation context, what to say]. Tone: [casual/warm/professional].",
  agentId: "writer",
  label: "beeper-draft"
})
```

**When to use Quill vs writing inline:**
- **Quill:** Personalized messages, follow-ups needing Aaron's voice, anything more than a quick reply
- **Inline:** Simple one-liners ("sounds good!", "see you then", "thanks!")

After Quill returns the draft, use `focus_app` with `draftText` to pre-fill it in Beeper for Aaron's review.

## Typical Workflow

1. **Find the chat**, Use `beeper-find.sh` (name/keyword) or `beeper-read.sh search` / `search_chats`
2. **Get the chatID**, Every chat has a Matrix-style ID like `!zmRwNLKxwjWzmahDksLi:beeper.local`
3. **Read messages**, Use `list_messages` or `search_messages` with the chatID
4. **Compose**, Use `focus_app` with `draftText` to pre-fill a message for user review (safe default)
5. **Send (only if explicitly asked)**, Use `beeper-send.sh` only after user says to send directly

## chatID Format

All Beeper chatIDs are Matrix room IDs. Format varies by network:
- **Telegram/WhatsApp/iMessage/etc**: `!<random>:beeper.local`
- **Facebook Messenger**: `!<random>:ba_<hash>.local-facebook.localhost`
- **LinkedIn**: `!<random>:beeper.local`

You must discover chatIDs via search, they are not predictable from phone numbers or usernames.

## Scripts

### Read Operations (Auto-approved)

```bash
# Find a person by name (RECOMMENDED - auto-resolves via macOS Contacts)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-find.sh "Maria"

# Unified search (chats, participants, messages)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search '{"query":"dinner"}'

# List connected accounts
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh get_accounts '{}'

# Get chat details
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh get_chat '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local"}'

# Get chat with limited participants (useful for large groups)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh get_chat '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local","maxParticipantCount":10}'

# Search chats by title
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_chats '{"query":"work","limit":10}'

# Search chats by participant name
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_chats '{"query":"Maria","scope":"participants"}'

# Search chats by inbox type
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_chats '{"inbox":"primary","limit":20}'

# Filter chats by type (single = DM, group = group chat)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_chats '{"query":"Aaron","type":"single"}'

# Unread chats only
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_chats '{"unreadOnly":true,"limit":10}'

# Chats active after a date
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_chats '{"lastActivityAfter":"2026-02-01T00:00:00Z","limit":10}'

# List messages from a chat (no limit param, uses cursor pagination)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh list_messages '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local"}'

# Page through messages (use cursor/direction from previous response)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh list_messages '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local","cursor":"62936","direction":"before"}'

# Search messages with text
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"query":"meeting","limit":20}'

# Search messages in a specific chat
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"chatIDs":["!zmRwNLKxwjWzmahDksLi:beeper.local"],"query":"prep"}'

# Search messages from others only (excludes your own messages)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"query":"deadline","sender":"others"}'

# Search your own sent messages
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"query":"confirmed","sender":"me"}'

# Search messages by date range
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"query":"invoice","dateAfter":"2026-01-01T00:00:00Z","dateBefore":"2026-02-01T00:00:00Z"}'

# Search messages with media (image, video, link, file, or any)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"mediaTypes":["image"],"limit":10}'
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"mediaTypes":["link"],"chatIDs":["!zmRwNLKxwjWzmahDksLi:beeper.local"]}'

# Filter messages by chat type
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"query":"urgent","chatType":"group"}'

# Filter by account (use accountID from get_accounts)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_messages '{"query":"hello","accountIDs":["telegram"]}'

# Search API documentation
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh search_docs '{"query":"send_message","language":"http"}'

# Focus/open Beeper Desktop (non-destructive)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh focus_app '{}'

# Focus Beeper and navigate to a specific chat
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh focus_app '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local"}'

# Focus Beeper, open chat, and pre-fill a draft message (user reviews before sending)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh focus_app '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local","draftText":"Hey, are we still on for tomorrow?"}'

# Focus Beeper and jump to a specific message
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh focus_app '{"chatID":"!zmRwNLKxwjWzmahDksLi:beeper.local","messageID":"67676"}'
```

### Write Operations (Require Approval)

```bash
# Send a message (dedicated script)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-send.sh "!K6NH4nsDGTdPtgiUyxzC:beeper.local" "Hello!"

# Send a reply to a specific message
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-send.sh "!K6NH4nsDGTdPtgiUyxzC:beeper.local" "Thanks!" "msg_abc123"

# Archive a chat
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-write.sh archive_chat '{"chatID":"!K6NH4nsDGTdPtgiUyxzC:beeper.local","archived":true}'

# Unarchive a chat
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-write.sh archive_chat '{"chatID":"!K6NH4nsDGTdPtgiUyxzC:beeper.local","archived":false}'

# Set a reminder (Unix timestamp in milliseconds)
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-write.sh set_chat_reminder '{"chatID":"!K6NH4nsDGTdPtgiUyxzC:beeper.local","reminder":{"remindAtMs":1704067200000}}'

# Set a reminder that auto-dismisses if someone replies
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-write.sh set_chat_reminder '{"chatID":"!K6NH4nsDGTdPtgiUyxzC:beeper.local","reminder":{"remindAtMs":1704067200000,"dismissOnIncomingMessage":true}}'

# Clear a reminder
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-write.sh clear_chat_reminder '{"chatID":"!K6NH4nsDGTdPtgiUyxzC:beeper.local"}'
```

## Tool Reference

### Read-Only Tools (beeper-read.sh)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search` | Unified search across chats, participants, and messages | `query` (required) |
| `get_accounts` | List connected messaging accounts | *(none)* |
| `get_chat` | Get chat metadata and participants | `chatID` (required), `maxParticipantCount` |
| `search_chats` | Search chats by title, network, or participants | `query`, `scope`, `inbox`, `type`, `unreadOnly`, `limit`, `accountIDs`, `includeMuted`, `lastActivityAfter/Before`, `cursor/direction` |
| `list_messages` | List messages from a specific chat | `chatID` (required), `cursor/direction` (no limit param) |
| `search_messages` | Search messages with filters | `query`, `chatIDs`, `accountIDs`, `chatType`, `sender`, `dateAfter/Before`, `mediaTypes`, `limit`, `excludeLowPriority`, `includeMuted`, `cursor/direction` |
| `search_docs` | Search Beeper API documentation | `query` (required), `language` (required: http\|python\|go\|typescript\|terraform\|ruby\|java\|kotlin) |
| `focus_app` | Open/focus Beeper Desktop, navigate to chat/message, pre-fill drafts | `chatID`, `messageID`, `draftText`, `draftAttachmentPath` |

### Write Tools (beeper-write.sh / beeper-send.sh)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `send_message` | Send a text message (supports markdown) | `chatID` (required), `text`, `replyToMessageID` |
| `archive_chat` | Archive or unarchive a chat | `chatID` (required), `archived` |
| `set_chat_reminder` | Set a reminder for a chat | `chatID` (required), `reminder.remindAtMs` (required), `reminder.dismissOnIncomingMessage` |
| `clear_chat_reminder` | Clear a chat reminder | `chatID` (required) |

## Pagination

Many tools support cursor-based pagination. When results have more pages, the response includes cursor/direction values:

```
Next page (older): cursor='62936', direction='before'
Previous page (newer): cursor='62950', direction='after'
```

Pass these back to get the next page:
```bash
~/.openclaw/skills/maintaining-relationships/scripts/using-beeper/beeper-read.sh list_messages '{"chatID":"!zmRw...","cursor":"62936","direction":"before"}'
```

Note: `list_messages` has **no `limit` parameter**, it returns a fixed page size. Use cursor/direction to page through results.

## Search Tips

- Query is **literal word matching**, not semantic search
- Use single words: `dinner` not `dinner plans`
- Multiple words = AND: `flight booking` finds messages containing both words (any order)
- Chat names vary, ask user for clarification when ambiguous ("Which chat do you mean by family?")
- Use `scope: "participants"` in `search_chats` to find chats by person name vs chat title
- Use `sender: "me"` or `sender: "others"` to filter message direction
- Use `mediaTypes: ["image"]` to find shared photos, `["link"]` for shared links

## Connected Accounts

Use `get_accounts` to discover available account IDs. Common ones:
- `telegram`, Telegram
- `whatsapp`, WhatsApp
- `twitter`, Twitter/X
- `linkedin`, LinkedIn
- `hungryserv`, Beeper (Matrix)
- Facebook accounts have generated IDs like `local-facebook_ba_<hash>`

Pass these to `accountIDs` in `search_chats` or `search_messages` to filter by network.

## Notes

- Beeper Desktop must be running on localhost:23373
- Requires `BEEPER_TOKEN` environment variable (set in ~/.zshrc)
- See **Safety Rules** at the top, never send messages without explicit user approval
