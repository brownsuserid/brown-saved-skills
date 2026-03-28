---
description: Executes a roadmap plan file
---
# Execute Roadmap Plan

Use TodoWrite to track progress through the plan execution:

## 1. Find the Plan
- Locate the plan file in the `plans/` folder
- Read and understand the requirements

## 2. Review Standards
- Read project rules and coding standards
- Understand existing patterns in the codebase

## 3. Setup Worktree
- Check if you're in a worktree
- If not, create one using `wt <branch-name>`
- Ensure latest code: `git fetch origin && git rebase origin/main`

## 4. Execute Plan (TDD)
Follow the plan using test-driven development:
- Write tests first (see [dev-writing-unit-tests](mdc:dev-writing-unit-tests/SKILL.md) for patterns)
- Implement features
- Validate tests pass after each step
- For integration tests, see [dev-writing-integration-tests](mdc:dev-writing-integration-tests/SKILL.md)

## 5. Quality Checks
**Note:** The Stop hook automatically runs formatting, linting, type checking, and unit tests after every turn. Focus on checks NOT covered by the Stop hook.

```bash
# Integration tests (not in Stop hook - requires .env)
cd [PROJECT ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v

# Security scanning (not in Stop hook)
bandit -c pyproject.toml -r .
```
If security issues found, fix and re-run integration tests.

### Anti-Pattern Scan (Post-Implementation)
After implementation is complete, run the anti-pattern detection skill to catch AI-generated code smells before PR:
- See [dev-reviewing-code](mdc:dev-reviewing-code/SKILL.md) - Use Deep Scan mode to catch error swallowing, duplication, and other common AI-generated anti-patterns

## 6. User Approval
Ask the user to test the application before committing.

## 7. Commit and Push
- Create commit with Conventional Commits format
- Push to remote branch
- Create PR if needed
