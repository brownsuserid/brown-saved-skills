# The Library

Private skill distribution for Brain Bridge AI and affiliated organizations. Manages skills, agents, and prompts across repos, devices, and teams using a single YAML catalog.

## Overview

The Library is a Claude Code meta-skill (`/library`) that catalogs and distributes our agentic capabilities. The catalog (`library.yaml`) stores references to skills across multiple GitHub repos. Nothing is copied until you ask for it — pull on demand with `/library use <name>`.

**What's in the catalog:**
- **100+ skills** across 5 source repos
- **19 command prompts** for development workflows
- Typed dependencies so skills can declare what they need

## Source Repositories

| Repo | Org | What's In It |
|------|-----|-------------|
| [core-library](https://github.com/Brain-Bridge-AI/core-library) | Brain-Bridge-AI | Reusable engines — Airtable config, calendar, gog, gamma, beeper, contacts/deals CRUD, task management, meeting prep, scoring, outreach |
| [bb-library](https://github.com/Brain-Bridge-AI/bb-library) | Brain-Bridge-AI | BB-specific — case studies, email approaches, pitch decks, speaking opps, campaign creation, outreach planning, BB routers |
| [ai-sdlc](https://github.com/Brain-Bridge-AI/ai-sdlc) | Brain-Bridge-AI | Developer skills — bug fixing, feature planning, code review, testing, refactoring, MCP builders, changelogs, documentation |
| [aitb-library](https://github.com/ai-trailblazers/aitb-library) | ai-trailblazers | AITB operations — calendar, gog, events, Groups.io, AITB routers |
| [personal-library](https://github.com/aaroneden/personal-library) | aaroneden | Aaron's personal workflows — gratitude reminders, social media, family planning, voice memos, weekly digests |

## Setup (New Team Member)

### Prerequisites

- **Claude Code** installed and working
- **git** with SSH keys or `GITHUB_TOKEN` configured for Brain-Bridge-AI repos
- **GitHub CLI** (`gh`) — `brew install gh`, then `gh auth login`

### Step 1: Clone the Library

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Brain-Bridge-AI/the-library.git ~/.claude/skills/library
```

This installs `/library` as a global slash command available in every Claude Code session.

### Step 2: Verify

Open a new Claude Code session (any directory) and run:

```
/library list
```

You should see the full catalog with install status indicators.

### Step 3: Install Skills You Need

Pull individual skills into your current project:

```
/library use airtable-config
/library use using-gog
/library use dev-fixing-bugs
```

Or install globally (available in all projects on this machine):

```
/library use airtable-config install globally
```

### Step 4: Install Dev Commands

Dev commands (commit, test, quality-check, etc.) install as slash commands:

```
/library use commit
/library use test
/library use fix-bug
```

These go to `.claude/commands/` and become available as `/commit`, `/test`, `/fix-bug`.

## Commands

| Command | What It Does |
|---------|-------------|
| `/library list` | Show catalog with install status |
| `/library search <keyword>` | Find skills by name or description |
| `/library use <name>` | Pull a skill from its source repo |
| `/library use <name> install globally` | Pull to `~/.claude/skills/` instead of project-local |
| `/library push <name>` | Push local changes back to the source repo |
| `/library add <details>` | Register a new skill in the catalog |
| `/library remove <name>` | Remove from catalog and optionally delete local copy |
| `/library sync` | Re-pull all installed items from their sources |

### Justfile Shortcuts

Run library commands from your terminal without an interactive Claude session:

```bash
just list                  # Show catalog
just use my-skill          # Pull a skill
just push my-skill         # Push changes back
just search "keyword"      # Search catalog
just sync                  # Refresh all installed items
```

> Requires `just` (`brew install just`). Recipes use `--dangerously-skip-permissions` for filesystem/git access.

## Catalog Structure

The catalog lives in `library.yaml` with this structure:

```yaml
default_dirs:
  skills:
    - default: .claude/skills/    # project-local install
    - global: ~/.claude/skills/   # machine-wide install
  agents:
    - default: .claude/agents/
    - global: ~/.claude/agents/
  prompts:
    - default: .claude/commands/
    - global: ~/.claude/commands/

library:
  skills:
    - name: skill-name
      description: What this skill does
      source: https://github.com/Brain-Bridge-AI/core-library/blob/main/skills/skill-name/SKILL.md
      requires: [skill:airtable-config]  # optional typed dependencies
  prompts:
    - name: command-name
      description: What this command does
      source: https://github.com/Brain-Bridge-AI/ai-sdlc/blob/main/commands/command-name.md
```

### Source Formats

| Format | Example |
|--------|---------|
| Local path | `/Users/me/projects/tools/skills/my-skill/SKILL.md` |
| GitHub browser URL | `https://github.com/org/repo/blob/main/skills/name/SKILL.md` |
| GitHub raw URL | `https://raw.githubusercontent.com/org/repo/main/skills/name/SKILL.md` |

The source points to a file. The system pulls the **entire parent directory** (skills include scripts, references, configs — not just the markdown).

### Dependencies

Skills can declare typed dependencies:

```yaml
requires: [skill:airtable-config, skill:using-gog]
```

When you `/library use` a skill, its dependencies are resolved and pulled first.

## Common Workflows

### Adding a New Skill to the Catalog

After creating a skill in one of the source repos:

```
/library add my-new-skill skill from https://github.com/Brain-Bridge-AI/core-library/blob/main/skills/my-new-skill/SKILL.md
```

This updates `library.yaml` and pushes the change so other team members can see it.

### Updating a Skill

Edit the skill locally, then push changes back to its source repo:

```
/library push my-skill
```

Other team members pick up changes on their next `/library sync` or `/library use my-skill`.

### Setting Up a New Project

Pull the skills you need for a specific project:

```
/library use airtable-config
/library use executing-tasks
/library use routing-airtable-tasks
/library use airtable-inbox-review
```

### Bootstrapping a New Machine

After cloning the library (Step 1), pull everything you need:

```
/library sync
```

This re-pulls all previously installed items from their sources.

## Architecture

```
~/.claude/skills/library/          # The Library (globally installed)
├── SKILL.md                       # Agent instructions
├── library.yaml                   # Catalog of all available skills
├── cookbook/                       # Step-by-step guides per command
│   ├── install.md
│   ├── add.md
│   ├── use.md
│   ├── push.md
│   ├── remove.md
│   ├── list.md
│   ├── sync.md
│   └── search.md
├── justfile                       # Terminal shortcuts
└── README.md                      # This file
```

## Key Concepts

- **Catalog, not manifest** — entries define what's *available*, not what's installed. Pull on demand.
- **Reference-based** — the catalog stores pointers, not copies. Skills live in their source repos.
- **Pure agent application** — no scripts, no CLIs, no build tools. The SKILL.md teaches the agent what to do.
- **Private-first** — built for private GitHub repos. Auth uses SSH keys or `GITHUB_TOKEN`.

## Skill Categories

### Core (Brain-Bridge-AI/core-library)

**Adapters & Engines:**
airtable-config, calendar-availability, using-gog, using-gamma, using-notebooklm, using-beeper, search-airtable

**Task & Project Management:**
executing-tasks, routing-airtable-tasks, airtable-inbox-review, creating-tasks, creating-projects, setting-todays-priorities, setting-up-weekly-rocks, monthly-planning, annual-planning, regenerating-recurring-tasks, auditing-task-quality

**Contacts, Deals & CRM:**
looking-up-contacts, looking-up-deals, updating-contacts, updating-deals, updating-orgs, sales-deal-review, managing-sales-followups, cleanup-duplicate-deals

**Communication & Content:**
coordinating-meeting-times, sending-meeting-invitations, preparing-for-meetings, searching-meeting-transcripts, reviewing-meeting-quality, scoring-content, ingesting-gmail-digests, managing-outreach, drafting-blog-posts, drafting-pr-faqs, generating-podcast, email-style-guide

**Monitoring:**
monitoring-job-listings, tracking-website-analytics, check-ai-usage, scraping-linkedin-metrics

**Meta:**
creating-skills, generating-morning-briefing, logging-completed-tasks

### BB (Brain-Bridge-AI/bb-library)

bb-case-studies, bb-email-approaches, creating-campaigns, planning-outreach, generating-pitch-decks, researching-speaking-opportunities, looking-up-organizations-bb, maintaining-relationships-bb, managing-finances-bb, managing-projects-bb

### AI SDLC (Brain-Bridge-AI/ai-sdlc)

dev-fixing-bugs, dev-implementing-features, dev-planning-features, dev-refactoring, dev-reviewing-code, dev-writing-unit-tests, dev-writing-integration-tests, dev-quality-checks, dev-documenting, dev-changelog-generator, dev-mcp-builder, dev-notebooklm, dev-shared-references

### Dev Commands (prompts)

commit, commit-only, commit_push_pr, quality-check, fix-bug, plan-feature, test, new-project, prime, question, worktree, squashed, audit-aws-security, roadmap-plan-01, roadmap-plan-02-architect, roadmap-plan-03-tests, roadmap-execute, troubleshoot-01, troubleshoot-02

### AITB (ai-trailblazers/aitb-library)

finding-calendar-availability-aitb, using-gog-aitb, looking-up-organizations-aitb, planning-aitb-events, aitb-groupsio, maintaining-relationships-aitb, managing-finances-aitb, managing-projects-aitb, applying-for-grants

### Personal (aaroneden/personal-library)

finding-calendar-availability, using-gog-personal, looking-up-organizations, writing-code, wishing-happy-birthdays, managing-interest-profile, ingesting-youtube, generating-weekly-digest, flagging-social-queue, pablo-task-execution, monthly-review, creating-gratitude-reminders, linkedin-connection-manager, planning-family-time, syncing-facebook-birthdays, routing-voice-memos, checking-social-media, archiving-apple-notes, running-weekly-retros, delegating-todays-work, analyzing-shadowtrader-reports, logging-completed-tasks, maintaining-relationships, managing-finances, managing-projects

## Credits

Based on [The Library](https://github.com/disler/the-library) by IndyDevDan. Forked and customized for Brain Bridge AI.
