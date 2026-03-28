# Quality Standards Reference

This document details the quality gates that must pass before code is considered production-ready.

## CRITICAL: Every Failure Is a Blocker

There is no concept of a "pre-existing failure" in quality checks. ALL tests must pass
before code is considered production-ready. Always treat every failing test as a blocker,
regardless of:
- Whether you caused the failure
- Whether the failure existed before your changes
- Whether the failure seems unrelated to current work

Always fix failing tests or stop and report to the user with full details.

## Stop Hook Automation

The Stop hook (`python_quality_check.sh`) automatically runs after every Claude Code turn:
- ✅ Unit tests (`pytest -m "not integration"`)
- ✅ Type checking (`mypy`)
- ✅ Linting (`ruff check --fix`)
- ✅ Formatting (`ruff format`)

**Check Stop hook output for failures before proceeding with manual checks.**

## Overview

Quality gates fall into two categories:

### Automated by Stop Hook
1. Unit Tests
2. Type Checking
3. Linting
4. Formatting

### Manual Checks Required
5. Integration Tests (requires `.env`)
6. Security Scanning (bandit)
7. User Validation

**Critical:** If security issues are found and fixed, re-run integration tests.

---

## 1. Unit Tests

### What They Check

Unit tests verify individual functions and methods work correctly in isolation:
- Core business logic
- Edge cases and boundary conditions
- Error handling
- Input validation
- Return values and side effects

### Requirements

- **Coverage:** 90%+ code coverage target
- **Speed:** Each test < 100ms
- **Isolation:** Tests must be independent (can run in any order)
- **Markers:** Must NOT include integration tests (`-m "not integration"`)

### Command

```bash
cd [PROJECT ROOT]
PYTHONPATH=. uv run pytest -m "not integration" -v
```

### Common Failures

**Import errors:**
- Missing `PYTHONPATH=.` environment variable
- Package not installed via `uv sync`
- Incorrect import paths

**Assertion failures:**
- Logic error in implementation
- Test expectations incorrect
- Missing edge case handling

**Fixture errors:**
- Incorrect fixture scope
- Missing fixture dependency
- Shared mutable state between tests

### How to Fix

1. **Read the failure message carefully** - pytest provides detailed output
2. **Run single test to isolate:** `pytest -k test_specific_name -v`
3. **Check test expectations** - verify they match requirements
4. **Fix implementation** - don't modify tests to pass (unless test is wrong)
5. **Re-run all tests** - ensure fix doesn't break other tests

---

## 2. Integration Tests

### What They Check

Integration tests verify multiple components work together correctly:
- Database operations (queries, transactions, constraints)
- API endpoints (request/response with persistence)
- External service integration (mocked or containerized)
- Complete user workflows
- Multi-module interactions

### Requirements

- **Markers:** Tagged with `@pytest.mark.integration`
- **Environment:** Requires `.env` file for configuration
- **Isolation:** Each test gets clean database state (transaction rollback)
- **Speed:** < 5 seconds per test
- **Dependencies:** May use Testcontainers or Docker Compose

### Command

```bash
cd [PROJECT ROOT]
set -a && source .env && set +a
PYTHONPATH=. uv run pytest -m integration -v
```

**Environment loading:** `set -a && source .env && set +a` loads environment variables

### Common Failures

**Environment errors:**
- Missing `.env` file
- Invalid database connection string
- Missing API keys or credentials

**Container errors:**
- Docker daemon not running
- Container failed to start
- Port conflicts

**Database errors:**
- Schema not created
- Migration not applied
- Transaction not rolled back (test pollution)

**Timeout errors:**
- Container startup too slow
- Expensive database operations
- Missing test timeouts

### How to Fix

1. **Check `.env` file exists** and has correct values
2. **Verify Docker running:** `docker ps`
3. **Run single integration test:** `pytest -k test_integration_name -v -m integration`
4. **Check container logs** if using Testcontainers
5. **Verify database transactions** roll back after each test
6. **Optimize slow tests** - minimize test data, use faster images

---

## 3. Type Checking

### What It Checks

MyPy performs static type analysis to catch type errors before runtime:
- Missing type hints
- Type mismatches (e.g., passing `str` where `int` expected)
- Optional/None handling
- Generic types (List, Dict, etc.)
- Return type consistency
- Attribute access on incorrect types

### Requirements

- **Coverage:** Type hints on all function signatures
- **Strictness:** No `Any` types without justification
- **Consistency:** Return types must match all code paths
- **Imports:** Proper `from typing import` statements

### Command

```bash
cd [PROJECT ROOT]
uv run mypy --exclude 'cdk/cdk\.out' --exclude 'cdk\.out' .
```

**Exclusions:** CDK output directories are excluded (generated code)

### Common Failures

**Missing type hints:**
```python
# ❌ BAD
def calculate(price, discount):
    return price * (1 - discount)

# ✓ GOOD
def calculate(price: float, discount: float) -> float:
    return price * (1 - discount)
```

**Type mismatches:**
```python
# ❌ BAD
def get_user(user_id: int) -> User:
    return None  # Should be Optional[User]

# ✓ GOOD
def get_user(user_id: int) -> Optional[User]:
    return None
```

**Missing imports:**
```python
# ❌ BAD
def process(items: List[str]) -> Dict[str, int]:
    # List and Dict not imported

# ✓ GOOD
from typing import Dict, List

def process(items: List[str]) -> Dict[str, int]:
    ...
```

### How to Fix

1. **Add type hints** to all function parameters and returns
2. **Import types:** `from typing import Optional, List, Dict, Union`
3. **Use Optional[T]** for values that can be None
4. **Use Union[T1, T2]** for multiple possible types
5. **Check return types** match all code paths
6. **Run incrementally:** `mypy path/to/file.py` to fix file by file

---

## 4. Security Scanning

### What It Checks

Bandit scans Python code for common security issues:
- Hardcoded passwords or secrets
- SQL injection vulnerabilities
- Command injection (shell=True)
- Insecure random number generation
- Weak cryptography
- Insecure temporary files
- Dangerous imports (pickle, eval)

### Requirements

- **Severity:** No medium or high severity issues
- **Configuration:** Uses `pyproject.toml` for exclusions
- **Coverage:** All Python files scanned

### Command

```bash
cd [PROJECT ROOT]
bandit -c pyproject.toml -r .
```

**Configuration:** `pyproject.toml` contains exclusions (e.g., test files)

### Common Failures

**Hardcoded secrets:**
```python
# ❌ BAD - B105: Hardcoded password
DATABASE_PASSWORD = "super_secret_123"

# ✓ GOOD
import os
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
```

**SQL injection:**
```python
# ❌ BAD - B608: SQL injection
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✓ GOOD
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

**Shell injection:**
```python
# ❌ BAD - B602: Shell injection
subprocess.call(f"ls {user_input}", shell=True)

# ✓ GOOD
subprocess.call(["ls", user_input])
```

**Weak random:**
```python
# ❌ BAD - B311: Weak random for security
import random
token = random.randint(1000, 9999)

# ✓ GOOD
import secrets
token = secrets.randbelow(10000)
```

### How to Fix

1. **Read issue code** (e.g., B105) and description
2. **Understand the vulnerability** - why it's dangerous
3. **Apply the fix** - use secure alternatives
4. **Re-run bandit** to confirm fixed
5. **CRITICAL:** If you fixed bandit issues, return to Step 1 (re-run all tests)

**Why re-run tests after bandit fixes?**
- Security fixes may change behavior
- Tests validate the fix doesn't break functionality
- Ensures fix doesn't introduce new bugs

---

## 5. Linting

### What It Checks

Ruff checks code quality and style issues:
- Unused imports
- Undefined variables
- Unreachable code
- Complexity issues
- PEP 8 violations
- Import ordering
- Docstring presence
- Code complexity

### Requirements

- **Zero errors:** All linting issues must be resolved
- **Auto-fix:** Use `--fix` flag to automatically resolve issues
- **Configuration:** Uses `pyproject.toml` or `ruff.toml`

### Command

```bash
cd [PROJECT ROOT]
uv run ruff check --fix .
```

**Auto-fix:** `--fix` automatically resolves fixable issues

### Common Failures

**Unused imports:**
```python
# ❌ BAD - F401: Unused import
from typing import List, Dict
import os  # Never used

def process(items: List[str]) -> Dict[str, int]:
    ...
```

**Undefined names:**
```python
# ❌ BAD - F821: Undefined name
def calculate():
    return total_price  # Not defined
```

**Import ordering:**
```python
# ❌ BAD - I001: Import block is un-sorted
from app.models import User
import os
from typing import List

# ✓ GOOD
import os
from typing import List

from app.models import User
```

**Too complex:**
```python
# ❌ BAD - C901: Function too complex
def process(data):
    if condition1:
        if condition2:
            if condition3:
                # Too many nested ifs
```

### How to Fix

1. **Run with auto-fix:** `ruff check --fix .`
2. **Review changes:** Check what ruff fixed automatically
3. **Manually fix remaining issues** - some can't be auto-fixed
4. **Run again** to verify all issues resolved
5. **Refactor complex code** if complexity warnings persist

---

## 6. Formatting

### What It Checks

Ruff format ensures consistent code style:
- Indentation (4 spaces)
- Line length (88 characters default)
- Trailing whitespace
- Blank lines (between functions, classes)
- Quote style (double quotes)
- Comma placement

### Requirements

- **Consistency:** All files must use same formatting
- **Automatic:** Ruff automatically reformats files
- **Non-breaking:** Formatting never changes behavior

### Command

```bash
cd [PROJECT ROOT]
uv run ruff format .
```

**Automatic:** Ruff will reformat files in place

### What Gets Formatted

**Before:**
```python
def calculate(price,discount,tax):
    result=price*(1-discount)*(1+tax)
    return result
```

**After:**
```python
def calculate(price, discount, tax):
    result = price * (1 - discount) * (1 + tax)
    return result
```

### How to Fix

1. **Just run it:** `ruff format .`
2. **Review changes:** `git diff` to see what changed
3. **Commit formatting separately** (if large changes)
4. **Configure if needed:** Set line length in `pyproject.toml`

---

## 7. User Validation

### What It Checks

Manual testing by the lead developer to verify:
- Feature works as intended
- User experience is smooth
- Error messages are clear
- Edge cases are handled gracefully
- No unexpected behavior

### Requirements

- **Explicit approval:** User must confirm working
- **Test scenarios:** Provide clear testing instructions
- **Documentation:** Explain what changed and how to test

### How to Request

Provide the user with:

**Feature/Fix:** [Name]

**What Changed:**
- [Summary of changes]

**How to Test:**
1. [Step-by-step instructions]
2. [Expected behavior at each step]
3. [Edge cases to try]

**Expected Results:**
- [What should happen in each scenario]

### Common Issues

**Unclear instructions:**
- Too vague ("test the login")
- Missing steps
- No expected behavior

**Incomplete testing:**
- Only happy path tested
- Edge cases not covered
- Error scenarios not tried

### How to Fix

1. **Provide specific steps** - exact commands or actions
2. **Include expected results** - what should happen
3. **Cover edge cases** - not just happy path
4. **Wait for approval** - don't proceed without confirmation
5. **Address feedback** - fix any issues found

---

## Quality Gate Workflow

### Standard Flow

**Automated by Stop Hook (runs every turn):**
1. ✓ Unit tests pass
2. ✓ Type checking passes
3. ✓ Linting passes
4. ✓ Formatting applied

**Manual Checks:**
5. Run integration tests → All pass ✓
6. Run security scanning → No issues ✓
7. User validation → Approved ✓

### If Security Issues Found

1. Fix security issues
2. Re-run integration tests → Confirm fixes work
3. Re-run security scan → Confirm issues fixed
4. Continue with user validation

### Why Re-test After Security Fixes?

Security fixes can:
- Change function behavior
- Modify data validation
- Affect error handling

Integration tests validate that security fixes:
- Solve the vulnerability
- Don't break existing functionality
- Work correctly end-to-end

---

## Troubleshooting

### Tests Pass Locally But Fail in CI/CD

**Possible causes:**
- Environment variables not set in CI/CD
- Different Python version
- Missing dependencies
- Test pollution (tests depend on order)

**Solutions:**
1. Run tests with `pytest --random-order` locally
2. Check CI/CD environment variables
3. Verify `pyproject.toml` has all dependencies
4. Check Python version matches CI/CD

### Type Checking Passes Locally But Fails in CI/CD

**Possible causes:**
- Different mypy version
- Missing type stubs
- Different Python version

**Solutions:**
1. Pin mypy version in `pyproject.toml`
2. Install type stubs: `uv add types-*`
3. Match Python version to CI/CD

### Bandit False Positives

**Problem:** Bandit reports issues that aren't real vulnerabilities

**Solutions:**
1. **Suppress specific line:** `# nosec`
   ```python
   password = "test_password_for_testing"  # nosec B105
   ```
2. **Configure exclusions in pyproject.toml:**
   ```toml
   [tool.bandit]
   exclude_dirs = ["tests", "docs"]
   skips = ["B101"]  # Skip assert_used in tests
   ```
3. **Only suppress if genuinely safe** - don't silence real issues

### Tests Hang or Timeout

**Possible causes:**
- Container startup taking too long
- Database query not returning
- Infinite loop in code
- Missing test timeout

**Solutions:**
1. Run single test to identify culprit: `pytest -k test_name -v`
2. Add timeout to specific slow tests via decorator: `@pytest.mark.timeout(10)`
3. Configure global timeout in pytest.ini if needed (requires pytest-timeout plugin)
4. Check Docker container logs for container startup issues
5. Use faster container images (alpine variants)

---

## Summary

**Automated by Stop Hook:**
1. ✓ Unit tests pass
2. ✓ Type checking passes
3. ✓ Linting passes
4. ✓ Formatting applied

**Manual Checks:**
5. ✓ Integration tests pass
6. ✓ Security scan passes
7. ✓ User validates

**All must pass before code is production-ready.**

**If security issues found:** Fix and re-run integration tests.
