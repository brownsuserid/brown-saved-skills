---
name: quality-checks
description: Runs comprehensive quality validation when ready to verify code meets production standards. Executes all tests, type checking, security scanning, linting, and formatting. Takes time to be thorough with no time constraints. Use before creating a PR, after implementing a feature, after fixing a bug, or before deployment.
---

# Quality Checks Skill

This skill runs quality gates that are NOT covered by the Stop hook. The Stop hook (`python_quality_check.sh`) already runs automatically after every Claude Code turn: formatting (ruff format), linting (ruff check --fix), type checking (mypy), and unit tests (pytest -m "not integration").

This skill adds: integration tests, security scanning, and user validation.

Use the TodoWrite tool to track progress through these phases.

---

## Phase 1: Verify Stop Hook Results

Check the Stop hook output from the most recent turn for failures in unit tests, type checking, linting, or formatting. Fix any failures before proceeding.

---

## Phase 2: Run Integration Tests

```bash
cd [PROJECT_ROOT]
set -a && source .env && set +a
PYTHONPATH=. uv run pytest -m integration -v
```

**ALL integration tests MUST pass.**

### If Tests Fail

There is no concept of a "pre-existing failure." Every failure is a blocker, regardless of when it was introduced.

1. Review failure output — check for environment or container issues
2. Common causes:
   - Missing `.env` file or invalid values
   - Docker daemon not running or container failed to start
   - Database connection or schema issues
3. Isolate failures: `pytest -k test_name -v -m integration`
4. Investigate root cause systematically — see [../dev-fixing-bugs/references/root-cause-analysis.md](../dev-fixing-bugs/references/root-cause-analysis.md)
5. Fix the failing tests or underlying code
6. Re-run ALL integration tests after fixes
7. Only proceed when every test passes
8. If you genuinely cannot fix a failure (e.g., external service down), stop and report to the user with full details — do not silently skip

**Detailed guidance:** See `references/quality-standards.md` Section 2.

---

## Phase 3: Run Anti-Pattern Scan

Run `dev-reviewing-code` in Deep Scan mode on the changed files to catch code smells, error swallowing, tight coupling, and other issues that automated linting misses.

```bash
# Identify changed files
git diff --name-only origin/main
```

Focus the scan on the files that changed. For each finding, fix the issue or document why it's acceptable.

---

## Phase 4: Run Security Scanning

```bash
cd [PROJECT_ROOT]
uv run bandit -c pyproject.toml -r .
```

**NO medium or high severity issues allowed.**

### If Security Issues Found

1. Review issue codes and descriptions
2. Fix ALL medium and high severity issues:
   - Hardcoded secrets → use environment variables
   - SQL injection → use parameterized queries
   - Command injection (shell=True) → use list arguments
   - Weak random → use `secrets` module
3. **CRITICAL: After fixing security issues, re-run integration tests (Phase 2), re-run anti-pattern scan (Phase 3), and then re-run bandit.** Security fixes can change behavior — modified validation logic, different error handling, changed function signatures. Only proceed once all security issues are resolved AND all tests still pass.

**Detailed guidance:** See `references/quality-standards.md` Section 4.

---

## Phase 5: User Validation

Ask the user to test the application. Provide them with:

1. **What Changed** — Summary of changes made
2. **How to Test** — Step-by-step instructions with expected behavior at each step
3. **Edge Cases to Try** — Not just the happy path
4. **Expected Results** — What should happen in each scenario

Wait for explicit user approval before declaring production-ready. Do not proceed without confirmation.

---

## Quality Checklist

Before declaring code production-ready, all items must be checked:

- [ ] Stop hook: Passing (unit tests, mypy, ruff)
- [ ] Integration tests: ALL passing
- [ ] Anti-pattern scan: No unaddressed issues in changed files
- [ ] Security scanning: No medium/high issues
- [ ] If security fixes applied: Re-ran integration tests and anti-pattern scan afterward
- [ ] User validation: Tested and approved
- [ ] 90%+ test coverage maintained

---

## Supporting Files Reference

### Quality Check Specific
- `references/quality-standards.md` - Complete guide for all quality gates, common issues, troubleshooting

### Related Skills
- `../dev-reviewing-code/SKILL.md` - Code review with Deep Scan mode for anti-pattern detection (used in Phase 3)

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` - Python best practices, type hints, docstrings
- `../dev-shared-references/git-conventions.md` - Commit message format and workflow
- `../dev-shared-references/uv-guide.md` - Dependency management with uv

---

## Key Principles

- **Thoroughness over speed:** Take the time needed to ensure quality
- **Every failure is a blocker:** No skipping, no "pre-existing" exceptions
- **Re-test after security fixes:** Security changes require re-running integration tests
- **User approval required:** Automated checks are necessary but not sufficient
