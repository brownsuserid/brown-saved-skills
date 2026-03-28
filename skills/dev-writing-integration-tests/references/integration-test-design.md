# Integration Test Design

This guide explains what integration tests are, when to write them, and how to design them effectively.

## What Are Integration Tests?

Integration tests verify that **multiple components work together correctly**. They test the interactions between your code and:
- Databases
- External APIs
- Message queues
- File systems
- Other services
- Multiple modules working together

### Unit Tests vs Integration Tests

| Aspect | Unit Tests | Integration Tests |
|--------|-----------|-------------------|
| **Scope** | Single function/class | Multiple components |
| **Dependencies** | Mocked | Real (or containerized) |
| **Speed** | Very fast (<100ms) | Slower (100ms-5s) |
| **Isolation** | Complete | Limited |
| **Purpose** | Verify logic | Verify integration |
| **Failures** | Point to specific bug | Point to integration issue |
| **Run frequency** | Every commit | Pre-merge, CI/CD |

### Example

**Unit Test:**
```python
def test_calculate_total_price(mock_database):
    # Mock the database
    mock_database.get_price.return_value = 10.00

    # Test the calculation logic
    total = calculate_order_total(item_id=123, quantity=2)

    assert total == 20.00
```

**Integration Test:**
```python
@pytest.mark.integration
def test_complete_order_flow(database_session, api_client):
    # Use REAL database and API client
    # Test the entire flow
    product = create_product("Widget", price=10.00)
    database_session.add(product)
    database_session.commit()

    # Make real API call
    response = api_client.post('/orders', json={
        "product_id": product.id,
        "quantity": 2
    })

    # Verify end-to-end behavior
    assert response.status_code == 201
    order = database_session.query(Order).first()
    assert order.total == 20.00
    assert order.status == "pending"
```

---

## When to Write Integration Tests

### Write Integration Tests For:

✓ **End-to-end workflows** - User registration → email verification → login
✓ **Database operations** - Verify queries, transactions, constraints work
✓ **API endpoints** - Test request/response cycles
✓ **External service integration** - Payment gateways, email services
✓ **Message queue processing** - Pub/sub, job queues
✓ **File operations** - Reading/writing files, uploads
✓ **Multi-module interactions** - When several modules must work together

### Don't Write Integration Tests For:

✗ **Pure logic** - Use unit tests instead
✗ **Individual functions** - Unit tests are faster
✗ **Every edge case** - Cover edge cases in unit tests, happy path in integration
✗ **Isolated validation** - Unit tests are sufficient

### The Testing Pyramid

```
         /\
        /  \      E2E Tests (Few)
       /    \     - Full system
      /------\
     /        \   Integration Tests (Some)
    /          \  - Component interaction
   /------------\
  /              \ Unit Tests (Many)
 /                \ - Individual functions
/------------------\
```

**Rule of Thumb:**
- 70% Unit Tests
- 20% Integration Tests
- 10% End-to-End Tests

---

## Integration Test Design Principles

### 1. Test Realistic Scenarios

Integration tests should reflect real-world usage.

```python
@pytest.mark.integration
def test_user_registration_and_login_flow(api_client, database_session):
    """Test realistic user journey."""
    # Register new user
    register_response = api_client.post('/auth/register', json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "SecurePass123!"
    })
    assert register_response.status_code == 201

    # Verify user in database
    user = database_session.query(User).filter_by(
        username="newuser"
    ).first()
    assert user is not None
    assert user.is_verified is False

    # Login (should fail - not verified)
    login_response = api_client.post('/auth/login', json={
        "username": "newuser",
        "password": "SecurePass123!"
    })
    assert login_response.status_code == 403

    # Verify email
    verify_user(user.verification_token, database_session)

    # Login (should succeed now)
    login_response = api_client.post('/auth/login', json={
        "username": "newuser",
        "password": "SecurePass123!"
    })
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
```

### 2. Test One Integration Path Per Test

Each test should focus on one workflow or integration point.

```python
# ✓ GOOD: Tests one specific integration
@pytest.mark.integration
def test_order_creates_database_record_and_sends_email(
    api_client,
    database_session,
    mock_email_service
):
    """Test order creation integrates with DB and email service."""
    response = api_client.post('/orders', json={...})

    # Verify database integration
    order = database_session.query(Order).first()
    assert order is not None

    # Verify email integration
    mock_email_service.send.assert_called_once()
```

```python
# ❌ BAD: Tests too many unrelated integrations
@pytest.mark.integration
def test_everything():
    # Tests orders, users, products, payments all at once
    # If this fails, what integration broke?
```

### 3. Use Real Dependencies (or Close Equivalents)

Integration tests should use actual databases, services, etc.

**Preferred Approaches:**

1. **Testcontainers** - Spin up real services in Docker
```python
@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres
```

2. **Docker Compose** - Define test environment
```yaml
# docker-compose.test.yml
services:
  test_db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: test
```

3. **In-Memory Alternatives** - For databases
```python
@pytest.fixture
def database_engine():
    # SQLite in-memory for speed
    return create_engine("sqlite:///:memory:")
```

### 4. Maintain Test Data Isolation

Each integration test should have isolated data.

**Transaction Rollback Pattern:**
```python
@pytest.fixture
def database_session(database_engine):
    """Session that rolls back after each test."""
    connection = database_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()  # Undo all changes
    connection.close()
```

**Cleanup Pattern:**
```python
@pytest.fixture
def api_client(database_session):
    client = TestClient(app)
    yield client

    # Clean up created resources
    database_session.query(Order).delete()
    database_session.query(User).delete()
    database_session.commit()
```

### 5. Tag Integration Tests

Use markers to separate integration from unit tests.

```python
@pytest.mark.integration
def test_database_integration():
    ...
```

**Run only integration tests:**
```bash
pytest -m integration
```

**Skip integration tests (for fast feedback):**
```bash
pytest -m "not integration"
```

**In CI/CD:**
```yaml
# Run unit tests on every commit
- name: Run unit tests
  run: pytest -m "not integration"

# Run integration tests before merge
- name: Run integration tests
  run: pytest -m integration
```

---

## Common Integration Test Patterns

### Pattern 1: Database Integration

```python
@pytest.mark.integration
class TestUserRepository:
    """Test user repository database operations."""

    def test_create_user_persists_to_database(self, database_session):
        # Create user
        user = User(username="john", email="john@example.com")
        database_session.add(user)
        database_session.commit()

        # Verify persistence
        retrieved = database_session.query(User).filter_by(
            username="john"
        ).first()
        assert retrieved is not None
        assert retrieved.email == "john@example.com"

    def test_unique_email_constraint_enforced(self, database_session):
        # Create first user
        user1 = User(username="john", email="test@example.com")
        database_session.add(user1)
        database_session.commit()

        # Try to create duplicate email
        user2 = User(username="jane", email="test@example.com")
        database_session.add(user2)

        with pytest.raises(IntegrityError):
            database_session.commit()
```

### Pattern 2: API Endpoint Integration

```python
@pytest.mark.integration
class TestOrderAPI:
    """Test order API endpoints."""

    def test_create_order_endpoint(self, api_client, database_session):
        # Create product first
        product = Product(name="Widget", price=10.00)
        database_session.add(product)
        database_session.commit()

        # Call API
        response = api_client.post('/orders', json={
            "product_id": product.id,
            "quantity": 2
        })

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 20.00

        # Verify database
        order = database_session.query(Order).get(data["id"])
        assert order is not None
        assert order.product_id == product.id

    def test_get_order_returns_correct_data(
        self,
        api_client,
        database_session
    ):
        # Setup: Create order in database
        order = Order(total=50.00, status="pending")
        database_session.add(order)
        database_session.commit()

        # Call API
        response = api_client.get(f'/orders/{order.id}')

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order.id
        assert data["total"] == 50.00
```

### Pattern 3: External Service Integration

```python
@pytest.mark.integration
def test_payment_processing_integration(
    database_session,
    payment_gateway_container  # Real or containerized service
):
    """Test integration with payment gateway."""
    # Create order
    order = Order(total=100.00, status="pending")
    database_session.add(order)
    database_session.commit()

    # Process payment with real gateway
    result = process_payment(
        order_id=order.id,
        amount=100.00,
        gateway_url=payment_gateway_container.get_connection_url()
    )

    # Verify result
    assert result.status == "success"
    assert result.transaction_id is not None

    # Verify database updated
    database_session.refresh(order)
    assert order.status == "paid"
    assert order.payment_transaction_id == result.transaction_id
```

### Pattern 4: Message Queue Integration

```python
@pytest.mark.integration
def test_order_created_event_published(
    database_session,
    message_queue_container,
    consumer
):
    """Test that order creation publishes event to queue."""
    # Create order
    order = create_order(
        product_id=123,
        quantity=2,
        queue_url=message_queue_container.get_connection_url()
    )

    # Wait for message
    messages = consumer.receive_messages(timeout=5)

    # Verify message published
    assert len(messages) == 1
    message = json.loads(messages[0].body)
    assert message["event_type"] == "order_created"
    assert message["order_id"] == order.id
```

---

## Test Organization

### File Structure

```
tests/
├── unit/                        # Unit tests (fast)
│   ├── test_validators.py
│   ├── test_calculators.py
│   └── test_utils.py
│
├── integration/                 # Integration tests (slower)
│   ├── conftest.py             # Integration-specific fixtures
│   ├── test_user_api.py
│   ├── test_order_workflow.py
│   ├── test_database_operations.py
│   └── test_external_services.py
│
└── conftest.py                  # Shared fixtures
```

### Naming Conventions

```python
# File names
test_[feature]_integration.py
test_[api_endpoint]_api.py
test_[workflow]_flow.py

# Test names
test_[action]_[integration_point]_[expected_result]

# Examples:
def test_create_order_saves_to_database_and_returns_201():
    ...

def test_user_registration_sends_verification_email():
    ...

def test_payment_processing_updates_order_status():
    ...
```

---

## Performance Considerations

### Keep Integration Tests Reasonably Fast

**Target:** < 5 seconds per integration test

**Strategies:**

1. **Use transactions for cleanup** (fast rollback)
2. **Minimize test data** (only what's needed)
3. **Reuse containers** (module/session scope)
4. **Run in parallel** (pytest-xdist)
5. **Use fast database backends** (PostgreSQL > MySQL for tests)

### Parallelize When Possible

```bash
# Run integration tests in parallel
pytest -m integration -n auto  # Uses all CPU cores
```

**Requirements:**
- Tests must be independent
- Each test gets isolated database
- No shared state

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Testing Too Much in One Test

```python
# BAD: Tests entire application
def test_everything():
    # User registration
    # Product creation
    # Order placement
    # Payment processing
    # Email sending
    # Report generation
    # ... 200 lines later
```

**Solution:** Break into focused tests, one integration per test.

### ❌ Mistake 2: Not Cleaning Up Test Data

```python
# BAD: Data persists between tests
def test_create_user():
    user = User(username="test")
    session.add(user)
    session.commit()
    # No cleanup!
```

**Solution:** Use transaction rollback or explicit cleanup.

### ❌ Mistake 3: Slow Tests Due to Unnecessary Setup

```python
# BAD: Starts containers for every test
def test_query_user():
    container = start_postgres_container()  # SLOW!
    # ... test
    container.stop()
```

**Solution:** Use module or session-scoped fixtures for containers.

### ❌ Mistake 4: Testing Implementation Instead of Integration

```python
# BAD: This is a unit test, not integration
@pytest.mark.integration
def test_calculate_total():
    # No database, no API, no external service
    # Just testing calculation logic
    assert calculate_total(10, 2) == 20
```

**Solution:** Integration tests must test actual integration between components.

---

## Integration Test Checklist

Before writing an integration test:

- [ ] Does this test the integration between 2+ components?
- [ ] Would unit tests be sufficient? (If yes, write unit tests)
- [ ] Is this testing a realistic user workflow?
- [ ] Are dependencies real (or containerized)?
- [ ] Is test data isolated from other tests?
- [ ] Is the test marked with `@pytest.mark.integration`?
- [ ] Will this test complete in < 5 seconds?
- [ ] Does cleanup happen reliably (rollback or explicit)?
- [ ] Is this test independent of execution order?
- [ ] Does the test name describe the integration being tested?

---

## Summary

**Integration tests:**
- Verify components work together
- Use real (or containerized) dependencies
- Are slower than unit tests but faster than E2E
- Should cover realistic workflows
- Need proper isolation and cleanup
- Are marked with `@pytest.mark.integration`

**Best practices:**
- One integration path per test
- Use transactions for cleanup
- Containerize external services
- Keep tests < 5 seconds
- Run in CI/CD before merge
- Focus on happy path + critical error cases
