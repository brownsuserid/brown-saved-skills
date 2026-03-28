# Testing Anti-Patterns Catalog

This reference covers testing code smells and bad practices.

## Test Structure Anti-Patterns

### The Secret Catcher (No Assertions)

**What:** Tests that don't actually assert anything meaningful.

**Why Bad:** Tests pass even when code is broken.

```python
# Bad: No real assertion
def test_create_user():
    user = create_user("alice", "alice@example.com")
    assert user is not None  # Just checks it didn't crash

# Good: Meaningful assertions
def test_create_user():
    user = create_user("alice", "alice@example.com")
    assert user.name == "alice"
    assert user.email == "alice@example.com"
    assert user.created_at is not None
```

### The Giant (Test Too Long)

**What:** Tests with 50+ lines testing multiple behaviors.

**Why Bad:** Hard to understand, hard to maintain, unclear what failed.

```python
# Bad: Giant test
def test_order_system():
    # Create user (10 lines)
    # Create products (10 lines)
    # Add to cart (10 lines)
    # Checkout (10 lines)
    # Verify order (10 lines)
    # Verify inventory (10 lines)

# Good: Focused tests
def test_create_order_creates_order_record(): ...
def test_create_order_decrements_inventory(): ...
def test_create_order_charges_payment(): ...
def test_create_order_sends_confirmation_email(): ...
```

### The Free Ride (Piggyback Assertions)

**What:** Adding unrelated assertions to existing tests.

**Why Bad:** Test name doesn't match what it tests.

```python
# Bad: Free ride
def test_user_login():
    user = login("alice", "password123")
    assert user.is_authenticated
    assert user.last_login is not None
    assert user.profile.avatar_url is not None  # Unrelated!
    assert calculate_tax(100) == 8.25  # Completely unrelated!

# Good: Separate tests
def test_user_login_authenticates_user(): ...
def test_user_login_updates_last_login(): ...
def test_user_profile_has_avatar(): ...  # Different test file
def test_calculate_tax_returns_correct_amount(): ...  # Different test file
```

## Test Independence Anti-Patterns

### The Interacting Tests

**What:** Tests that depend on other tests running first.

**Why Bad:** Random failures, can't run tests in isolation.

```python
# Bad: Shared state
user = None

def test_create_user():
    global user
    user = create_user("alice")
    assert user is not None

def test_update_user():  # Depends on test_create_user!
    user.email = "new@example.com"
    save(user)
    assert get_user(user.id).email == "new@example.com"

# Good: Each test independent
def test_create_user():
    user = create_user("alice")
    assert user is not None

def test_update_user():
    user = create_user("alice")  # Own setup
    user.email = "new@example.com"
    save(user)
    assert get_user(user.id).email == "new@example.com"
```

### The Shared Fixture Problem

**What:** Fixtures that modify state used by multiple tests.

**Why Bad:** Tests affect each other, order-dependent failures.

```python
# Bad: Shared mutable fixture
@pytest.fixture(scope="module")
def database():
    db = create_database()
    yield db
    db.drop()

def test_insert(database):
    database.insert({"id": 1})  # Modifies shared db

def test_count(database):  # Sees insert from previous test!
    assert database.count() == 0  # Fails!

# Good: Fresh fixture per test
@pytest.fixture
def database():
    db = create_database()
    yield db
    db.drop()
```

## Mocking Anti-Patterns

### The Mockery (Over-Mocking)

**What:** Mocking so much that you're testing mocks, not code.

**Why Bad:** Tests pass but code doesn't work in production.

```python
# Bad: Testing mocks
def test_process_order():
    mock_db = Mock()
    mock_email = Mock()
    mock_payment = Mock()
    mock_inventory = Mock()

    mock_payment.charge.return_value = True
    mock_inventory.reserve.return_value = True

    process_order(order, mock_db, mock_email, mock_payment, mock_inventory)

    mock_payment.charge.assert_called()  # Just verifying mock was called

# Good: Integration test with minimal mocking
def test_process_order():
    # Real database (Testcontainers)
    # Real payment (sandbox)
    # Mock only external services you don't control
    mock_email = Mock()

    result = process_order(order, db, mock_email, payment_client, inventory)

    assert result.status == "completed"
    assert db.get_order(order.id).status == "completed"
```

### The Wrong Level of Mocking

**What:** Mocking at the wrong abstraction level.

**Why Bad:** Misses integration issues.

```python
# Bad: Mock at wrong level
def test_get_user():
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"name": "alice"}
        user = user_service.get_user(1)
        assert user.name == "alice"

# Good: Mock at service boundary
def test_get_user():
    with patch.object(user_service, "_api_client") as mock_client:
        mock_client.get_user.return_value = User(name="alice")
        user = user_service.get_user(1)
        assert user.name == "alice"
```

## Test Quality Anti-Patterns

### The Liar (Misleading Test Names)

**What:** Test name doesn't describe what's tested.

**Why Bad:** Can't understand what failed from test name.

```python
# Bad: Vague/misleading names
def test_user(): ...
def test_login_works(): ...
def test_it(): ...

# Good: Descriptive names
def test_login_with_valid_credentials_returns_user(): ...
def test_login_with_invalid_password_raises_auth_error(): ...
def test_login_increments_failed_attempts_on_failure(): ...
```

### The Happy Path Only

**What:** Only testing success cases, no edge cases.

**Why Bad:** Edge cases cause production bugs.

```python
# Bad: Only happy path
def test_divide():
    assert divide(10, 2) == 5

# Good: Include edge cases
def test_divide_integers():
    assert divide(10, 2) == 5

def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_negative_numbers():
    assert divide(-10, 2) == -5

def test_divide_floats():
    assert divide(10, 3) == pytest.approx(3.333, rel=0.01)
```

### The Flaky Test

**What:** Tests that randomly pass or fail.

**Why Bad:** Erodes trust in test suite, ignored failures.

**Common causes:**
- Time-dependent logic
- Random data
- Race conditions
- External service dependencies
- Shared state

```python
# Bad: Time-dependent
def test_token_valid():
    token = create_token()
    time.sleep(0.001)  # Race condition!
    assert is_valid(token)

# Good: Control time
def test_token_valid(freezegun):
    with freeze_time("2024-01-01 12:00:00"):
        token = create_token()
    with freeze_time("2024-01-01 12:00:01"):
        assert is_valid(token)
```

### The Commented-Out Test

**What:** Tests that are commented out instead of deleted or fixed.

**Why Bad:** Indicates untested code, technical debt.

```python
# Bad
# def test_payment_processing():
#     # TODO: Fix this later
#     pass

# Good: Skip with reason
@pytest.mark.skip(reason="Payment sandbox unavailable - JIRA-123")
def test_payment_processing():
    ...

# Or delete and track in issue tracker
```

## Test Smell Anti-Patterns

### Copy-Paste Tests

**What:** Similar tests with minor variations copy-pasted.

**Why Bad:** Maintenance nightmare, bugs in copied code.

```python
# Bad: Copy-paste
def test_create_user_alice():
    user = create_user("alice", "alice@example.com")
    assert user.name == "alice"
    assert user.email == "alice@example.com"

def test_create_user_bob():
    user = create_user("bob", "bob@example.com")
    assert user.name == "bob"
    assert user.email == "bob@example.com"

# Good: Parametrize
@pytest.mark.parametrize("name,email", [
    ("alice", "alice@example.com"),
    ("bob", "bob@example.com"),
])
def test_create_user(name, email):
    user = create_user(name, email)
    assert user.name == name
    assert user.email == email
```

### Testing Implementation, Not Behavior

**What:** Tests that verify HOW code works, not WHAT it does.

**Why Bad:** Breaks on refactoring even when behavior unchanged.

```python
# Bad: Testing implementation
def test_cache_uses_dict():
    cache = Cache()
    cache.set("key", "value")
    assert "key" in cache._storage  # Implementation detail!
    assert isinstance(cache._storage, dict)

# Good: Testing behavior
def test_cache_stores_and_retrieves_values():
    cache = Cache()
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

## Detection Commands

```bash
# Find tests without assertions
rg "def test_" -A 20 tests/ | rg -v "assert|pytest.raises|expect"

# Find large test files
find tests/ -name "*.py" | xargs wc -l | sort -rn | head -10

# Find shared module-level state
rg "^[a-zA-Z_]+ = " tests/ --type py

# Find commented-out tests
rg "# *def test_" tests/

# Find TODO/FIXME in tests
rg "TODO|FIXME" tests/

# Find tests without parametrize that should have it
rg "def test_.*_[0-9]" tests/
```

## Detection Tools

| Issue | Tool | Command |
|-------|------|---------|
| Coverage gaps | pytest-cov | `pytest --cov --cov-report=html` |
| Slow tests | pytest-timeout | `pytest --timeout=5` |
| Test smells | pytest-deadfixtures | `pytest --dead-fixtures` |
| Mutation testing | mutmut | `mutmut run` |

## References

- [Software Testing Anti-patterns](https://blog.codepipes.com/testing/software-testing-antipatterns.html)
- [Unit Testing Anti-Patterns](https://www.yegor256.com/2018/12/11/unit-testing-anti-patterns.html)
- [pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
