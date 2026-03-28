# Test Quality Checklist

Use this checklist to ensure your tests are high-quality, maintainable, and effective.

## Before Writing Tests

### Planning

- [ ] **Understand the requirement**: What behavior are you testing?
- [ ] **Identify test cases**: Happy path, edge cases, error cases
- [ ] **Check existing tests**: Are similar tests already written?
- [ ] **Plan test data**: What data do you need? Can you use factories?

---

## Writing Individual Tests

### Test Structure

- [ ] **Follows AAA pattern**: Arrange, Act, Assert clearly separated
- [ ] **Tests one thing**: Single logical concept per test
- [ ] **Descriptive name**: `test_[what]_[scenario]_[expected]`
- [ ] **Has docstring** (if complex): Explains what's being tested

### Assertions

- [ ] **Meaningful assertions**: Not just `assert x is not None`
- [ ] **Tests behavior**: Not implementation details
- [ ] **Core behavior tested**: Not just side effects (avoid "Dodger" anti-pattern)
- [ ] **Specific values**: Not just type checks or existence checks
- [ ] **Exception testing**: Uses `pytest.raises` for expected errors

### Independence

- [ ] **No shared state**: Doesn't rely on global variables
- [ ] **No order dependence**: Can run in any order
- [ ] **Uses fixtures**: For setup/teardown, not manual code
- [ ] **Clean state**: Each test starts fresh
- [ ] **Can run alone**: `pytest -k test_specific_test` works

### Performance

- [ ] **Runs fast**: < 100ms for unit tests
- [ ] **Mocks externals**: No real HTTP calls, file I/O, etc.
- [ ] **Uses in-memory DB**: SQLite `:memory:` or test database
- [ ] **No sleeps/waits**: No `time.sleep()` or arbitrary waits

---

## Test Coverage

### Scenarios Covered

- [ ] **Happy path**: Normal, expected inputs
- [ ] **Edge cases**: Boundary values, empty inputs, None
- [ ] **Error cases**: Invalid inputs, missing data
- [ ] **Parametrized**: Multiple scenarios via `@pytest.mark.parametrize`

### Comprehensive Coverage

- [ ] **90%+ code coverage**: Run `pytest --cov`
- [ ] **All branches covered**: If/else, try/except, loops
- [ ] **All public methods**: Every public API has tests
- [ ] **Integration points**: Interactions with other modules tested

---

## Fixtures and Test Data

### Fixture Usage

- [ ] **Appropriate scope**: Function (default), class, module, or session
- [ ] **Uses yield**: For cleanup/teardown
- [ ] **Defined in conftest.py**: If shared across files
- [ ] **Single responsibility**: Each fixture does one thing
- [ ] **No modification**: Class/module/session fixtures not modified in tests

### Test Data

- [ ] **Uses factories**: Factory Boy for complex objects
- [ ] **Uses Faker**: For realistic random data
- [ ] **Minimal data**: Only what's needed for the test
- [ ] **Readable data**: Clear what each value represents

---

## Mocking and Isolation

### External Dependencies

- [ ] **Mocks external APIs**: No real HTTP requests
- [ ] **Mocks database**: Uses in-memory or test database
- [ ] **Mocks time**: Uses `freezegun` or `time-machine` for time-dependent code
- [ ] **Mocks file system**: Uses `tmp_path` or mocks
- [ ] **Mocks email/SMS**: External services mocked

### Proper Mocking

- [ ] **Mocks the right level**: Mock at boundaries, not internals
- [ ] **Verifies calls**: Uses `assert_called_with` when needed
- [ ] **Reasonable returns**: Mock returns realistic data
- [ ] **Handles failures**: Mocks error scenarios too

---

## Code Quality

### Readability

- [ ] **Clear variable names**: `user`, `expected_result`, not `x`, `temp`
- [ ] **No magic numbers**: Use named constants
- [ ] **Comments for complex setup**: Explains WHY, not WHAT
- [ ] **Consistent style**: Follows project conventions

### Maintainability

- [ ] **DRY principles**: Uses fixtures/factories, not duplicate setup
- [ ] **No hardcoded paths**: Uses `tmp_path`, relative paths, or config
- [ ] **No hardcoded URLs**: Uses config or environment variables
- [ ] **Parametrized for variations**: Not duplicate test functions

### Following Standards

- [ ] **Type hints**: Test functions have type hints if used in project
- [ ] **Follows `../references/coding-standards.md`**: Project standards applied
- [ ] **Passes linting**: `ruff check tests/`
- [ ] **Formatted**: `ruff format tests/`

---

## Anti-Patterns to Avoid

### Design Anti-Patterns

- [ ] **NOT a "Secret Catcher"**: Has meaningful assertions
- [ ] **NOT a "Dodger"**: Tests core behavior, not just side effects
- [ ] **NOT "Null Assertions"**: Asserts specific values, not just existence
- [ ] **NOT enumerated names**: No `test_1`, `test_2`, etc.
- [ ] **NO global state**: Doesn't use module-level variables

### Implementation Anti-Patterns

- [ ] **NO test interdependencies**: Tests don't rely on each other
- [ ] **NO hardcoded waits**: No `time.sleep(5)` to wait for async
- [ ] **NO testing privates**: Doesn't test private methods/attributes
- [ ] **NO duplicate code**: Uses fixtures/factories for reuse
- [ ] **NO flaky tests**: Consistent pass/fail, not random

### Async-Specific Checks

**If testing async code:**
- [ ] **Uses `@pytest.mark.asyncio`**: Decorator present on all async tests
- [ ] **Matches code style**: Async code uses async tests, sync code uses sync tests
- [ ] **Uses `AsyncMock`**: Not regular `Mock` for async functions
- [ ] **Has timeout protection**: Uses `asyncio.wait_for()` or `asyncio.timeout()` where appropriate
- [ ] **Async fixtures for async resources**: Database connections, HTTP clients use async fixtures
- [ ] **Uses `await` correctly**: No `asyncio.run()` inside async tests
- [ ] **Verifies awaits**: Uses `.assert_awaited_once()` for mocked async calls
- [ ] **Proper cleanup**: Async fixtures use `yield` for guaranteed cleanup
- [ ] **No shared async state**: Each test gets fresh async resources
- [ ] **Event loop managed by pytest**: Not manually creating/closing event loops

---

## Integration with Project

### File Organization

- [ ] **Correct location**: In `tests/` directory
- [ ] **Mirrors source structure**: `tests/test_module.py` for `src/module.py`
- [ ] **conftest.py updated**: Shared fixtures added if needed
- [ ] **Tagged properly**: Integration tests have `@pytest.mark.integration`

### Documentation

- [ ] **Test docstrings**: Complex tests explained
- [ ] **README updated**: If new test patterns introduced
- [ ] **Examples provided**: For unusual/complex test patterns

---

## Before Committing

### Run Full Test Suite

- [ ] **All tests pass**: `pytest`
- [ ] **No skipped tests**: Unless intentionally marked
- [ ] **No warnings**: Fix pytest warnings
- [ ] **Coverage maintained**: `pytest --cov` shows 90%+

### Quality Checks

- [ ] **Linting passes**: `ruff check tests/`
- [ ] **Formatting applied**: `ruff format tests/`
- [ ] **Type checking**: `mypy tests/` (if used)
- [ ] **Security scan**: `bandit -r tests/` (if applicable)

### Git

- [ ] **Files staged**: `git add tests/`
- [ ] **Commit message**: Follows `../references/git-conventions.md`
- [ ] **No unrelated changes**: Only test-related changes included

---

## Common Issues Checklist

### If Tests Are Failing

- [ ] Run single test in isolation: `pytest -k test_name`
- [ ] Check fixture scopes (function vs class vs module)
- [ ] Verify no shared state between tests
- [ ] Check test execution order dependency
- [ ] Verify mocks are set up correctly
- [ ] Check for leftover state from previous tests

### If Tests Are Slow

- [ ] Profile tests: `pytest --durations=10`
- [ ] Check for real I/O (network, disk, database)
- [ ] Verify using in-memory database
- [ ] Check fixture scopes (can you use class/module?)
- [ ] Look for unnecessary sleeps/waits
- [ ] Ensure external services are mocked

### If Tests Are Flaky

- [ ] Check for time-dependent code (use freezegun)
- [ ] Look for race conditions (async code)
- [ ] Verify random data generation is seeded
- [ ] Check for order-dependent tests
- [ ] Look for shared mutable state
- [ ] Check for external dependencies not mocked

---

## Test Quality Score

Rate each test 1-5 for these criteria:

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Clear naming | __ | Descriptive, follows convention? |
| Proper isolation | __ | Independent, uses fixtures? |
| Meaningful assertions | __ | Tests behavior, specific checks? |
| Good coverage | __ | Happy path, edges, errors? |
| Fast execution | __ | < 100ms? |
| Maintainability | __ | DRY, clear, documented? |

**Target:** 4+ average across all criteria

**If < 4:** Refactor the test before committing

---

## Review Checklist for Test PRs

When reviewing tests in pull requests:

### Functionality

- [ ] Tests actually test what they claim to test
- [ ] Tests would catch the bug/verify the feature
- [ ] Edge cases and errors are covered
- [ ] No false positives (tests pass when they shouldn't)
- [ ] No false negatives (tests fail when they shouldn't)

### Quality

- [ ] Follows project testing standards
- [ ] Uses existing fixtures/factories when available
- [ ] Introduces new fixtures/factories appropriately
- [ ] Test names are clear and descriptive
- [ ] No anti-patterns present

### Coverage

- [ ] Coverage increased or maintained (90%+)
- [ ] All new code is tested
- [ ] Critical paths are tested
- [ ] No "superficial" tests just for coverage

---

## Self-Review Checklist

Before submitting tests for review:

1. **Read your own code**: Does it make sense?
2. **Run tests multiple times**: Do they always pass?
3. **Run tests in different orders**: `pytest --random-order`
4. **Run single tests**: Do they work in isolation?
5. **Check coverage**: `pytest --cov` - any gaps?
6. **Verify speed**: `pytest --durations=10` - any slow tests?
7. **Review against this checklist**: All items checked?

---

## Example: Good vs Bad Test Comparison

### ❌ BAD Test

```python
def test_1(user_factory):
    u = user_factory()
    assert u is not None  # Superficial
    u.email = "newemail@example.com"
    assert u.email == "newemail@example.com"  # Testing Python, not our code
```

**Issues:**
- Non-descriptive name
- Superficial assertion
- Tests multiple things
- Tests language features, not business logic

### ✓ GOOD Test

```python
def test_update_user_email_changes_email_field(user_factory, database_session):
    # Arrange
    user = user_factory(email="old@example.com")
    database_session.add(user)
    database_session.commit()

    # Act
    user.update_email("new@example.com")
    database_session.commit()

    # Assert
    refreshed_user = database_session.query(User).get(user.id)
    assert refreshed_user.email == "new@example.com"
```

**Why it's good:**
- Descriptive name
- AAA pattern clear
- Tests specific behavior
- Uses appropriate fixtures
- Verifies persistence (not just in-memory change)

---

## Summary

High-quality tests are:

✓ **Independent** - Can run in any order, in isolation
✓ **Fast** - Execute quickly (< 100ms each)
✓ **Reliable** - Consistent results, no flakiness
✓ **Maintainable** - Clear, DRY, well-organized
✓ **Meaningful** - Test behavior, not implementation
✓ **Comprehensive** - Happy path, edges, errors

Use this checklist for every test you write!
