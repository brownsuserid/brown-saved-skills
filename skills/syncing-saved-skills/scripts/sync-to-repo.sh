#!/usr/bin/env bash
# sync-to-repo.sh
# Syncs local ~/.claude/ tracked files to the brown-saved-skills git repo.
# Commits and pushes any changes found.

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
REPO_URL="https://github.com/brownsuserid/brown-saved-skills.git"
REPO_DIR="/tmp/brown-saved-skills"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Tracked directories (relative to ~/.claude/)
TRACKED_DIRS=(
    "skills"
    "commands"
    "scheduled-tasks"
    "hooks"
    "plans"
    "tasks"
    "todos"
)

# Tracked files (relative to ~/.claude/)
TRACKED_FILES=(
    "settings.json"
    "settings.local.json"
)

echo "=== Claude Config Sync: $TIMESTAMP ==="

# Clone or update the repo
if [ -d "$REPO_DIR/.git" ]; then
    echo "Repo exists, pulling latest..."
    cd "$REPO_DIR"
    git fetch origin 2>/dev/null
    git reset --hard origin/main 2>/dev/null || true
else
    echo "Cloning repo..."
    git clone "$REPO_URL" "$REPO_DIR" 2>/dev/null
    cd "$REPO_DIR"
fi

# Sync tracked directories
for dir in "${TRACKED_DIRS[@]}"; do
    src="$CLAUDE_DIR/$dir"
    dest="$REPO_DIR/$dir"
    if [ -d "$src" ]; then
        # Remove old version, copy fresh (handles deletions)
        rm -rf "$dest"
        cp -r "$src" "$dest"
        echo "Synced $dir/"
    fi
done

# Sync tracked files
for file in "${TRACKED_FILES[@]}"; do
    src="$CLAUDE_DIR/$file"
    if [ -f "$src" ]; then
        cp "$src" "$REPO_DIR/$file"
        echo "Synced $file"
    fi
done

# Sync project memory directories
find "$CLAUDE_DIR/projects" -type d -name "memory" 2>/dev/null | while read memdir; do
    relpath="${memdir#$CLAUDE_DIR/}"
    dest_parent="$REPO_DIR/$(dirname "$relpath")"
    mkdir -p "$dest_parent"
    rm -rf "$dest_parent/memory"
    cp -r "$memdir" "$dest_parent/"
    echo "Synced $relpath/"
done

# Clean up files that should be gitignored
find "$REPO_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$REPO_DIR" -type d -name ".wrangler" -exec rm -rf {} + 2>/dev/null || true
find "$REPO_DIR" -name "*.pyc" -delete 2>/dev/null || true

# Check for changes
cd "$REPO_DIR"
git add -A

if git diff --cached --quiet; then
    echo "No changes detected. Repo is up to date."
    exit 0
fi

# Show what changed
echo ""
echo "=== Changes detected ==="
git diff --cached --stat

# Commit and push
git commit -m "Auto-sync: $TIMESTAMP

Automated sync of Claude Code configuration from local device.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"

git push origin main 2>&1

echo ""
echo "=== Sync complete: pushed to GitHub ==="
