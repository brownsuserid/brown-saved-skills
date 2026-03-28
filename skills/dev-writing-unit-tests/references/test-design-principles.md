# Test Design Principles

This guide covers the core principles for writing meaningful, maintainable unit tests that avoid common anti-patterns.

## The AAA Pattern (Arrange-Act-Assert)

Every test should follow the AAA pattern for clarity and maintainability.

### Structure

```python
def test_user_creation_sets_default_role():
    # ARRANGE: Set up test data and preconditions
    username = "testuser"
    email = "test@example.com"

    # ACT: Execute the code being tested
    user = create_user(username=username, email=email)

    # ASSERT: Verify the expected outcome
    assert user.role == "member"
    assert user.username == username
    assert user.email == email
```

### Why AAA?

- **Clarity**: Anyone reading the test knows exactly what's being tested
- **Maintainability**: Each section has a clear purpose
- **Debuggability**: Easy to pinpoint where a test fails

### Visual Separation

Use blank lines or comments to separate the three sections:

```python
def test_calculate_discount():
    # Arrange
    price = 100.0
    discount_rate = 0.2

    # Act
    final_price = calculate_discount(price, discount_rate)

    # Assert
    assert final_price == 80.0
```

---

## Test One Thing at a Time

Each test should verify **one logical concept** or **one behavior**.

### ❌ BAD: Testing Multiple Behaviors

```python
def test_user_operations():
    # Testing too many things at once
    user = create_user("john", "john@example.com")
    assert user.username == "john"

    user.update_email("newemail@example.com")
    assert user.email == "newemail@example.com"

    user.deactivate()
    assert user.is_active is False

    # If this fails, which behavior is broken?
```

**Problems:**
- Hard to identify what's broken when test fails
- If first assertion fails, you never test the rest
- Violates single responsibility principle

### ✓ GOOD: Separate Tests for Each Behavior

```python
def test_create_user_sets_username():
    user = create_user("john", "john@example.com")
    assert user.username == "john"

def test_update_email_changes_user_email():
    user = create_user("john", "john@example.com")

    user.update_email("newemail@example.com")

    assert user.email == "newemail@example.com"

def test_deactivate_sets_is_active_to_false():
    user = create_user("john", "john@example.com")

    user.deactivate()

    assert user.is_active is False
```

**Benefits:**
- Clear failure messages
- Independent tests (no cascade failures)
- Documents each behavior separately

---

## Write Meaningful Tests, Not Superficial Ones

### Anti-Pattern: Secret Catcher

A test that appears to do no testing due to absence of assertions.

#### ❌ BAD: No Assertions

```python
def test_process_payment():
    # Just calling the function - no verification!
    process_payment(user_id=123, amount=50.00)
    # If this doesn't throw an exception, test passes
    # But did it actually work correctly?
```

**Problem:** Relies on exceptions being thrown. Doesn't verify correct behavior.

#### ✓ GOOD: Explicit Assertions

```python
def test_process_payment_creates_transaction():
    user_id = 123
    amount = 50.00

    result = process_payment(user_id=user_id, amount=amount)

    assert result.status == "completed"
    assert result.amount == amount
    assert result.user_id == user_id
    # Verify in database if needed
    transaction = get_transaction(result.transaction_id)
    assert transaction is not None
```

### Anti-Pattern: Dodger

A test with lots of tests for minor side effects but never tests the core desired behavior.

#### ❌ BAD: Testing Everything Except the Important Part

```python
def test_send_welcome_email():
    user = User(username="john", email="john@example.com")

    # Testing side effects, not main behavior
    assert user.username == "john"  # Not what we're testing
    assert user.email is not None   # Not the point
    assert "@" in user.email        # Still avoiding the real test

    send_welcome_email(user)

    # Never actually verifies email was sent!
```

**Problem:** Tests everything except whether the email was actually sent.

#### ✓ GOOD: Test the Core Behavior

```python
def test_send_welcome_email_sends_email_to_user(mock_email_service):
    user = User(username="john", email="john@example.com")

    send_welcome_email(user)

    # Verify the CORE behavior
    mock_email_service.send.assert_called_once_with(
        to=user.email,
        subject="Welcome!",
        template="welcome_email"
    )
```

### Anti-Pattern: Null Assertions

Tests with assertions that don't actually verify anything meaningful.

#### ❌ BAD: Meaningless Assertions

```python
def test_get_user_data():
    data = get_user_data(user_id=123)

    assert data is not None  # Too vague
    assert isinstance(data, dict)  # Doesn't verify correctness
    assert len(data) > 0  # Doesn't verify content
```

**Problem:** Tests pass even if data is completely wrong.

#### ✓ GOOD: Specific, Meaningful Assertions

```python
def test_get_user_data_returns_correct_fields():
    user_id = 123

    data = get_user_data(user_id=user_id)

    assert data["user_id"] == user_id
    assert data["username"] is not None
    assert data["email"] is not None
    assert "created_at" in data
    assert isinstance(data["created_at"], datetime)
```

---

## Use Descriptive Test Names

Test names should describe **what** is being tested and **what** the expected outcome is.

### Naming Convention

```
test_[unit_being_tested]_[scenario]_[expected_behavior]
```

### ❌ BAD: Enumerated Names

```python
def test_user_1():
    ...

def test_user_2():
    ...

def test_create():
    ...
```

**Problem:** No idea what's being tested without reading the code.

### ✓ GOOD: Descriptive Names

```python
def test_create_user_with_valid_email_succeeds():
    ...

def test_create_user_with_invalid_email_raises_validation_error():
    ...

def test_update_user_email_sends_confirmation_email():
    ...

def test_deactivate_user_prevents_login():
    ...
```

**Benefits:**
- Self-documenting
- Clear failure messages
- Searchable

---

## Test Behavior, Not Implementation

Tests should verify **what** the code does, not **how** it does it.

### ❌ BAD: Testing Implementation Details

```python
def test_calculate_total_price():
    cart = ShoppingCart()
    cart.add_item("apple", 1.00)
    cart.add_item("banana", 0.50)

    # Testing internal state/implementation
    assert len(cart._items) == 2  # Private attribute!
    assert cart._items[0]["name"] == "apple"  # Internal structure!

    total = cart.calculate_total()
    assert total == 1.50
```

**Problems:**
- Breaks when refactoring internal implementation
- Couples tests to implementation details
- Makes code harder to refactor

### ✓ GOOD: Testing Public Behavior

```python
def test_calculate_total_price_sums_all_items():
    cart = ShoppingCart()
    cart.add_item("apple", 1.00)
    cart.add_item("banana", 0.50)

    total = cart.calculate_total()

    # Only test the public behavior
    assert total == 1.50
```

**Benefits:**
- Can refactor internal implementation freely
- Tests remain valid as long as behavior is correct
- Focuses on user-facing functionality

---

## Use Parametrization for Multiple Scenarios

When testing the same behavior with different inputs, use `pytest.mark.parametrize`.

### ❌ BAD: Duplicate Test Code

```python
def test_is_valid_email_with_gmail():
    assert is_valid_email("user@gmail.com") is True

def test_is_valid_email_with_yahoo():
    assert is_valid_email("user@yahoo.com") is True

def test_is_valid_email_with_custom_domain():
    assert is_valid_email("user@company.co.uk") is True

def test_is_valid_email_missing_at():
    assert is_valid_email("usergmail.com") is False

def test_is_valid_email_missing_domain():
    assert is_valid_email("user@") is False
```

**Problems:**
- Lots of duplication
- Hard to maintain
- Adding new cases requires new functions

### ✓ GOOD: Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("email,expected", [
    ("user@gmail.com", True),
    ("user@yahoo.com", True),
    ("user@company.co.uk", True),
    ("usergmail.com", False),
    ("user@", False),
    ("@domain.com", False),
    ("", False),
])
def test_is_valid_email(email, expected):
    assert is_valid_email(email) == expected
```

**Benefits:**
- One test function, many scenarios
- Easy to add new cases
- Clear table of inputs/outputs
- Each case runs independently

### Multiple Parameters

```python
@pytest.mark.parametrize("price,discount,expected", [
    (100.0, 0.1, 90.0),
    (100.0, 0.5, 50.0),
    (100.0, 0.0, 100.0),
    (50.0, 0.2, 40.0),
])
def test_calculate_discounted_price(price, discount, expected):
    result = calculate_discount(price, discount)
    assert result == expected
```

---

## Keep Tests Fast

Unit tests should run quickly (< 100ms per test ideally).

### Guidelines

**DO:**
- Use in-memory databases (SQLite `:memory:`)
- Mock external API calls
- Mock file system operations
- Mock time-dependent operations

**DON'T:**
- Make real HTTP requests
- Access real databases (use fixtures/factories)
- Sleep or wait for arbitrary timeouts
- Access the file system unnecessarily

### ❌ BAD: Slow Test

```python
def test_fetch_user_data():
    # Makes real HTTP request - SLOW!
    response = requests.get("https://api.example.com/users/123")
    assert response.status_code == 200
```

### ✓ GOOD: Fast Test with Mock

```python
def test_fetch_user_data(mock_requests):
    mock_requests.get.return_value.status_code = 200
    mock_requests.get.return_value.json.return_value = {"id": 123}

    response = fetch_user_data(123)

    assert response["id"] == 123
```

---

## Test Edge Cases and Error Conditions

Don't just test the happy path—test what happens when things go wrong.

### What to Test

**Happy Path:**
- Normal, expected inputs
- Typical user workflows

**Edge Cases:**
- Boundary values (0, max int, empty strings)
- Empty collections ([], {}, "")
- None/null values
- Maximum/minimum valid values

**Error Cases:**
- Invalid inputs
- Missing required data
- Duplicate data when uniqueness required
- Permission/authorization failures
- External service failures

### Example

```python
def test_divide_normal_case():
    assert divide(10, 2) == 5.0

def test_divide_by_one():
    assert divide(10, 1) == 10.0

def test_divide_zero_numerator():
    assert divide(0, 5) == 0.0

def test_divide_negative_numbers():
    assert divide(-10, 2) == -5.0

def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_with_none_raises_type_error():
    with pytest.raises(TypeError):
        divide(None, 5)
```

---

## Avoid Test Interdependencies

Tests should be independent and runnable in any order.

### ❌ BAD: Tests Depend on Each Other

```python
# Global state shared between tests
current_user = None

def test_create_user():
    global current_user
    current_user = create_user("john", "john@example.com")
    assert current_user is not None

def test_update_user():
    # Depends on test_create_user running first!
    global current_user
    current_user.update_email("new@example.com")
    assert current_user.email == "new@example.com"
```

**Problems:**
- Tests fail when run in isolation
- Order-dependent (brittle)
- Hard to debug

### ✓ GOOD: Independent Tests

```python
@pytest.fixture
def user():
    return create_user("john", "john@example.com")

def test_create_user():
    user = create_user("john", "john@example.com")
    assert user is not None
    assert user.username == "john"

def test_update_user(user):
    user.update_email("new@example.com")
    assert user.email == "new@example.com"
```

---

## Use Assertions Wisely

### Multiple Related Assertions Are OK

It's OK to have multiple assertions if they're testing one logical concept:

```python
def test_create_user_sets_all_required_fields():
    user = create_user("john", "john@example.com", age=30)

    # All these assertions are testing one concept:
    # "user creation sets all fields correctly"
    assert user.username == "john"
    assert user.email == "john@example.com"
    assert user.age == 30
    assert user.is_active is True
    assert user.created_at is not None
```

### But Avoid Unrelated Assertions

```python
# ❌ BAD: Unrelated assertions
def test_user_and_product():
    user = create_user("john", "john@example.com")
    assert user.username == "john"

    product = create_product("Widget", 19.99)
    assert product.price == 19.99  # Different concept!
```

### Use pytest.raises for Exceptions

```python
def test_create_user_with_duplicate_email_raises_error():
    create_user("john", "john@example.com")

    with pytest.raises(DuplicateEmailError) as exc_info:
        create_user("jane", "john@example.com")

    # Can also assert on exception message
    assert "already exists" in str(exc_info.value)
```

---

## Documentation Through Tests

Tests serve as documentation—they show how code should be used.

### Example: Testing as Documentation

```python
def test_shopping_cart_workflow_example():
    """
    This test demonstrates the typical shopping cart workflow:
    1. Create empty cart
    2. Add items
    3. Apply discount code
    4. Calculate total
    5. Checkout
    """
    # Create cart
    cart = ShoppingCart()
    assert cart.is_empty() is True

    # Add items
    cart.add_item("Widget", price=10.00, quantity=2)
    cart.add_item("Gadget", price=15.00, quantity=1)

    # Apply discount
    cart.apply_discount_code("SAVE10")

    # Calculate total
    total = cart.calculate_total()
    assert total == 31.50  # (20 + 15) - 10% discount

    # Checkout
    order = cart.checkout(payment_method="credit_card")
    assert order.status == "completed"
```

---

## Summary: Principles Checklist

When writing a test, ask yourself:

- [ ] Does it follow AAA pattern?
- [ ] Does it test one logical concept?
- [ ] Are the assertions meaningful (not superficial)?
- [ ] Does it test behavior, not implementation?
- [ ] Is the test name descriptive?
- [ ] Is it independent of other tests?
- [ ] Does it run fast (<100ms)?
- [ ] Does it test edge cases and errors?
- [ ] Would a new developer understand what's being tested?
- [ ] Will it still pass if I refactor the internal implementation?

If you answer "no" to any of these, revisit the test design.
