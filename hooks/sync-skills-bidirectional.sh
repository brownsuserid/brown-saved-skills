#!/usr/bin/env bash
# sync-skills-bidirectional.sh
# Bidirectional sync between ~/.claude/ and brown-saved-skills repo.
# Usage:
#   sync-skills-bidirectional.sh push   - local -> repo (commit & push)
#   sync-skills-bidirectional.sh pull   - repo -> local (skills only, not settings)
#   sync-skills-bidirectional.sh both   - pull then push (full sync)

set -euo pipefail

ACTION="${1:-both}"
CLAUDE_DIR="$HOME/.claude"
REPO_DIR="$HOME/brown-saved-skills"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Directories synced in BOTH directions
PULL_DIRS=(skills commands scheduled-tasks plans tasks todos)
# Directories only pushed (local -> repo), never pulled (machine-specific content)
PUSH_ONLY_DIRS=(hooks)
# Files only pushed, never pulled (contain machine-specific paths)
PUSH_ONLY_FILES=(settings.json settings.local.json)

log() { echo "[skill-sync] $*"; }

ensure_repo() {
    if [ ! -d "$REPO_DIR/.git" ]; then
        log "Cloning brown-saved-skills..."
        git clone "https://github.com/brownsuserid/brown-saved-skills.git" "$REPO_DIR" 2>/dev/null
    fi
}

pull_from_repo() {
    log "Pulling latest from brown-saved-skills..."
    cd "$REPO_DIR"
    git fetch origin 2>/dev/null
    git reset --hard origin/main 2>/dev/null || true

    # Only pull safe directories (not hooks or settings - those are machine-specific)
    for dir in "${PULL_DIRS[@]}"; do
        src="$REPO_DIR/$dir"
        dest="$CLAUDE_DIR/$dir"
        if [ -d "$src" ]; then
            rm -rf "$dest"
            cp -r "$src" "$dest"
            log "Pulled $dir/"
        fi
    done

    # Sync project memory directories: repo -> local
    if [ -d "$REPO_DIR/projects" ]; then
        find "$REPO_DIR/projects" -type d -name "memory" 2>/dev/null | while read memdir; do
            relpath="${memdir#$REPO_DIR/}"
            dest_parent="$CLAUDE_DIR/$(dirname "$relpath")"
            mkdir -p "$dest_parent"
            rm -rf "$dest_parent/memory"
            cp -r "$memdir" "$dest_parent/"
            log "Pulled $relpath/"
        done
    fi

    log "Pull complete."
}

push_to_repo() {
    log "Pushing local changes to brown-saved-skills..."
    cd "$REPO_DIR"
    git fetch origin 2>/dev/null
    git reset --hard origin/main 2>/dev/null || true

    # Sync pull dirs: local -> repo
    for dir in "${PULL_DIRS[@]}"; do
        src="$CLAUDE_DIR/$dir"
        dest="$REPO_DIR/$dir"
        if [ -d "$src" ]; then
            rm -rf "$dest"
            cp -r "$src" "$dest"
        fi
    done

    # Sync push-only dirs: local -> repo
    for dir in "${PUSH_ONLY_DIRS[@]}"; do
        src="$CLAUDE_DIR/$dir"
        dest="$REPO_DIR/$dir"
        if [ -d "$src" ]; then
            rm -rf "$dest"
            cp -r "$src" "$dest"
        fi
    done

    # Sync push-only files: local -> repo
    for file in "${PUSH_ONLY_FILES[@]}"; do
        src="$CLAUDE_DIR/$file"
        if [ -f "$src" ]; then
            cp "$src" "$REPO_DIR/$file"
        fi
    done

    # Sync project memory directories: local -> repo
    find "$CLAUDE_DIR/projects" -type d -name "memory" 2>/dev/null | while read memdir; do
        relpath="${memdir#$CLAUDE_DIR/}"
        dest_parent="$REPO_DIR/$(dirname "$relpath")"
        mkdir -p "$dest_parent"
        rm -rf "$dest_parent/memory"
        cp -r "$memdir" "$dest_parent/"
    done

    # Clean up artifacts
    find "$REPO_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$REPO_DIR" -type d -name ".wrangler" -exec rm -rf {} + 2>/dev/null || true
    find "$REPO_DIR" -name "*.pyc" -delete 2>/dev/null || true

    cd "$REPO_DIR"
    git add -A

    if git diff --cached --quiet; then
        log "No changes to push."
        return 0
    fi

    git diff --cached --stat
    git commit -m "Auto-sync: $TIMESTAMP

Automated sync of Claude Code configuration from local device.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"

    git push origin main 2>&1
    log "Push complete."
}

ensure_repo

case "$ACTION" in
    pull)  pull_from_repo ;;
    push)  push_to_repo ;;
    both)  pull_from_repo; push_to_repo ;;
    *)     log "Unknown action: $ACTION (use pull, push, or both)"; exit 1 ;;
esac
