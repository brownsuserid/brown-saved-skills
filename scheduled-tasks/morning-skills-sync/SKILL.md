---
name: morning-skills-sync
description: Syncs local Claude Code config (skills, commands, memory, settings) to the brown-saved-skills GitHub repo at 4 AM daily.
---

Run the sync script to push local Claude Code configuration changes to the brown-saved-skills GitHub repo.

Execute this command:
```bash
bash ~/.claude/skills/syncing-saved-skills/scripts/sync-to-repo.sh
```

Report whether changes were found and pushed, or if everything was already up to date.