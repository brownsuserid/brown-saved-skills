# Test Isolation and Fixtures

This guide covers how to properly isolate tests from each other using pytest fixtures, avoiding common pitfalls with shared state and setup/teardown.

## Why Test Isolation Matters

**Test isolation ensures:**
- Tests can run in any order
- Tests can run in parallel
- One failing test doesn't cause cascade failures
- Tests are reproducible and deterministic
- Easy to debug (clear which test has the issue)

**Without isolation, you get:**
- Flaky tests (pass/fail randomly based on order)
- Cascade failures (one failure breaks many tests)
- Hard-to-debug issues
- Can't run tests in parallel
- Tests that pass locally but fail in CI

---

## Fixtures: The Foundation of Test Isolation

Fixtures provide a clean, isolated environment for each test. They handle setup and teardown automatically.

### Basic Fixture

```python
import pytest

@pytest.fixture
def user():
    """Provides a fresh user instance for each test."""
    # Setup: create user
    user = User(username="testuser", email="test@example.com")

    # Provide to test
    yield user

    # Teardown: cleanup (if needed)
    user.delete()  # Optional cleanup
```

Usage:

```python
def test_user_creation(user):
    # 'user' is automatically provided by the fixture
    assert user.username == "testuser"

def test_user_email(user):
    # Gets a FRESH user instance, independent of previous test
    assert user.email == "test@example.com"
```

### ✓ Benefits

- Each test gets a fresh instance
- Automatic cleanup via `yield`
- No shared state between tests
- Clear, reusable setup code

---

## Fixture Scopes

Fixtures can have different scopes to optimize test performance while maintaining isolation.

### Function Scope (Default)

**Runs once per test function** - Maximum isolation.

```python
@pytest.fixture  # scope="function" is default
def database_connection():
    """New database connection for each test."""
    conn = create_connection()
    yield conn
    conn.close()
```

**Use when:**
- Each test needs completely fresh state
- Setup/teardown is fast (<10ms)
- Maximum isolation is priority

### Class Scope

**Runs once per test class** - Tests in same class share fixture.

```python
@pytest.fixture(scope="class")
def database_with_users():
    """Shared database with test users for a test class."""
    db = create_test_database()
    db.seed_users()
    yield db
    db.drop()

class TestUserQueries:
    def test_find_user(self, database_with_users):
        user = database_with_users.find_user("john")
        assert user is not None

    def test_count_users(self, database_with_users):
        count = database_with_users.count_users()
        assert count > 0
```

**Use when:**
- Related tests that don't modify shared state
- Setup is expensive (database seeding, etc.)
- Tests only READ from the fixture

**⚠️ Warning:**
- Don't modify the fixture in tests
- Tests must not depend on execution order

### Module Scope

**Runs once per test file** - All tests in file share fixture.

```python
@pytest.fixture(scope="module")
def api_client():
    """Single API client for entire test module."""
    client = APIClient()
    client.authenticate()
    yield client
    client.logout()
```

**Use when:**
- Very expensive setup (external service connections)
- Fixture is read-only
- Performance is critical

### Session Scope

**Runs once per entire test session** - Shared across all tests.

```python
@pytest.fixture(scope="session")
def docker_services():
    """Start Docker containers once for entire test run."""
    subprocess.run(["docker-compose", "up", "-d"])
    yield
    subprocess.run(["docker-compose", "down"])
```

**Use when:**
- Extremely expensive setup (Docker containers, etc.)
- Never modified during tests
- Same state valid for all tests

---

## Common Anti-Patterns and Solutions

### ❌ Anti-Pattern: Shared Mutable State

**Problem:**

```python
# Global variable shared between tests - BAD!
_test_users = []

def test_add_user():
    _test_users.append("john")
    assert len(_test_users) == 1

def test_remove_user():
    # Depends on test_add_user running first!
    _test_users.remove("john")
    assert len(_test_users) == 0
```

**Issues:**
- Order-dependent
- Fails when run in isolation
- Can't run in parallel

**✓ Solution: Use Fixtures**

```python
@pytest.fixture
def user_list():
    """Fresh list for each test."""
    return []

def test_add_user(user_list):
    user_list.append("john")
    assert len(user_list) == 1

def test_remove_user(user_list):
    user_list.append("john")  # Set up within test
    user_list.remove("john")
    assert len(user_list) == 0
```

### ❌ Anti-Pattern: Modifying Class-Scoped Fixtures

**Problem:**

```python
@pytest.fixture(scope="class")
def shopping_cart():
    return ShoppingCart()

class TestCart:
    def test_add_item(self, shopping_cart):
        shopping_cart.add("apple")
        assert shopping_cart.count() == 1

    def test_remove_item(self, shopping_cart):
        # Expects empty cart but previous test added "apple"!
        shopping_cart.add("banana")
        assert shopping_cart.count() == 1  # FAILS! Count is 2
```

**✓ Solution 1: Use Function Scope**

```python
@pytest.fixture  # function scope (default)
def shopping_cart():
    return ShoppingCart()

class TestCart:
    def test_add_item(self, shopping_cart):
        shopping_cart.add("apple")
        assert shopping_cart.count() == 1

    def test_remove_item(self, shopping_cart):
        shopping_cart.add("banana")
        assert shopping_cart.count() == 1  # Works! Fresh cart
```

**✓ Solution 2: Reset in Fixture**

```python
@pytest.fixture(scope="class")
def shopping_cart():
    cart = ShoppingCart()
    yield cart
    cart.clear()  # Reset after each test

# Or use autouse to reset before each test
@pytest.fixture(autouse=True)
def reset_cart(shopping_cart):
    shopping_cart.clear()
```

### ❌ Anti-Pattern: Poor Setup/Teardown

**Problem:**

```python
def test_database_operation():
    # Manual setup
    db = create_database()
    db.connect()

    # Test
    result = db.query("SELECT * FROM users")
    assert len(result) > 0

    # Manual teardown - EASY TO FORGET!
    db.disconnect()
    db.drop()
```

**Issues:**
- Easy to forget teardown
- Teardown skipped if test fails/raises exception
- Duplicate setup code across tests

**✓ Solution: Use Fixtures with Yield**

```python
@pytest.fixture
def database():
    # Setup
    db = create_database()
    db.connect()

    # Provide to test
    yield db

    # Teardown - ALWAYS runs, even if test fails
    db.disconnect()
    db.drop()

def test_database_operation(database):
    result = database.query("SELECT * FROM users")
    assert len(result) > 0
    # Teardown happens automatically
```

---

## conftest.py: Centralized Fixtures

`conftest.py` makes fixtures available across multiple test files without imports.

### Structure

```
tests/
├── conftest.py          # Root fixtures (available to all tests)
├── test_users.py
├── test_orders.py
└── api/
    ├── conftest.py      # API-specific fixtures
    ├── test_auth.py
    └── test_endpoints.py
```

### Root conftest.py

```python
# tests/conftest.py
import pytest

@pytest.fixture
def database():
    """Available to all tests."""
    db = create_test_database()
    yield db
    db.drop()

@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def _create_user(username="testuser", email=None):
        email = email or f"{username}@example.com"
        return User(username=username, email=email)
    return _create_user
```

### Module-Specific conftest.py

```python
# tests/api/conftest.py
import pytest

@pytest.fixture
def api_client(database):
    """API client - only available to tests in api/ folder."""
    client = APIClient(database=database)
    yield client
    client.close()
```

### Benefits

- No imports needed
- Organize fixtures by scope
- Avoid circular imports
- Clear fixture hierarchy

---

## Fixture Dependencies

Fixtures can depend on other fixtures.

```python
@pytest.fixture
def database():
    db = create_database()
    yield db
    db.drop()

@pytest.fixture
def user(database):
    """Depends on database fixture."""
    user = User(username="john")
    database.save(user)
    return user

@pytest.fixture
def authenticated_client(user):
    """Depends on user fixture (which depends on database)."""
    client = APIClient()
    client.login(user)
    return client

def test_api_call(authenticated_client):
    # All fixtures set up automatically in correct order:
    # database -> user -> authenticated_client
    response = authenticated_client.get("/profile")
    assert response.status_code == 200
```

---

## Factory Pattern with Factory Boy

For complex objects, use Factory Boy to generate realistic test data.

### Installation

```bash
uv add -D factory-boy faker pytest-factoryboy
```

### Define Factories

```python
# tests/factories.py
import factory
from factory import Faker

class UserFactory(factory.Factory):
    class Meta:
        model = User

    username = Faker("user_name")
    email = Faker("email")
    age = Faker("random_int", min=18, max=100)
    is_active = True

class OrderFactory(factory.Factory):
    class Meta:
        model = Order

    order_id = Faker("uuid4")
    user = factory.SubFactory(UserFactory)
    total_amount = Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    status = "pending"
```

### Register in conftest.py

```python
# tests/conftest.py
from pytest_factoryboy import register
from tests.factories import UserFactory, OrderFactory

# Register factories as fixtures
register(UserFactory)
register(OrderFactory)
```

### Use in Tests

```python
def test_create_user(user_factory):
    # Get a fresh user with random realistic data
    user = user_factory()

    assert user.username is not None
    assert "@" in user.email
    assert 18 <= user.age <= 100

def test_create_order(order_factory):
    # Order comes with a user automatically via SubFactory
    order = order_factory()

    assert order.user is not None
    assert order.total_amount > 0

def test_custom_user(user_factory):
    # Override specific fields
    user = user_factory(username="custom_user", age=25)

    assert user.username == "custom_user"
    assert user.age == 25
```

### Parametrize with Factories

```python
@pytest.mark.parametrize("username,email", [
    ("john", "john@example.com"),
    ("jane", "jane@example.com"),
])
def test_users_with_specific_data(user_factory, username, email):
    user = user_factory(username=username, email=email)

    assert user.username == username
    assert user.email == email
```

---

## Mocking External Dependencies

Mock external dependencies to keep tests fast and isolated.

### Using unittest.mock

```python
from unittest.mock import Mock, patch

@pytest.fixture
def mock_email_service():
    """Mock the email service."""
    with patch('app.services.EmailService') as mock:
        yield mock

def test_send_welcome_email(mock_email_service):
    user = User(username="john", email="john@example.com")

    send_welcome_email(user)

    # Verify email service was called correctly
    mock_email_service.send.assert_called_once_with(
        to=user.email,
        subject="Welcome!",
        template="welcome_email"
    )
```

### Using pytest-mock

```bash
uv add -D pytest-mock
```

```python
def test_fetch_user_data(mocker):
    # mocker is provided by pytest-mock
    mock_api = mocker.patch('app.api.get_user')
    mock_api.return_value = {"id": 123, "name": "John"}

    result = fetch_user_data(123)

    assert result["name"] == "John"
    mock_api.assert_called_once_with(123)
```

---

## Database Testing Best Practices

### Use Transactions for Isolation

```python
@pytest.fixture
def database_session():
    """Database session with automatic rollback."""
    connection = create_database_connection()
    transaction = connection.begin()

    yield connection

    # Rollback after test - database returns to clean state
    transaction.rollback()
    connection.close()
```

### Use In-Memory SQLite for Speed

```python
@pytest.fixture(scope="session")
def database_engine():
    """In-memory SQLite database for entire test session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def database_session(database_engine):
    """New session per test with automatic cleanup."""
    Session = sessionmaker(bind=database_engine)
    session = Session()

    yield session

    session.rollback()
    session.close()
```

---

## autouse Fixtures

Fixtures that run automatically for every test in scope.

```python
@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    UserManager.reset()
    ConfigManager.reset()
    yield
    # Cleanup if needed
```

**Use sparingly:**
- Good for: Resetting global state, cleanup
- Bad for: Expensive operations, most setup tasks

---

## Temporary Files and Directories

Use `tmp_path` fixture (built-in pytest).

```python
def test_save_file(tmp_path):
    # tmp_path is a Path object to a temporary directory
    file_path = tmp_path / "test_file.txt"

    save_data(file_path, "test content")

    assert file_path.exists()
    assert file_path.read_text() == "test content"
    # Automatically cleaned up after test
```

---

## Fixture Best Practices Summary

### ✓ DO

- Use fixtures for all setup/teardown
- Choose appropriate scope (default to `function`)
- Define shared fixtures in `conftest.py`
- Use `yield` for cleanup
- Use Factory Boy for complex test data
- Mock external dependencies
- Keep fixtures focused and single-purpose

### ❌ DON'T

- Use global variables for test state
- Modify class/module/session-scoped fixtures
- Forget teardown (use `yield` to guarantee it)
- Create God fixtures that do too much
- Share mutable state between tests
- Make tests depend on execution order

---

## Isolation Checklist

For each test file, verify:

- [ ] No global mutable state
- [ ] All setup/teardown in fixtures
- [ ] Appropriate fixture scopes chosen
- [ ] No test modifies shared fixtures
- [ ] Tests can run in any order
- [ ] Tests can run in isolation (pytest -k test_name)
- [ ] Each test gets fresh state
- [ ] Cleanup happens even on test failure
- [ ] External dependencies are mocked
- [ ] Database operations use transactions or in-memory DB

If all checked, your tests are properly isolated!
