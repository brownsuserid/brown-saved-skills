# Creating Invoices in QBO

> Tool: QBO MCP Server (`mcp__quickbooks__*` tools)
> Fallback: Playwright MCP if QBO MCP is not configured

## When to Use

- Customer has completed work and needs to be billed
- Token usage for the month needs to be invoiced (see [token-billing.md](token-billing.md) for the full monthly process)
- One-off project invoice

## Finding the Customer

1. Look up the customer contact: `python3 ~/.openclaw/.claude/skills/looking-up-contacts/scripts/search_contacts.py "[Customer Name]" --json`
2. Find or create the customer in QBO: use `mcp__quickbooks__search_customers` with the customer name
3. If no QBO match, use `mcp__quickbooks__create_customer` with details from Airtable

## Creating the Invoice

Use `mcp__quickbooks__create_invoice`:

```json
{
  "customer_ref": "<QBO_CUSTOMER_ID>",
  "line_items": [
    {
      "description": "AI Token Services, March 2026",
      "qty": 1,
      "unit_price": 2500
    }
  ],
  "txn_date": "2026-03-28"
}
```

Key decisions:
- **Terms:** Net 30 unless the customer's contract says otherwise
- **Line item description:** Be specific about the service period and what's being billed
- **Amount:** Always confirm with Aaron before creating. No guessing.

## After Creating

1. Tell Aaron the invoice details (customer, amount, due date, invoice number)
2. Create a tracking task:

```bash
python3 ~/.openclaw/.claude/skills/executing-tasks/scripts/create_task.py \
  --base bb \
  --title "AR: Track payment - [Customer] - Invoice #[NUM] ($[AMT])" \
  --description "Invoice created in QBO. Due [date]. If unpaid at 7 days past due, escalate to collection workflow." \
  --project recXFT8s5hBfYurjp \
  --assignee pablo \
  --due-date "[due date + 7 days]"
```

## Checking Outstanding AR

To find all overdue invoices:

```
mcp__quickbooks__search_invoices with filters:
  Balance > 0
  DueDate < [today]
```

This is the fastest way to answer "who hasn't paid?" without manually checking QBO in a browser.
