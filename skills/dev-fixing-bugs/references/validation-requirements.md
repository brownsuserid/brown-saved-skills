# Validation Requirements

This guide details all quality gates that must pass before a bug fix is considered complete.

## Stop Hook Automation

The Stop hook (`python_quality_check.sh`) automatically runs after every Claude Code turn:
- ✅ Formatting (`ruff format`)
- ✅ Linting (`ruff check --fix`)
- ✅ Type checking (`mypy`)
- ✅ Unit tests (`pytest -m "not integration"`)

**Check Stop hook output for failures before proceeding with manual checks.**

## Mandatory Quality Gates

ALL bug fixes must pass these gates. No exceptions.

### Automated by Stop Hook

These run automatically - just verify the Stop hook output shows no failures:
- [ ] **Unit tests pass** (all existing + new tests)
- [ ] **Type checking passes** (mypy)
- [ ] **Linting passes** (ruff check)
- [ ] **Formatting applied** (ruff format)

### Manual Checks Required

These are NOT covered by the Stop hook:

#### Integration Tests
```bash
cd [PROJECT_ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v
```
- [ ] **All integration tests pass**
- [ ] **No side effects** introduced in other parts of the system
- [ ] **End-to-end flow works** if bug affected integration points
- [ ] **Integration tests tagged** with `@pytest.mark.integration`

#### Security Scanning
```bash
bandit -c pyproject.toml -r .
```
- [ ] **No new security issues**
- [ ] **Existing security issues not worsened**
- [ ] **Security implications reviewed** if fix touches:
  - User input handling
  - Authentication/authorization
  - Data validation
  - External API calls
  - File system operations
  - Database queries

**Common Security Concerns:**
- SQL injection risks
- Command injection risks
- Path traversal vulnerabilities
- Insecure random number generation
- Hardcoded secrets
- Insecure deserialization

#### Test Coverage
- [ ] **90%+ test coverage maintained** or improved
- [ ] **Bug-related code is covered** by tests
- [ ] **No coverage regression** from the fix

### Documentation Requirements

#### Code Documentation
- [ ] **Docstrings updated** if function behavior changed
- [ ] **Comments added** to explain non-obvious fixes
- [ ] **Complex logic explained** in comments
- [ ] **TODO/FIXME removed** if fix addresses them

**Documentation Standards:**
Follow `../references/coding-standards.md`:
- Google-style docstrings
- Document parameters, returns, raises
- Include examples for complex functions
- Explain WHY not just WHAT

#### Bug Fix Documentation
- [ ] **Root cause explained** in commit message
- [ ] **Fix approach described** in commit message
- [ ] **Impact assessed** and documented
- [ ] **Related issues referenced** (e.g., "Fixes #123")

#### API/External Documentation
If bug affected external APIs or user-facing features:
- [ ] **API docs updated** if behavior changed
- [ ] **Changelog updated** with bug fix note
- [ ] **Migration guide provided** if breaking change
- [ ] **User documentation updated** if user-visible

### Git Requirements

#### Commit Message Quality
Follow `../references/git-conventions.md`:

```
fix: [brief description of bug]

Root Cause:
[Explain what was actually wrong]

Fix Applied:
[Explain what changed to fix it]

Impact:
[Describe what this fixes and any side effects]

Tests:
[Describe test coverage added]

Fixes #[issue-number]

-Agent Generated Commit Message
```

**Required Elements:**
- [ ] **Type prefix** (`fix:` for bug fixes)
- [ ] **Brief title** (max 72 chars)
- [ ] **Detailed body** explaining root cause and fix
- [ ] **Reference to issue** if applicable
- [ ] **Agent signature** at end

#### Branch & PR Requirements
- [ ] **Branch created** from main/master (use ~/scripts/wt.sh if using worktrees)
- [ ] **Descriptive branch name** (e.g., `fix/user-authentication-bug`)
- [ ] **Never push directly to main**
- [ ] **PR created** with detailed description
- [ ] **PR links to issue** being fixed
- [ ] **PR includes test evidence** (screenshots, logs, etc.)

### Pre-Commit Checklist

**Automated by Stop Hook:** Unit tests, mypy, ruff check, ruff format run automatically.

**Manual checks before commit:**

```bash
# 1. Integration tests (not in Stop hook)
cd [PROJECT_ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v

# 2. Security scan (not in Stop hook)
bandit -c pyproject.toml -r .

# 3. Review changes
git diff

# 4. Stage changes
git add .

# 5. Commit with proper message
git commit -m "$(cat <<'EOF'
fix: resolve race condition in user authentication

Root Cause:
Session tokens were being validated and updated in separate operations,
allowing a window where expired tokens could be used.

Fix Applied:
Combined validation and update into atomic database transaction using
SELECT FOR UPDATE to lock the row during validation and update.

Impact:
Eliminates race condition in concurrent authentication requests.
No breaking changes to API or user experience.

Tests:
- Added test_concurrent_token_validation() to verify fix
- Added test_expired_token_rejected() for edge case
- All existing tests pass

Fixes #456

-Agent Generated Commit Message
EOF
)"
```

### Post-Commit Validation

After committing but before creating PR:

- [ ] **CI/CD pipeline passes** (if applicable)
- [ ] **Build succeeds** in clean environment
- [ ] **Tests pass in CI** (not just locally)
- [ ] **No environment-specific issues**

### Lead Developer Testing

Before marking bug as complete:

- [ ] **Lead developer has tested** the fix
- [ ] **Original bug scenario verified fixed**
- [ ] **Edge cases manually tested**
- [ ] **No regressions observed**
- [ ] **Performance impact assessed** (if relevant)

**Testing Scenarios to Provide:**

1. **Original Bug Scenario**
   - Steps to reproduce original bug
   - Expected failure before fix
   - Expected success after fix

2. **Edge Cases**
   - Boundary conditions
   - Null/empty inputs
   - Maximum values
   - Concurrent operations

3. **Regression Testing**
   - Related features still work
   - Dependent systems unaffected
   - Performance not degraded

## Validation Workflow

### Phase 1: Stop Hook Verification
The Stop hook runs automatically after every turn. Verify its output shows:
- ✅ Unit tests passing
- ✅ Type checking passing
- ✅ Linting passing
- ✅ Formatting applied

### Phase 2: Manual Checks
Run checks NOT covered by Stop hook:
```bash
# Integration tests
cd [PROJECT_ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v

# Security scan
bandit -c pyproject.toml -r .
```

### Phase 3: Code Review
- Self-review changes in git diff
- Check for unintended changes
- Verify only bug fix changes included (no scope creep)

### Phase 4: Lead Developer Approval
- Provide testing instructions
- Demonstrate fix working
- Get explicit approval

### Phase 5: Commit & PR
- Only after ALL above phases complete
- Push to feature branch
- Create PR with evidence
- Wait for CI/CD before merging

## Common Validation Pitfalls

### ❌ Pitfall: "Tests pass on my machine"
**Solution:** Run tests in clean environment, verify CI passes

### ❌ Pitfall: "Forgot to add test file to git"
**Solution:** Always run `git status` before committing

### ❌ Pitfall: "Fixed bug but broke something else"
**Solution:** Run FULL test suite, not just new tests

### ❌ Pitfall: "Type hints pass but runtime fails"
**Solution:** Run actual tests, don't rely only on mypy

### ❌ Pitfall: "Works in dev but fails in production"
**Solution:** Test with production-like data and configuration

### ❌ Pitfall: "Formatting changes mixed with fix"
**Solution:** Format entire codebase first (separate commit), then fix bug

### ❌ Pitfall: "Skipped security scan"
**Solution:** Always run bandit, especially for user input handling

## Quality Gate Failure Response

If any quality gate fails:

### Test Failures
1. Review test output carefully
2. Determine if test needs fixing OR fix needs adjustment
3. Never skip/disable tests without investigation
4. Add tests for newly discovered edge cases

### Linting Failures
1. Fix issues rather than suppressing warnings
2. If suppression needed, add comment explaining why
3. Keep suppressions minimal and localized

### Type Checking Failures
1. Add proper type hints rather than using `Any`
2. Fix inference issues with explicit types
3. Use `# type: ignore[specific-error]` with explanation if unavoidable

### Security Scan Failures
1. Treat seriously—don't ignore
2. Fix vulnerability or prove it's false positive
3. Document why false positive in code comment
4. Consider alternative approaches that avoid the issue

## Success Criteria Summary

Bug fix is complete when:

**Stop Hook (Automated):**
✅ Unit tests passing
✅ Type checking passes (mypy)
✅ Linting passes (ruff check)
✅ Formatting applied (ruff format)

**Manual Checks:**
✅ Root cause identified and validated
✅ Fix implemented with minimal changes
✅ Integration tests passing
✅ Security scan passes (bandit)
✅ Lead developer tested and approved
✅ Commit message explains root cause and fix
✅ PR created (never direct push to main)
✅ CI/CD pipeline passes

Only then is the bug fix ready to merge.
