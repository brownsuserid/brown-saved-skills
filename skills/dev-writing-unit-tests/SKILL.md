---
name: writing-unit-tests
description: Creates comprehensive, well-isolated unit tests when adding test coverage for new or existing code. Follows modern pytest best practices including proper fixtures, meaningful assertions, and avoids common anti-patterns like test interdependencies and superficial tests. Use this skill whenever someone asks to "write tests", "add test coverage", "unit test this function/class", "add tests for edge cases", or "improve test quality". Also triggers for "my tests are flaky", "tests fail in CI but pass locally", "tests depend on each other", "need better assertions", "tests are too slow", or when reviewing code that lacks test coverage. Do NOT use for integration tests against real databases or deployed AWS — use dev-writing-integration-tests instead.
---

# Writing Unit Tests Skill

Write high-quality unit tests that are independent, fast, meaningful, and maintainable. The most common problems in test suites — flaky tests, cascade failures, superficial coverage — almost always trace back to shared mutable state, poor isolation, or assertions that don't actually verify behavior. This skill focuses on getting those fundamentals right.

Use the TodoWrite tool to track progress through these phases.

---

## Phase 1: Understand What to Test

Before writing any tests, read the code under test thoroughly and plan what needs coverage.

**Identify test scenarios:**
- What is the core behavior? What are the expected inputs and outputs?
- What edge cases exist? (boundary values, empty inputs, None/null)
- What error conditions should be handled? (invalid inputs, exceptions)
- What external dependencies need mocking? (APIs, databases, email, filesystem)

**Check the existing test suite** for patterns, fixtures in conftest.py, and factory conventions already in use. Consistency with the project's testing style matters — don't introduce a new pattern when one already exists.

**See `references/test-design-principles.md`** for detailed guidance on what makes a meaningful test vs. a superficial one.

---

## Phase 2: Set Up Test Infrastructure

Good test infrastructure makes writing each individual test easy. Invest time here to avoid repetitive setup in every test function.

### Fixtures and Isolation

Default to **function-scoped fixtures** (one fresh instance per test). Only broaden scope (class, module, session) when setup is expensive AND the fixture is read-only. If a test modifies a fixture, that fixture must be function-scoped.

```python
@pytest.fixture
def mock_email_service():
    """Mock email service to avoid sending real emails."""
    with patch('app.services.EmailService') as mock:
        yield mock
```

For complex test data, use factories (Factory Boy or simple factory functions) rather than manually constructing objects in every test.

**See `references/test-isolation.md`** for comprehensive fixture patterns, conftest.py organization, factory setup, and debugging test pollution.

### Async Code

If the code under test uses `async def` / `await`, tests must also be async — it's a syntax requirement, not a style choice:

```python
@pytest.mark.asyncio
async def test_fetch_user_returns_user_data():
    result = await fetch_user_from_db(user_id=123)
    assert result.email == "test@example.com"
```

Use `AsyncMock` (not `Mock`) for async dependencies, and `assert_awaited_once()` for verification.

**See `references/async-testing-guide.md`** for complete async testing patterns including fixtures, mocking, retry testing, and event loop management.

### Windows Note

On Windows, avoid shell redirection (`>`, `>>`) for creating test files — it can corrupt files with null bytes. Use the Write tool or `Path.write_text("", encoding="utf-8")` instead.

---

## Phase 3: Write Tests Following AAA Pattern

Every test should follow Arrange-Act-Assert. This isn't just convention — it makes tests self-documenting. When a test fails, AAA structure lets you immediately see what was set up, what was called, and what expectation was violated.

```python
def test_calculate_discount_applies_percentage_correctly(user_factory):
    # Arrange
    user = user_factory(membership="premium")
    original_price = 100.00

    # Act
    final_price = calculate_discount(user=user, price=original_price, discount_rate=0.2)

    # Assert
    assert final_price == 80.00
```

### Naming Convention

Use `test_[what]_[scenario]_[expected_behavior]` — test names are the first thing you see in failure output, so they should tell you what broke without reading the test body:

```python
def test_calculate_discount_with_zero_rate_returns_original_price(): ...
def test_calculate_discount_with_invalid_rate_raises_value_error(): ...

# NOT: test_discount_1(), test_user_stuff()
```

### Use Parametrize for Related Scenarios

When testing the same behavior with different inputs, `@pytest.mark.parametrize` eliminates duplication while keeping each case independent:

```python
@pytest.mark.parametrize("input_email,is_valid", [
    ("user@example.com", True),
    ("user@company.co.uk", True),
    ("invalid@", False),
    ("@example.com", False),
    ("", False),
])
def test_email_validation(input_email, is_valid):
    assert is_valid_email(input_email) == is_valid
```

---

## Phase 4: Avoid Common Anti-Patterns

These are the three most common ways tests end up providing false confidence. Each one creates tests that pass but don't actually verify anything useful:

**Secret Catcher** — Test has no assertions. It only "passes" because no exception was thrown. The function could return completely wrong data and the test would still pass.

**Dodger** — Test asserts on side effects or setup data but never checks the core behavior. Example: testing `send_email()` by asserting `user.email is not None` but never verifying the email was sent.

**Null Assertions** — Assertions are too vague to catch bugs: `assert data is not None`, `assert isinstance(data, dict)`. These pass even when data is completely wrong.

**Complete anti-pattern guide with examples:** See `references/test-design-principles.md`

---

## Phase 5: Ensure Test Isolation

Tests that depend on each other are the #1 source of flaky test suites. The fix is almost always the same: use function-scoped fixtures instead of shared state.

**Red flags to watch for:**
- Global variables modified across tests
- Tests that fail when run with `pytest --randomly` or `pytest -k test_name`
- Class/module-scoped fixtures being mutated

**Verify independence** after writing tests:
```bash
pytest --randomly tests/test_module.py
pytest -k test_specific_test tests/test_module.py
```

**Complete isolation guide and pollution debugging:** See `references/test-isolation.md`

---

## Phase 6: Validate and Finalize

Before committing, run the quality checklist at `references/test-quality-checklist.md` and verify:

```bash
uv run pytest tests/test_module.py                              # All tests pass
uv run pytest --cov=app --cov-report=term-missing tests/        # Coverage >= 90%
uv run pytest --durations=10 tests/                             # Each test < 100ms
uv run pytest --randomly tests/test_module.py                   # Independence check
```

Unit tests should run fast (< 100ms each) because they mock all external dependencies. If a test is slow, it's probably making real I/O calls that should be mocked. If a test legitimately needs more time, use `@pytest.mark.timeout(10)` rather than a global timeout flag.

Then run [dev-quality-checks](../dev-quality-checks/SKILL.md) for linting, formatting, and type checking.

---

## Supporting Files Reference

### Test-Writing Specific
- `references/test-design-principles.md` - AAA pattern, meaningful tests, anti-patterns with examples
- `references/test-isolation.md` - Fixtures, scopes, conftest.py, factory patterns, debugging pollution
- `references/async-testing-guide.md` - Async testing patterns, AsyncMock, event loops, FastAPI testing
- `references/test-quality-checklist.md` - Comprehensive quality checklist for self-review
- `templates/unit-test-template.md` - Starter templates for test files, conftest.py, and factories

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` - Python best practices, type hints, docstrings
- `../dev-shared-references/git-conventions.md` - Commit message format and workflow
- `../dev-shared-references/uv-guide.md` - Dependency management with uv

---

## Success Criteria

- Tests follow AAA pattern consistently
- All tests independent and isolated (verified by random order runs)
- Meaningful assertions that test actual behavior, not just existence
- Proper use of fixtures with appropriate scopes
- No anti-patterns (Secret Catcher, Dodger, Null Assertions)
- 90%+ code coverage maintained
- All tests run in < 100ms each
- Can run in any order (`pytest --randomly`)
- All quality gates pass (linting, formatting, type checking)
