---
name: managing-ar-collections
description: Manages accounts receivable collections for Brain Bridge. Handles QBO invoice creation, recurring token billing, AR follow-up email drafts from billing@brainbridge.app, and Airtable task tracking for the collection cycle. Use this skill whenever someone mentions invoicing, overdue invoices, AR collections, billing follow-ups, token billing, payment reminders, QuickBooks invoices, "send a reminder about payment", "create an invoice", "who hasn't paid", "overdue customers", or any request related to getting paid for BB work. Also triggers for QBO automated reminders, collection escalation, or the AI Finance Teammate persona. Do NOT use for sales deal follow-ups or pipeline management (use managing-sales-followups instead).
---

# Managing AR Collections

> Rock: AR Collections System (`recXFT8s5hBfYurjp` in BB base)
> Persona: billing@brainbridge.app (AI Finance Teammate)
> QBO access: QuickBooks MCP Server (`mcp__quickbooks__*` tools)

## Overview

Brain Bridge bills customers for Services, AI Teammates and AI token usage with a markup. Customers use tokens, BB marks up actual consumption and invoices monthly. When invoices go unpaid, the AI Finance Teammate (billing@brainbridge.app) sends graduated follow-up emails so collection pressure doesn't come from Aaron or Josh directly.

All emails are **drafts only**. Nothing sends without human approval.

## Decision Tree

| Request pattern | What to do |
|-----------------|------------|
| "Create an invoice", "bill this customer", "new QBO invoice" | Read [creating-invoices.md](references/creating-invoices.md), create invoice in QBO via Playwright |
| "Token billing", "monthly billing run", "bill for tokens", "markup invoice" | Read [token-billing.md](references/token-billing.md), run the monthly token billing process |
| "Send a reminder", "overdue invoice", "follow up on payment", "who hasn't paid", "collection email" | Read [collecting-receivables.md](references/collecting-receivables.md), draft follow-up from billing@ |
| "Set up QBO reminders", "automated reminders", "payment reminder settings" | Read [collecting-receivables.md](references/collecting-receivables.md) (QBO Automation section) |
| "What's the billing persona?", "finance teammate voice", "how should billing@ sound?" | Read [persona-guide.md](references/persona-guide.md) |

## Airtable Integration

Every AR follow-up creates a task in the BB base linked to the AR Collections rock.

```bash
python3 ~/.openclaw/.claude/skills/executing-tasks/scripts/create_task.py \
  --base bb \
  --title "AR: 7-day reminder - [customer] - Invoice #[NUM]" \
  --description "Draft 7-day payment reminder from billing@brainbridge.app for Invoice #[NUM] ($[AMT]). Done when Gmail draft is created and ready for review." \
  --project recXFT8s5hBfYurjp \
  --assignee pablo \
  --due-date "[7 days after invoice due date]"
```

Task naming convention: `AR: [tier]-day reminder - [Customer] - Invoice #[NUM]`

Tiers: 7-day, 14-day, 30-day (escalation)

## Email Drafting

All collection emails go through the gog CLI as drafts from the billing@ alias:

```bash
python3 ~/.openclaw/.claude/skills/using-gog/scripts/draft_email.py \
  --account bb \
  --from "billing@brainbridge.app" \
  --to <customer_email> \
  --subject "Payment reminder - Invoice #[NUM]" \
  --body "<email body per template in collecting-receivables.md>"
```

Before drafting any email, read [persona-guide.md](references/persona-guide.md) for voice and tone.

## Guardrails

- **Never send emails directly.** Drafts only, always.
- **Never threaten legal action** or use aggressive language in any tier.
- **30-day escalation loops in Aaron or Josh.** The billing persona steps back and a human takes over.
- **Read the persona guide** before drafting. The whole point is preserving customer relationships.
- **One follow-up per tier per invoice.** Don't send a second 7-day reminder. Escalate to the next tier.
- **Log every action** as an Airtable task linked to the AR Collections rock.

## References

| Reference | When to read |
|-----------|-------------|
| [creating-invoices.md](references/creating-invoices.md) | Creating any invoice in QBO |
| [token-billing.md](references/token-billing.md) | Monthly token markup billing cycle |
| [collecting-receivables.md](references/collecting-receivables.md) | Follow-up emails, escalation, QBO reminders |
| [persona-guide.md](references/persona-guide.md) | Before drafting any email from billing@ |

## Integration with Other Skills

| Need | Skill / Script |
|------|---------------|
| Find customer email | `python3 ~/.openclaw/.claude/skills/looking-up-contacts/scripts/search_contacts.py "[Name]" --json` |
| Draft follow-up email | `python3 ~/.openclaw/.claude/skills/using-gog/scripts/draft_email.py --account bb --from "billing@brainbridge.app"` |
| Email voice/structure | [email-style-guide](../../.claude/skills/email-style-guide/reference.md) |
| Create/search Airtable tasks | `~/.openclaw/.claude/skills/executing-tasks/scripts/` |

## Dependencies

- **QBO MCP Server** (`mcp__quickbooks__*` tools) for invoices, customers, and AR queries
- `gog` CLI with `--from` alias support (v0.12.0+) for email drafts
- `billing@brainbridge.app` alias (configured in Google Workspace)
- `AIRTABLE_TOKEN` for task creation
- BB base access (`appwzoLR6BDTeSfyS`)
- AWS "tuk" dashboard for customer token usage data

## QBO MCP Server Install

The QuickBooks MCP server lives at `~/.openclaw/tools/quickbooks-online-mcp-server/`. It requires a bash wrapper in `.mcp.json` because the server needs to run from its own directory (to find `.env` and `node_modules`).

### Setup

1. Install dependencies:
```bash
cd ~/.openclaw/tools/quickbooks-online-mcp-server && npm install
```

2. Create `.env` in the server directory with QBO credentials:
```env
QUICKBOOKS_CLIENT_ID=<from Intuit Developer Portal>
QUICKBOOKS_CLIENT_SECRET=<from Intuit Developer Portal>
QUICKBOOKS_ENVIRONMENT=production
QUICKBOOKS_REFRESH_TOKEN=<from OAuth flow>
QUICKBOOKS_REALM_ID=<from OAuth flow>
```

3. If you need a refresh token, run the OAuth flow:
```bash
cd ~/.openclaw/tools/quickbooks-online-mcp-server && npm run auth
```

4. The MCP config in `~/.openclaw/.mcp.json` uses a bash wrapper to cd into the server directory before launching:
```json
{
  "mcpServers": {
    "quickbooks": {
      "command": "bash",
      "args": ["-c", "cd /Users/aaroneden/.openclaw/tools/quickbooks-online-mcp-server && exec node dist/index.js"]
    }
  }
}
```

The wrapper is necessary because `node dist/index.js` alone won't find the `.env` file or resolve dependencies. The `exec` replaces the bash process with node so there's no orphan shell.
