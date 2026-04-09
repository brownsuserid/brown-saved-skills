#!/usr/bin/env bash
# skill-crud-sync.sh
# PostToolUse hook: triggers push to brown-saved-skills when any Claude config file
# is created, updated, or deleted (skills, commands, hooks, plans, tasks, todos,
# settings, or project memory).

INPUT=$(cat)

# Find jq
JQ="jq"
if ! command -v jq &>/dev/null; then
    if [ -f "$HOME/bin/jq.exe" ]; then
        JQ="$HOME/bin/jq.exe"
    else
        exit 0
    fi
fi

# Extract file_path from the tool input
FILE_PATH=$(echo "$INPUT" | "$JQ" -r '.tool_input.file_path // .tool_input.command // empty' 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Normalize path separators for Windows
FILE_PATH=$(echo "$FILE_PATH" | sed 's|\\|/|g')

# Check if the file is under any synced ~/.claude/ directory or is a synced config file
if echo "$FILE_PATH" | grep -qiE '\.claude/(skills|commands|hooks|plans|tasks|todos|projects)/|\.claude/settings(\.local)?\.json'; then
    SCRIPT_DIR="$(dirname "$0")"
    "$SCRIPT_DIR/sync-skills-bidirectional.sh" push &>/dev/null &
fi

exit 0
