---
name: syncing-saved-skills
description: Syncs local Claude Code configuration (skills, commands, memory, settings, scheduled tasks, hooks) to the brown-saved-skills GitHub repo. Runs automatically on session start (pull), on skill CRUD (push), and via scheduled tasks.
---

# Syncing Saved Skills to GitHub

Bidirectional sync between `~/.claude/` and `https://github.com/brownsuserid/brown-saved-skills.git`.

## Sync Behavior

### Pull (repo -> local): skills, commands, scheduled-tasks, plans, tasks, todos, project memory
### Push (local -> repo): all of the above PLUS hooks, settings.json, settings.local.json

Settings and hooks are **push-only** because they contain machine-specific paths.

## What Does NOT Get Synced

- `.credentials.json`, `cache/`, `sessions/`, `debug/`, `file-history/`, `shell-snapshots/`, `downloads/`, `stats-cache.json`, `history.jsonl`

## How to Run

### Manual
```bash
bash ~/.claude/hooks/sync-skills-bidirectional.sh pull   # repo -> local
bash ~/.claude/hooks/sync-skills-bidirectional.sh push   # local -> repo
bash ~/.claude/hooks/sync-skills-bidirectional.sh both   # pull then push
```

### Automated Triggers
- **Session start** - `SessionStart` hook runs `pull` in background
- **Skill CRUD** - `PostToolUse` hook on Edit/Write/MultiEdit detects changes to `~/.claude/skills/` and runs `push` in background
- **Scheduled** - morning (4 AM) and evening (10 PM) tasks run push

## Setting Up a New Device

```bash
git clone https://github.com/brownsuserid/brown-saved-skills.git ~/brown-saved-skills
bash ~/brown-saved-skills/hooks/sync-skills-bidirectional.sh pull
# Then manually review and adapt settings.json for local paths
```
