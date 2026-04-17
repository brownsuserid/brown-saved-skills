# Git Commit and Pull Request Workflow

Comprehensive guide for creating commits and pull requests.

## Overview

This document provides standard patterns for:
- Creating well-formatted commit messages
- Pushing changes to branches
- Creating pull requests with proper descriptions
- Following git best practices

**Related references:**
- For version bumping guidance, see [semantic-versioning.md](semantic-versioning.md)

---

## Commit Message Format

### Standard Format

```bash
git commit -m "$(cat <<'EOF'
type(scope): brief description

Detailed explanation of changes:
- What was changed
- Why it was changed
- Any important details

Additional context or notes if needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Aaron <aaron@brainbridge.app>
EOF
)"
```

### Commit Types

- **feat**: New feature or functionality (may bump MINOR version)
- **fix**: Bug fix (may bump PATCH version)
- **docs**: Documentation changes only
- **style**: Code formatting, whitespace (no functional changes)
- **refactor**: Code restructuring without behavior changes
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates
- **perf**: Performance improvements
- **feat!** or **fix!**: Breaking changes (bumps MAJOR version)

**Version bumping:** See [semantic-versioning.md](semantic-versioning.md) for guidance on when to increment MAJOR, MINOR, or PATCH versions.

### Commit Scope (Optional)

Add scope in parentheses to indicate what part of codebase changed:
- `feat(auth):` - Authentication feature
- `fix(api):` - API bug fix
- `docs(readme):` - README update
- `test(unit):` - Unit test changes
- `refactor(database):` - Database refactoring

### Commit Message Guidelines

**Title Line:**
- Max 72 characters
- Lowercase after the colon
- No period at the end
- Imperative mood ("add" not "added" or "adds")

**Body:**
- Wrap at 72 characters per line
- Explain WHAT and WHY, not HOW
- Use bullet points for multiple changes
- Reference issues/tickets if applicable

**Examples:**

```bash
# Good - Feature
feat(skills): add async testing guidance

Added comprehensive async testing best practices:
- When to use async vs sync tests
- AsyncMock patterns and examples
- Event loop management
- Performance optimization

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```bash
# Good - Bug Fix
fix(auth): resolve token expiration edge case

Fixed race condition where tokens could expire between validation
and usage. Added 30-second buffer to token expiration check.

Resolves #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```bash
# Good - Documentation
docs: update installation instructions

Updated README with:
- Python 3.11+ requirement
- New dependency installation steps
- Troubleshooting section for common setup issues

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Creating Commits

### Pre-Commit Checklist

Before committing, verify:
- [ ] All tests pass
- [ ] Code is formatted (ruff/black)
- [ ] Linting passes (ruff check)
- [ ] Type checking passes (mypy, if applicable)
- [ ] No unintended files staged
- [ ] Commit message is clear and descriptive

### Staging Changes

```bash
# Stage all changes
git add .

# Or stage specific files
git add file1.py file2.py

# Review what will be committed
git status
git diff --cached
```

### Creating the Commit

```bash
# Use heredoc for multi-line messages
git commit -m "$(cat <<'EOF'
feat(feature): brief description

Detailed explanation here.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Verifying the Commit

```bash
# View the commit
git log -1

# Check commit message format
git log -1 --format=%B
```

---

## Pushing Changes

### Push to Branch

```bash
# Push to current branch
git push

# Push and set upstream for new branch
git push -u origin branch-name

# Force push (use with caution!)
git push --force-with-lease
```

### Post-Push Checklist

- [ ] Verify push succeeded
- [ ] Check CI/CD pipeline status
- [ ] Review any automated checks
- [ ] Create PR if ready for review

---

## Creating Pull Requests

### Analyze ALL Commits First

**CRITICAL**: Before creating a PR, review the **complete branch history** to understand the full scope of work:

```bash
# Get the base branch (usually main)
BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# View ALL commits that will be in this PR (from divergence point)
git log --oneline $BASE_BRANCH..HEAD

# View full diff of all changes against base
git diff $BASE_BRANCH...HEAD --stat
```

The PR description MUST summarize ALL commits shown above, not just the most recent commit. This ensures reviewers understand the complete scope of work.

### PR Creation with gh CLI

```bash
gh pr create --title "Brief PR title" --body "$(cat <<'EOF'
## Summary
High-level overview of ALL changes across ALL commits in 1-3 sentences.

## Changes
- Change 1 with explanation
- Change 2 with explanation
- Change 3 with explanation

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Edge cases verified

## Documentation
- [ ] README updated (if applicable)
- [ ] API docs updated (if applicable)
- [ ] Comments added for complex logic

## Notes
Any additional context, caveats, or follow-up items.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### PR Title Format

Follow same conventions as commit messages:
- `feat(scope): add new feature`
- `fix(scope): resolve specific issue`
- `docs: update documentation`

### PR Description Template

```markdown
## Summary
Brief explanation of what this PR does and why.

## Changes
- Bullet point list of key changes
- Each change should be specific
- Group related changes together

## Testing
How these changes were tested:
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] Edge cases covered

## Screenshots (if UI changes)
[Add screenshots here]

## Checklist
- [ ] Tests pass
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Reviewed own code

## Related Issues
Closes #123
Related to #456

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### PR Best Practices

**Do:**
- Keep PRs focused and small (< 400 lines when possible)
- Write clear, descriptive titles and descriptions
- Include test plan or evidence of testing
- Link related issues/tickets
- Add screenshots for UI changes
- Review your own PR first
- Respond to reviewer feedback promptly

**Don't:**
- Mix unrelated changes in one PR
- Submit PRs with failing tests
- Leave PR descriptions empty
- Force push after reviews start (unless requested)
- Merge without required approvals

---

## Common Workflows

### Feature Development Workflow

```bash
# 1. Create new branch
git checkout -b feat/new-feature

# 2. Make changes and commit
git add .
git commit -m "feat: add new feature

Detailed explanation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Push to remote
git push -u origin feat/new-feature

# 4. Create PR
gh pr create --title "feat: add new feature" --body "..."

# 5. Address review feedback
# Make changes, commit, push

# 6. Merge when approved
gh pr merge --squash  # or --merge, --rebase
```

### Bug Fix Workflow

```bash
# 1. Create fix branch
git checkout -b fix/issue-123

# 2. Make fix and commit
git commit -m "fix: resolve issue with X

Fixed by doing Y because Z.

Closes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Push and create PR
git push -u origin fix/issue-123
gh pr create --title "fix: resolve issue #123" --body "..."
```

### Documentation Update Workflow

```bash
# 1. Create docs branch
git checkout -b docs/update-readme

# 2. Update documentation
git commit -m "docs: update installation guide

Added troubleshooting section and clarified prerequisites.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Push and create PR
git push -u origin docs/update-readme
gh pr create --title "docs: update installation guide" --body "..."
```

---

## Git Worktrees

### When to Use Worktrees

- We use worktrees for each new feature or bug fix.

### Creating Worktrees

```bash
# Use the helper script
~/scripts/wt.sh feature-name
```

### Managing Worktrees

```bash
# List all worktrees
git worktree list

# Remove worktree
git worktree remove ../project-feature-name

# Prune stale worktrees
git worktree prune
```

---

## Handling Pre-commit Hooks

### If Commit Fails Due to Hooks

If a pre-commit hook modifies files:

1. **Check what changed:**
   ```bash
   git diff
   ```

2. **If changes are formatting/auto-fixes, amend:**
   ```bash
   git add .
   git commit --amend --no-edit
   ```

3. **Verify commit authorship before amending:**
   ```bash
   git log -1 --format='%an %ae'
   ```
   - Only amend if it's your commit
   - Never amend commits from other developers

4. **If you can't amend, create new commit:**
   ```bash
   git add .
   git commit -m "chore: apply pre-commit fixes

Applied auto-formatting from pre-commit hooks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

---


---

## CI/CD Integration

### Check CI Status

```bash
# View PR checks
gh pr checks

# View workflow runs
gh run list

# View specific run details
gh run view <run-id>
```

### Re-running Failed Checks

```bash
# Re-run failed checks
gh run rerun <run-id> --failed

# Re-run all checks
gh run rerun <run-id>
```

---

## Branch Protection Rules

### Typical Requirements

Most projects require:
- [ ] All status checks pass
- [ ] At least 1 approval from reviewer
- [ ] No merge conflicts
- [ ] Branch is up-to-date with base
- [ ] Linear history (if required)

### Updating Branch

```bash
# Update with main
git fetch origin
git merge origin/main

# Or rebase (if linear history required)
git fetch origin
git rebase origin/main
```

---

## Versioning and Releases

### Creating Release Tags

When creating a release, follow semantic versioning and tag appropriately.

**See [semantic-versioning.md](semantic-versioning.md) for comprehensive versioning guidance.**

```bash
# 1. Update version in code (pyproject.toml, __version__, etc.)
# 2. Update CHANGELOG.md with release notes
# 3. Commit version bump
git add .
git commit -m "chore: prepare release v1.5.3

Updated version to 1.5.3 and finalized changelog.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. Create annotated tag
git tag -a v1.5.3 -m "Release version 1.5.3"

# 5. Push commit and tag
git push origin main
git push origin v1.5.3
```

### Version Bump Decision

**MAJOR (x.0.0):** Breaking changes
- Removing public APIs
- Changing function signatures
- Incompatible behavior changes

**MINOR (x.Y.0):** New features (backward-compatible)
- Adding new APIs
- Adding optional parameters
- New functionality

**PATCH (x.y.Z):** Bug fixes (backward-compatible)
- Fixing bugs
- Security patches
- Documentation updates

**Example:**
```bash
# Bug fix: 1.5.2 → 1.5.3
git commit -m "fix: correct discount calculation"

# New feature: 1.5.3 → 1.6.0
git commit -m "feat: add user caching functionality"

# Breaking change: 1.6.0 → 2.0.0
git commit -m "feat!: migrate to OAuth2 authentication

BREAKING CHANGE: Removed legacy token-based auth."
```

---

## Quick Reference

### Commit

```bash
git add .
git commit -m "type(scope): description

Details here.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

### Create PR

```bash
gh pr create \
  --title "type(scope): description" \
  --body "$(cat <<'EOF'
## Summary
...

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```