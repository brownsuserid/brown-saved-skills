#!/bin/zsh
# work-task: Open Warp + Claude Code to work on an Airtable task by title
# Usage: work-task "Claude plugin marketplace"
# Also handles pablo:// URL scheme calls

TASK_TITLE="$1"

# If called via URL scheme, parse it: pablo://task/Some+Task+Title
if [[ "$TASK_TITLE" == pablo://* ]]; then
  TASK_TITLE="${TASK_TITLE#pablo://task/}"
  TASK_TITLE=$(python3 -c "import urllib.parse,sys; print(urllib.parse.unquote_plus(sys.argv[1]))" "$TASK_TITLE")
fi

if [ -z "$TASK_TITLE" ]; then
  echo "Usage: work-task <task title>"
  exit 1
fi

# Escape single quotes in task title for safe YAML embedding
ESCAPED_TITLE="${TASK_TITLE//\'/\'\\\'\'}"

# Write a temporary launch config with the task baked in
CONFIG_FILE="$HOME/.warp/launch_configurations/_work-task-temp.yaml"
cat > "$CONFIG_FILE" <<YAMLEOF
---
name: Execute Task
windows:
  - tabs:
      - title: ${TASK_TITLE}
        layout:
          cwd: $HOME/.openclaw
          commands:
            - exec: >-
                cc
                "Search for the task '${ESCAPED_TITLE}' using
                python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/search_tasks.py
                --base all --query '${ESCAPED_TITLE}' --max 1.
                Then follow the full 7-phase task execution workflow in
                ~/.openclaw/skills/managing-projects/references/executing-tasks.md.
                Start at Phase 1 (understand context), write a plan in Phase 3,
                present the plan and wait for my approval before executing."
YAMLEOF

open "warp://launch/Execute%20Task"
