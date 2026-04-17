# Token Billing

> Tool: QBO MCP Server, AWS "tuk" dashboard
> Contact lookup: `~/.openclaw/.claude/skills/looking-up-contacts/scripts/search_contacts.py`

## How It Works

Brain Bridge customers consume AI tokens. BB marks up actual usage and bills monthly. No pre-purchased blocks. The markup rate varies by customer, so always ask Aaron if you don't know it for a specific account.

## Where to Find Token Usage

The **Customer Token Usage (tuk)** dashboard on AWS shows each customer's actual token consumption. Pull the previous month's numbers from there at billing time.

## Monthly Billing Process

### Step 1: Pull Usage from tuk Dashboard

Check the tuk dashboard for each active customer's token consumption for the billing period. Present a summary:

```
Customer: [Name]
Period: [Month Year]
Actual token cost: $[amount]
Markup rate: [ask Aaron if unknown]
Invoice amount: $[marked-up amount]
```

Get Aaron's approval on the numbers before creating anything.

### Step 2: Create the Invoice

Follow [creating-invoices.md](creating-invoices.md). Use:
- **Description:** "AI Token Services, [Month Year]"
- **Amount:** The marked-up total for actual usage

Since usage varies month to month, always verify current numbers. Don't carry forward last month's figure.

### Step 3: Track It

```bash
python3 ~/.openclaw/.claude/skills/executing-tasks/scripts/create_task.py \
  --base bb \
  --title "AR: Track payment - [Customer] - [Month] token billing ($[AMT])" \
  --description "Monthly token invoice created in QBO. Due [date]. Monitor for payment." \
  --project recXFT8s5hBfYurjp \
  --assignee pablo \
  --due-date "[due date + 7 days]"
```

## Billing Calendar

- **1st of month:** Pull previous month's usage from tuk
- **1st-3rd:** Create invoices for all active customers
- **Due dates:** Per customer terms (usually Net 30)
- **7 days past due:** First follow-up kicks in (see [collecting-receivables.md](collecting-receivables.md))
