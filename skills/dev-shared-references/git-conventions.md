# Git Commit and Push Conventions

Quick reference for git commit and push operations. **For comprehensive workflows, see [git-and-pr-workflow.md](git-and-pr-workflow.md).**

## When to Apply

Apply these conventions whenever:
1. The user indicates they want to commit or push changes
2. The user asks about git commit conventions
3. The user wants to update or save their work to git
4. Any git-related commit and push operations are requested

This ensures consistent commit message formatting, proper change documentation, and maintainable git history.

## Quick Commit Format

```bash
git commit -m "$(cat <<'EOF'
type(scope): brief description

Detailed explanation of changes:
- What was changed
- Why it was changed
- Any important details

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Aaron <aaron@brainbridge.app>
EOF
)"
```

## Commit Types

- **feat**: New feature or functionality (may bump MINOR version)
- **fix**: Bug fix (may bump PATCH version)
- **docs**: Documentation changes only
- **style**: Code formatting, whitespace (no functional changes)
- **refactor**: Code restructuring without behavior changes
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates
- **perf**: Performance improvements
- **feat!** or **fix!**: Breaking changes (bumps MAJOR version)

**Version bumping:** See [semantic-versioning.md](semantic-versioning.md) for detailed guidance.

## Commit Message Guidelines

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

## Git Workflow Essentials

### Branching Strategy

- Always work in git worktrees for each feature/bug fix
- Use `~/scripts/wt.sh feature-name` to create worktrees
- Always push to a branch and use PRs for changes to main
- Never push directly to main/master

### Branch Naming

- `feat/feature-name` - For new features
- `fix/bug-description` - For bug fixes
- `refactor/component-name` - For refactoring
- `docs/update-description` - For documentation updates
- `test/test-description` - For test additions

## Pre-Commit Checklist

Before committing, verify:
- [ ] All tests pass
- [ ] Code is formatted (ruff/black)
- [ ] Linting passes (ruff check)
- [ ] Type checking passes (mypy, if applicable)
- [ ] No unintended files staged
- [ ] Commit message is clear and descriptive

## Post-Commit Actions

After committing:
1. Push to remote branch: `git push` or `git push -u origin branch-name`
2. Verify CI/CD pipeline passes
3. Create pull request if ready for review
4. Link to relevant issues or tickets in PR description

---

## Complete Documentation

**For comprehensive guidance, see:**
- [git-and-pr-workflow.md](git-and-pr-workflow.md) - Complete git workflow including PRs, worktrees, CI/CD, versioning
- [semantic-versioning.md](semantic-versioning.md) - Version bumping and release management

**Common workflows:**
- Feature development
- Bug fixes
- Documentation updates
- Pull request creation
- Handling pre-commit hooks
- CI/CD integration
- Versioning and releases
