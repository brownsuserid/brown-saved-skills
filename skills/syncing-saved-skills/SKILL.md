---
name: syncing-saved-skills
description: Syncs local Claude Code configuration (skills, commands, memory, settings, scheduled tasks, hooks) to the brown-saved-skills GitHub repo. Run manually or via scheduled task at 4am and 10pm daily.
---

# Syncing Saved Skills to GitHub

This skill syncs your local `~/.claude/` configuration to the central GitHub repo at `https://github.com/brownsuserid/brown-saved-skills.git`.

## What Gets Synced

- **skills/** - All skill folders and their contents
- **commands/** - Slash command definitions
- **scheduled-tasks/** - Scheduled task definitions
- **hooks/** - Git/automation hooks
- **plans/** - Active plans
- **tasks/** - Task data
- **todos/** - Todo lists
- **settings.json** and **settings.local.json** - Claude Code settings
- **projects/*/memory/** - Project memory files

## What Does NOT Get Synced

- `.credentials.json` (secrets)
- `cache/`, `sessions/`, `debug/`, `file-history/`, `shell-snapshots/`, `downloads/` (ephemeral)
- `stats-cache.json`, `history.jsonl` (machine-specific)
- Session logs and tool results inside `projects/`

## How to Run

### Manual
```bash
bash ~/.claude/skills/syncing-saved-skills/scripts/sync-to-repo.sh
```

### Automated
Two scheduled tasks run this automatically:
- **morning-skills-sync** - 4:00 AM daily
- **evening-skills-sync** - 10:00 PM daily

## Setting Up a New Device

To pull the latest config onto a new machine:
```bash
git clone https://github.com/brownsuserid/brown-saved-skills.git /tmp/brown-saved-skills
cp -r /tmp/brown-saved-skills/skills/ ~/.claude/skills/
cp -r /tmp/brown-saved-skills/commands/ ~/.claude/commands/
cp -r /tmp/brown-saved-skills/scheduled-tasks/ ~/.claude/scheduled-tasks/
cp -r /tmp/brown-saved-skills/hooks/ ~/.claude/hooks/
cp /tmp/brown-saved-skills/settings.json ~/.claude/settings.json
cp /tmp/brown-saved-skills/settings.local.json ~/.claude/settings.local.json
# Copy memory files as needed from projects/
```
