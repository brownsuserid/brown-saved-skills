---
name: skill-router
description: "Skill routing and matching layer that activates on EVERY user request. Analyzes the user's intent against all installed skills to find applicable skills or reusable skill components. ALWAYS trigger this skill — it runs on every single user message regardless of topic. This includes coding tasks, email tasks, infrastructure tasks, document tasks, planning tasks, CRM tasks, meeting tasks, and anything else. If you're about to respond to a user without checking this skill first, stop and check it. The only exception is if the user is asking a simple clarifying question in an ongoing conversation where the skill was already routed."
---

# Skill Router

You are a skill routing layer. Your job is to match every incoming user request against the installed skill library and surface the best skill (or skill components) for the task — or stay silent if nothing applies.

## How It Works

When a user sends a request, do the following before taking any other action:

### Step 1: Parse Intent

Read the user's message and identify:
- **Primary action**: What are they trying to do? (build, fix, deploy, email, plan, create a doc, etc.)
- **Domain**: What area does this touch? (code, infrastructure, email, CRM, documents, presentations, meetings, sales, etc.)
- **Artifacts**: Are specific file types, services, or tools mentioned? (.docx, .pdf, .xlsx, .pptx, Lambda, CDK, Gmail, Airtable, Google Calendar, etc.)
- **Workflow stage**: Are they planning, implementing, testing, reviewing, deploying, or triaging?

### Step 2: Match Against Skills

Scan the available skills list (provided in your system context) and look for:

1. **Direct match**: A skill whose description clearly covers this exact task. Examples:
   - User says "fix this bug" → `dev-fixing-bugs`
   - User says "triage my email" → `email-morning-triage`
   - User says "create a .docx report" → `anthropic-skills:docx`
   - User says "deploy this CDK stack" → `infra-cdk-quality`

2. **Partial match**: No single skill covers the whole task, but parts of one or more skills contain useful workflows, templates, or patterns. Examples:
   - User wants to "build a new feature and write tests" → `dev-implementing-features` for the build, `dev-writing-unit-tests` for the tests
   - User wants to "prepare for tomorrow's meeting with a client" → `preparing-for-meetings` for meeting prep, `looking-up-contacts` or `looking-up-deals` for CRM context

3. **No match**: The request is straightforward enough that no skill adds value, or it falls outside all skill domains.

### Step 3: Act on the Match

**If there is a direct match (one skill covers the task):**
- Invoke that skill immediately using the Skill tool
- Do not ask the user "should I use this skill?" — just use it

**If there is a partial match (multiple skills or components apply):**
- Briefly tell the user which skills you're pulling from and why (one sentence max)
- Invoke the most relevant skill, and reference techniques from secondary skills as needed during execution

**If there is no match:**
- Say nothing about skills. Do not mention that you checked. Do not say "no skill applies." Just proceed to handle the request directly as you normally would. The user should never know this routing layer ran unless it found something useful.

## Important Principles

**Be invisible when unnecessary.** The whole point of this skill is to make the skill library more useful — not to add friction. If nothing matches, the user should have zero awareness that routing happened.

**Prefer action over suggestion.** If you find a matching skill, invoke it. Don't ask permission or list options unless there's genuine ambiguity (e.g., the request could plausibly go to two very different skills and you're not sure which the user wants).

**Think about components, not just whole skills.** A skill might have a useful subprocess even if the overall skill doesn't match. For instance, `email-reply-assistant` has a workflow for gathering CRM context that could be useful even if the user isn't replying to an email — they might just want to look someone up before a call.

**Don't over-route.** Simple questions ("what does this function do?", "explain this error") rarely need a skill. Coding tasks that are a few lines of change don't need `dev-implementing-features`. Use judgment — skills are for workflows that benefit from structure, not for trivial tasks.

**Skill names to know about:**
- Dev workflow: `dev-planning-features`, `dev-implementing-features`, `dev-fixing-bugs`, `dev-refactoring`, `dev-reviewing-code`, `dev-writing-unit-tests`, `dev-writing-integration-tests`, `dev-quality-checks`, `dev-changelog-generator`, `dev-documenting`
- Infrastructure: `infra-cdk-quality`, `infra-cloudwatch-investigation`, `infra-auditing-aws-spending`, `infra-detecting-loops`, `infra-oauth-lambda`
- Email & comms: `email-morning-triage`, `email-reply-assistant`, `sending-meeting-confirmations`, `sending-meeting-invitations`
- Documents & media: `anthropic-skills:docx`, `anthropic-skills:pdf`, `anthropic-skills:pptx`, `anthropic-skills:xlsx`, `using-gamma`, `using-notebooklm`
- CRM & sales: `looking-up-contacts`, `looking-up-deals`, `updating-contacts`, `updating-deals`, `updating-orgs`, `managing-sales-followups`, `sales-deal-review`, `search-airtable`
- Google Workspace: `using-gog`
- Meetings: `preparing-for-meetings`, `coordinating-meeting-times`, `calendar-availability`, `searching-meeting-transcripts`
- Project management: `creating-tasks`, `executing-tasks`, `routing-airtable-tasks`, `setting-todays-priorities`, `monthly-planning`, `annual-planning`
- Meta/tooling: `skill-creator`, `creating-skills`, `skill-overlap-checker`, `syncing-saved-skills`, `update-config`, `launching-tasks`
- Git workflow: `commit`, `commit-only`, `commit-push-pr`, `quality-check`, `test`
- Troubleshooting: `troubleshoot-01` (root cause), `troubleshoot-02` (resolution)
