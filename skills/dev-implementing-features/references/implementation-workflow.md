# Implementation Workflow — Deep Reference

This reference supplements the main SKILL.md with detailed TDD patterns, testing strategies, and troubleshooting guidance. Read this when you need more depth than the main skill provides.

## Table of Contents

- [TDD Patterns](#tdd-patterns)
- [Writing Effective Tests](#writing-effective-tests)
- [Integration Test Patterns](#integration-test-patterns)
- [TDD Best Practices](#tdd-best-practices)
- [Troubleshooting](#troubleshooting)

---

## TDD Patterns

### Starting with the Simplest Case

Begin with the most basic happy-path test. This establishes the function signature and return type before you get into edge cases:

```python
def test_calculate_discount_applies_percentage():
    """The simplest case: a straightforward percentage discount."""
    result = calculate_discount(price=100.0, rate=0.2)
    assert result == 80.0
```

Only after this passes do you layer in complexity:

```python
def test_calculate_discount_zero_rate_returns_original_price():
    """Zero discount should return the original price unchanged."""
    result = calculate_discount(price=100.0, rate=0.0)
    assert result == 100.0

def test_calculate_discount_rejects_negative_rate():
    """Negative rates don't make sense — should raise, not silently produce wrong values."""
    with pytest.raises(ValueError, match="rate must be between 0 and 1"):
        calculate_discount(price=100.0, rate=-0.1)

def test_calculate_discount_rejects_rate_above_one():
    """Rate > 1 usually means the caller passed a percentage (20) instead of a decimal (0.2)."""
    with pytest.raises(ValueError, match="rate must be between 0 and 1"):
        calculate_discount(price=100.0, rate=20)
```

### Testing Async Code

For async functions, use `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_user_returns_user_data():
    """Verify the async fetch returns structured user data."""
    result = await fetch_user(user_id="user_123")
    assert result["email"] == "user@example.com"
    assert "created_at" in result
```

### Testing with Fixtures

Use fixtures to share setup across tests without creating dependencies between them:

```python
@pytest.fixture
def sample_order():
    """A realistic order for testing discount calculations."""
    return Order(
        items=[
            OrderItem(name="Widget", price=29.99, quantity=2),
            OrderItem(name="Gadget", price=49.99, quantity=1),
        ],
        customer_id="cust_456",
    )

def test_order_total_before_discount(sample_order):
    assert sample_order.total == 109.97

def test_order_apply_discount(sample_order):
    sample_order.apply_discount(0.1)
    assert sample_order.total == pytest.approx(98.97, abs=0.01)
```

---

## Writing Effective Tests

### Name Tests Descriptively

Test names should read as specifications. Someone reading just the test names should understand what the function does:

```python
# Good — reads as a specification
def test_parse_email_extracts_domain_from_valid_address():
def test_parse_email_raises_value_error_for_missing_at_sign():
def test_parse_email_handles_plus_addressing():

# Bad — vague, tells you nothing
def test_parse_email():
def test_parse_email_2():
def test_error():
```

### Use AAA Pattern Consistently

Every test should have clear Arrange-Act-Assert sections:

```python
def test_merge_configs_prefers_override_values():
    # Arrange
    base = {"timeout": 30, "retries": 3, "verbose": False}
    override = {"timeout": 60, "verbose": True}

    # Act
    result = merge_configs(base, override)

    # Assert
    assert result["timeout"] == 60  # overridden
    assert result["retries"] == 3   # kept from base
    assert result["verbose"] is True  # overridden
```

### Test Behavior, Not Implementation

Tests should verify what a function does, not how it does it internally. This means your tests survive refactoring:

```python
# Good — tests the observable behavior
def test_sort_users_by_name_returns_alphabetical_order():
    users = [User("Charlie"), User("Alice"), User("Bob")]
    result = sort_users_by_name(users)
    assert [u.name for u in result] == ["Alice", "Bob", "Charlie"]

# Bad — tests implementation details (what sorting algorithm is used)
def test_sort_users_calls_builtin_sorted():
    with patch("builtins.sorted") as mock_sorted:
        sort_users_by_name([User("A")])
        mock_sorted.assert_called_once()
```

---

## Integration Test Patterns

Integration tests verify that components work together with real dependencies. Tag them so they can run separately:

```python
@pytest.mark.integration
def test_create_user_persists_to_database(db_session):
    """Full flow: create user via service layer, verify it's in the database."""
    # Arrange
    service = UserService(db_session)

    # Act
    user = service.create_user(email="test@example.com", name="Test User")

    # Assert
    saved = db_session.query(User).filter_by(email="test@example.com").first()
    assert saved is not None
    assert saved.name == "Test User"
    assert saved.id == user.id
```

### Running Integration Tests

Integration tests typically need environment variables for database connections, API keys, etc.:

```bash
cd [PROJECT_ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v
```

---

## TDD Best Practices

### Do

- Write one test at a time, make it pass, then write the next
- Start with the simplest test case and build complexity gradually
- Write minimal code to pass — resist adding features the tests don't require yet
- Refactor after tests pass, while they're still green
- Keep tests independent — each test should set up its own state
- Use descriptive names that read as specifications

### Avoid

- Writing implementation before tests — you lose the design benefit
- Writing multiple tests before implementing any — you lose the incremental feedback
- Skipping tests because "it's simple" — simple code still breaks
- Testing implementation details — these tests break on every refactor
- Modifying tests to make code pass — fix the code, not the tests
- Skipping the refactor step — technical debt accumulates fast

---

## Troubleshooting

### Tests Don't Pass After Implementation

**Symptoms:** Tests fail even though the code looks correct.

**Approach:**
1. Read the test output carefully — the assertion message usually tells you exactly what's wrong
2. Check test expectations vs actual implementation — is the test testing what you think?
3. Run a single test in isolation: `pytest -k test_specific_test -v`
4. Add print statements or use `pytest --pdb` to drop into a debugger at the failure point
5. Check for state leaking between tests — does the test pass alone but fail in the suite?

### Type Checking Fails

**Symptoms:** Mypy reports type errors on new code.

**Common fixes:**
- Add type hints to function parameters and returns
- Use `Optional[T]` for values that can be None
- Use `Union[T1, T2]` for multiple types
- Check that return type matches the declared type in all code paths
- For complex types, consider creating a TypedDict or dataclass

### Integration Tests Fail But Unit Tests Pass

**Symptoms:** Unit tests are green but integration tests reveal issues.

**This usually means:**
1. Mocks in unit tests don't match real service behavior — check API contracts
2. Database state isn't clean between tests — ensure test isolation
3. Environment variables aren't loaded — verify `.env` is sourced
4. Transaction handling differs between test and production — check commit/rollback behavior
5. Run integration tests individually to isolate: `pytest -k test_specific_integration -v`

### Merge Conflicts

**Symptoms:** Branch conflicts with main after rebasing.

**Resolution:**
1. `git fetch origin`
2. `git rebase origin/main`
3. Resolve conflicts in each file — keep your changes where intentional, accept upstream otherwise
4. Re-run all tests after resolving — merge resolution can introduce subtle bugs
5. `git rebase --continue`
