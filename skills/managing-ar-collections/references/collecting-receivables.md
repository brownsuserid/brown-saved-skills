# Collecting Receivables

> Before drafting anything: read [persona-guide.md](persona-guide.md)
> For general email voice: read [email-style-guide](../../.claude/skills/email-style-guide/reference.md)

## The Escalation Ladder

One email per tier per invoice. Never skip a tier. Never send the same tier twice.

| Days Past Due | Vibe | Who |
|--------------|------|-----|
| 7 | "Hey, heads up" | Taylor |
| 14 | "Just circling back" | Taylor |
| 30 | "Flagging this for Aaron" | Taylor sends final note, Aaron/Josh take over |

## Email Templates

These are starting points, not scripts. Mix up the wording so it doesn't feel like a robot wrote it (even though one did). Keep it breezy. People pay faster when they don't feel attacked.

### 7-Day: The Friendly Nudge

**Subject:** Quick heads up on Invoice #[NUM]

Hey [First Name],

Just wanted to make sure Invoice #[NUM] for $[AMT] didn't get lost in the shuffle. It was due on [DATE].

You can pay through the link in the original invoice email. If you need it resent, just let me know.

Taylor Morgan
Billing Coordinator
Brain Bridge
billing@brainbridge.app

### 14-Day: The Follow-Up

**Subject:** Following up on Invoice #[NUM] ($[AMT])

Hey [First Name],

Circling back on Invoice #[NUM] for $[AMT] from [DATE]. If payment's already on its way, ignore this completely.

Otherwise, could you give me a quick update on timing? Happy to resend the invoice or sort out any questions.

Taylor Morgan
Billing Coordinator
Brain Bridge
billing@brainbridge.app

### 30-Day: The Handoff

**Subject:** Invoice #[NUM], quick note

Hey [First Name],

I've reached out a couple times about Invoice #[NUM] for $[AMT] and wanted to touch base one more time. I'm going to have Aaron follow up with you directly on this one.

If anything on our end needs adjusting, just say the word. We appreciate the partnership and want to keep things smooth.

Taylor Morgan
Billing Coordinator
Brain Bridge
billing@brainbridge.app

**After the 30-day email:** Taylor's done. Create a task for Aaron.

```bash
python3 ~/.openclaw/.claude/skills/executing-tasks/scripts/create_task.py \
  --base bb \
  --title "AR: Personal follow-up needed - [Customer] - Invoice #[NUM] (30+ days)" \
  --description "Taylor sent 7, 14, and 30-day reminders. No payment. Aaron or Josh should reach out personally." \
  --project recXFT8s5hBfYurjp \
  --assignee aaron \
  --for-today
```

## Drafting & Tracking

Draft the email:
```bash
python3 ~/.openclaw/.claude/skills/using-gog/scripts/draft_email.py \
  --account bb \
  --from "billing@brainbridge.app" \
  --to <customer_email> \
  --subject "<per template>" \
  --body "<personalized email>"
```

Then create a tracking task for the next tier:
```bash
python3 ~/.openclaw/.claude/skills/executing-tasks/scripts/create_task.py \
  --base bb \
  --title "AR: [next_tier]-day reminder - [Customer] - Invoice #[NUM]" \
  --description "Previous [tier]-day sent. Next escalation due if still unpaid." \
  --project recXFT8s5hBfYurjp \
  --assignee pablo \
  --due-date "[next tier trigger date]"
```

## QBO Automated Reminders

QBO can handle the pre-due nudges so Taylor only shows up when things are actually late.

**Setup** (via Playwright, one time): Navigate to `Settings > Account and settings > Sales > Reminders` in QBO.

**Recommended config:**
- Reminder 1: 3 days before due ("Your invoice is coming up")
- Reminder 2: Day of ("Due today")
- Reminder 3: 3 days after due ("Just past due")

These come from QBO directly, not from billing@. Taylor's manual follow-ups kick in at day 7, after QBO's reminders have already had their shot.

## Guardrails

- **Check QBO first.** If the invoice got paid since the task was created, skip the email and close the task.
- **One per tier per invoice.** Escalate, don't repeat.
- **Draft only.** Aaron or Josh sends.
- **30-day handoff is final** for Taylor.
