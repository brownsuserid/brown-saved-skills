#!/usr/bin/env bash
# session-start-sync.sh
# Runs on Claude session start: pulls latest skills from brown-saved-skills repo.
# Runs in background to avoid blocking session startup.

SCRIPT_DIR="$(dirname "$0")"
"$SCRIPT_DIR/sync-skills-bidirectional.sh" pull &>/dev/null &
exit 0
