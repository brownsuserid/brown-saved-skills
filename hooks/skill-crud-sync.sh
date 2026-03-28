#!/usr/bin/env bash
# skill-crud-sync.sh
# PostToolUse hook: triggers push to brown-saved-skills when a skill file is modified.

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

# Check if the file is under ~/.claude/skills/
if echo "$FILE_PATH" | grep -qi "\.claude/skills\|\.claude\\\\skills"; then
    SCRIPT_DIR="$(dirname "$0")"
    "$SCRIPT_DIR/sync-skills-bidirectional.sh" push &>/dev/null &
fi

exit 0
