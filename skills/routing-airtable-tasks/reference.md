# Inbox Router

> Scripts: `~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/`
> Learned mappings: `~/.openclaw/skills/managing-projects/references/learned_mappings.json`

## Overview

Routes items from all inboxes (Airtable tasks, Gmail, Beeper messages) to the appropriate base and project. Uses learned mappings for automatic routing and explores goals/projects dynamically when needed.

**Inbox sources:**
- **Airtable**: Tasks in the Inbox project for each base
- **Gmail**: Emails in INBOX for personal, BB, and AITB accounts
- **Beeper**: Unread messages across all chats

## Inbox Gathering Scripts

```bash
# Gather all inboxes at once
~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_all_inbox.sh

# Or individually:
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_inbox.py      # Airtable
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_emails.py --max 50 --since 3d  # Gmail
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_beeper.py --limit 30  # Beeper
```

---

## Email Routing

### Step 0: Check Email Rules
Before routing, check `learned_mappings.json` for `email_rules` that match the sender.

```json
"email_rules": [
  {
    "from_pattern": "regex to match sender email",
    "from_name_pattern": "optional regex to match sender name",
    "account": "personal|bb|aitb",
    "add_labels": ["Digest"],
    "remove_labels": ["INBOX"],
    "note": "Why this rule exists"
  }
]
```

**If rule matches:** Apply labels and archive. No task needed.

**If no rule matches:** Proceed to routing workflow below.

### Email Routing Decision Tree

1. **Transactional/Receipt emails** (PayPal, invoices, confirmations) → Archive, no task
2. **Newsletters/Digests** → Add to Digest label, archive, no task
3. **Spam/Marketing** → Archive or delete, no task
4. **Actionable emails** (requires response, review, or follow-up) → Create task, then route

**When creating a task from email:**
- Task title: `[Contact Name] - [Action verb]` (e.g., "Sven Pleger - Reschedule call")
- Notes: Include email thread ID or link for reference
- Route using the Airtable task workflow below

---

## Beeper Message Routing

### Message Routing Decision Tree

1. **Greetings/Social** (Buenos dias, How are you) → Reply directly, no task
2. **Family/Group chats** → Read, reply if needed, no task unless action required
3. **Spam/Phishing links** → Ignore
4. **Actionable requests** (intro requests, meeting requests, questions needing research) → Create task, then route

**When creating a task from message:**
- Task title: `[Contact Name] - [Action verb]` (e.g., "Bob Harries - Make introduction")
- Notes: Include chat context
- Route using the Airtable task workflow below

---

## Airtable Task Routing

## Workflow

### Step 1: Identify Candidate Bases
Read the entire task (title, description, comments, etc) and determine which base(s) might be relevant:
- **Personal**: Family (Maria, Victoria, Miranda), health, home, hobbies, personal development
- **AI Trailblazers**: Meetups, workshops, community, apprenticeships, nonprofit, education, 501c3
- **Brain Bridge**: Clients, consulting, AI Teammates, business services, partnerships, B2B

### Step 2: Explore Goals
For each candidate base, query goals to understand current priorities:

**Goal hierarchy (AITB & Brain Bridge):**
- **Objectives (1y)**, Annual strategic objectives
- **Mountains (30d)**, Monthly focus areas, linked up to Objectives
- **Rocks (7d)**, Weekly deliverables, linked up to Mountains

**Goal hierarchy (Personal):**
- **1yr Goals**, Annual goals (no monthly/weekly tables yet)

Use the `scripts/query_goals.py` helper to fetch goals by base and type.

### Step 3: Explore Existing Projects
Query existing projects in each candidate base to find alignment:

**What to look for:**
- Project names that semantically match the task
- Projects linked to relevant goals
- Recent project activity that might relate

Use the `scripts/query_projects.py` helper to fetch projects.

### Step 4: Determine Best Fit
Score potential matches:
- **Strong match**: Task description directly aligns with project name/purpose AND connects to an active goal
- **Possible match**: Partial alignment, may need clarification
- **No match**: No existing project fits, flag for new project creation

### Step 5: Return Routing Decision AND ASSIGN TASK

**If match found:**
```
Base: [Personal | AI Trailblazers | Brain Bridge]
Project: [Project Name]
Project ID: [recXXXXXX]
Confidence: [High | Medium]
Reasoning: [Brief explanation of the match]
ACTION REQUIRED: Update task's Project field to the Project ID above
```

**CRITICAL:** Do NOT just add routing notes to the task. You MUST update the actual Project field on the task record using `update_task.py --project [ID]`.

**If no match, auto-create project:**

When no existing project matches AND the base is clear, create a new project using `create_project_rock.py` following the [creating-projects.md](creating-projects.md) quality standard.

1. Identify the best base from Step 1
2. Find the most relevant goal from Step 2 (for `--goal`)
3. Determine the driver (default: the task's assignee or Aaron)
4. Create the project:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_project_rock.py \
  --base <personal|aitb|bb> \
  --name "Specific, outcome-oriented project name" \
  --description "Done when [observable, verifiable outcome]" \
  --driver <pablo|aaron|juan> \
  --goal <goalRecordId> \
  --notes "Created during task routing. Source task: [task description]"
```

5. Use the returned record ID to link the original task to the new project
6. Aaron will see new projects in his next inbox review

**If no match AND base is unclear:**
```
Base: Unclear, need input
Recommendation: Create new project
Suggested project name: [Your suggestion]
Candidate bases: [list with reasoning]
Next step: Confirm base with Aaron, then create project
```

## Helper Scripts

Requires `AIRTABLE_TOKEN` environment variable to be set.

### scripts/query_goals.py
Fetch goals from a specific base and level.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_goals.py --base [personal|aitb|bb] --type [annual|monthly|weekly]
```

**Table mapping:**
| Base | `--type annual` | `--type monthly` | `--type weekly` |
|------|----------------|-----------------|----------------|
| personal | 1yr Goals | *(not available)* | *(not available)* |
| aitb | Objectives (1y) | Mountains (30d) | Rocks (7d) |
| bb | Objectives (1y) | Mountains (30d) | Rocks (7d) |

**Output:** JSON array of goals with name, status, description, priority, and linked records (up/down hierarchy).

### scripts/query_projects.py
Fetch projects from a specific base.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_projects.py --base [personal|aitb|bb] [--active-only]
```

**Output:** JSON array of projects with name, status, description, and linked goals (where available).

**Note:** `--active-only` excludes completed/archived projects. The completion status names differ per base (Personal: "Complete", AITB: "Complete"/"Archived", BB: "Done").

## Learned Mappings

Always check `~/.openclaw/skills/managing-projects/references/learned_mappings.json` for rules that override exploration.

### Task Rules (`always_rules`)
```json
{
  "always_rules": [
    {
      "pattern": "regex pattern to match task title",
      "base": "personal|aitb|bb",
      "project": "Exact Project Name from Airtable",
      "auto_action": "optional: Execute immediately using executing-tasks skill"
    }
  ]
}
```

### Beeper Rules (`beeper_rules`)
```json
{
  "beeper_rules": [
    {
      "chat_pattern": "regex or exact chat name",
      "action": "mark_read",
      "unless_mentioned": "Aaron",
      "note": "Why this rule exists"
    }
  ]
}
```

**Actions:**
- `mark_read`: Auto-mark as read unless `unless_mentioned` name appears in message

### Email Rules (`email_rules`)
```json
{
  "email_rules": [
    {
      "from_pattern": "regex to match sender email",
      "from_name_pattern": "optional regex to match sender display name",
      "account": "personal|bb|aitb",
      "add_labels": ["label1", "label2"],
      "remove_labels": ["INBOX"],
      "note": "Why this rule exists"
    }
  ]
}
```

### Routing History (`routed_history`)
Recent routing decisions for reference. Helps identify patterns for new ALWAYS rules.

**When to add rules:** Only after multiple consistent routings where exploration would be unnecessary. Aaron approves all ALWAYS rules.

## Base Configuration

**Personal Base**
- ID: `appvh0RXcE3IPCy6X`
- Tables: Tasks (`tblxAXXXCOc18a31C`), Projects, 1yr Goals, 5yr Goals, 10yr Goals, People
- Project name field: `Project`
- Project status values: Not Started, In Progress, Complete, Blocked

**AI Trailblazers Base**
- ID: `appweWEnmxwWfwHDa`
- Tables: Tasks (`tbl5k5KqzkrKIewvq`), Projects, Objectives (1y), Mountains (30d), Rocks (7d), Meetups, Classes, Apprentices, Deals, Contacts, Organizations
- Project name field: `Project Name`
- Project status values: Not Started, In Progress, Blocked, Complete, Archived

**Brain Bridge Base**
- ID: `appwzoLR6BDTeSfyS`
- Tables: Tasks (`tblmQBAxcDPjajPiE`), Projects, Objectives (1y), Mountains (30d), Rocks (7d), Organizations, Contacts, Deals, Employees, Leads, Campaigns
- Project name field: `Name`
- Project status values: Pending, In progress, Done

## Integration with Task Creation

This skill returns routing decisions only. To actually create the task:

1. Get routing decision from this skill
2. Call executing-tasks, see [executing-tasks.md](executing-tasks.md)

## Example Usage

**User:** "Where should I put 'Follow up on the F|Staff onboarding checklist'?"

**Process:**
1. Check learned_mappings.json → No ALWAYS rule match
2. "F|Staff" is a clear client reference → Brain Bridge base
3. Query BB projects: Find "F|Staff M-Size Project" (Status: In progress)
4. Return: Brain Bridge → F|Staff M-Size Project (Confidence: High)

---

**User:** "Where should I put 'Prepare slides for AI Hackathon'?"

**Process:**
1. No ALWAYS rule match
2. "AI Hackathon" → likely AI Trailblazers
3. Query AITB projects: Find "AI Hackathon 2/15/26" (Status: In Progress)
4. Return: AI Trailblazers → AI Hackathon 2/15/26 (Confidence: High)

---

**User:** "Where should I put 'Research new meditation app'?"

**Process:**
1. No ALWAYS rule match
2. Check all bases, could fit Personal (wellness) or AITB (community program)
3. Query goals: Personal has "Build Habit: Consistent Gratitude" 1yr goal (On Track)
4. Query Personal projects: Find "Build a plan for daily gratitude habits" (In Progress)
5. Return: Personal → Build a plan for daily gratitude habits (Confidence: Medium, confirm if this is the right fit or needs a new project)
