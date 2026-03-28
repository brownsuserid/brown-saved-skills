---
description: Conducts quality checks then if passing, commits changes, pushes them to Github and creates a PR.
---
# Commit, Push, and Create PR

Use TodoWrite to track progress:

## 1. Update Plan File
Update the `/plans` file to reflect completed tasks.

## 2. Run Quality Checks

Follow the `dev-quality-checks` skill to run comprehensive quality validation (integration tests, security scanning, user validation). Do not proceed to commit until all checks pass.

## 3. Generate Changelog (Optional)
Ask the user: "Would you like to generate a changelog entry for these changes?"

If yes, use the `dev-changelog-generator` skill.

## 4. Self-Review (Recommended)
Before committing, do a quick self-review of your changes for common issues:
- Error-swallowing patterns (broad except returning defaults without re-raise)
- AI-generated duplication (similar functions that should be consolidated)
- Missing type hints or docstrings on new functions
- Architecture diagrams — if changes add/modify components, data flows, or service interactions, verify diagrams in `docs/architecture/` are current

For deeper analysis, use the `dev-reviewing-code` skill.

## 5. Stage, Review, and Commit

```bash
git add .
git status
git diff --cached
```

Review staged changes to ensure no unintended files are included. Follow commit format from `dev-shared-references/git-conventions.md`. End message with "-Agent Generated Commit Message".

## 6. Push to Remote
```bash
git push -u origin <branch-name>
```

## 7. Analyze ALL Commits for PR Description

**STOP. Do NOT skip this step. Do NOT base the PR description on the commit you just made in step 5.**

A branch often has many commits. The PR describes the branch, not one commit. Run these commands and read the full output:

```bash
BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
git log --oneline $BASE_BRANCH..HEAD
git diff $BASE_BRANCH...HEAD --stat
```

If the log shows multiple commits, you MUST read and understand every one of them. The PR title and body must cover ALL of them.

## 8. Create PR

Write a PR title that reflects the full scope of ALL commits on the branch (from step 7), not just the latest commit. The body should summarize every significant change across the entire branch diff.

```bash
gh pr create --title "type: description covering full branch scope" --body "$(cat <<'EOF'
## Summary
- [Summarize ALL changes across ALL commits on this branch]

## Test plan
- [How to verify the changes]

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Only mention formatting/linting if it was the sole focus of the PR.
