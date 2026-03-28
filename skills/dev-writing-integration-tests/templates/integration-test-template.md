# Integration Test Template

This template provides structure for writing integration tests with external services.

## Complete Integration Test File Template

```python
"""Integration tests for [module/feature]."""

import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app, get_db
from app.models import Base, User, Order
from tests.factories import UserFactory, OrderFactory


# ==============================================================================
# CONTAINER FIXTURES (Module Scope - Start Once)
# ==============================================================================

@pytest.fixture(scope="module")
def postgres_container():
    """Provide PostgreSQL container for all tests in module."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def database_engine(postgres_container):
    """Create database engine connected to container."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    return engine


# ==============================================================================
# SESSION FIXTURES (Function Scope - Transaction Rollback)
# ==============================================================================

@pytest.fixture
def database_session(database_engine):
    """
    Provide database session with automatic rollback.

    Each test gets a fresh transaction that's rolled back after the test,
    ensuring complete isolation between tests.
    """
    connection = database_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ==============================================================================
# API CLIENT FIXTURE
# ==============================================================================

@pytest.fixture
def api_client(database_session):
    """
    Provide test API client with database override.

    FastAPI dependency injection is used to replace the production
    database with our test database session.
    """
    def get_test_db():
        yield database_session

    app.dependency_overrides[get_db] = get_test_db

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


# ==============================================================================
# INTEGRATION TESTS - DATABASE
# ==============================================================================

@pytest.mark.integration
class TestUserDatabaseIntegration:
    """Test User model database operations."""

    def test_create_user_persists_to_database(self, database_session):
        """Test that creating a user persists to the database."""
        # Arrange
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed123"
        )

        # Act
        database_session.add(user)
        database_session.commit()

        # Assert - verify persistence
        retrieved = database_session.query(User).filter_by(
            username="testuser"
        ).first()
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.id is not None

    def test_unique_email_constraint_enforced(self, database_session):
        """Test that database enforces unique email constraint."""
        # Arrange - create first user
        user1 = User(username="user1", email="same@example.com")
        database_session.add(user1)
        database_session.commit()

        # Act & Assert - try duplicate email
        user2 = User(username="user2", email="same@example.com")
        database_session.add(user2)

        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            database_session.commit()

    def test_cascade_delete_removes_related_orders(
        self,
        database_session,
        user_factory,
        order_factory
    ):
        """Test that deleting user cascades to delete orders."""
        # Arrange
        user = user_factory()
        database_session.add(user)
        database_session.commit()

        order1 = order_factory(user_id=user.id)
        order2 = order_factory(user_id=user.id)
        database_session.add_all([order1, order2])
        database_session.commit()

        order_ids = [order1.id, order2.id]

        # Act - delete user
        database_session.delete(user)
        database_session.commit()

        # Assert - orders should be deleted too
        for order_id in order_ids:
            assert database_session.query(Order).get(order_id) is None


# ==============================================================================
# INTEGRATION TESTS - API ENDPOINTS
# ==============================================================================

@pytest.mark.integration
class TestUserAPIIntegration:
    """Test User API endpoints with real database."""

    def test_create_user_endpoint_persists_to_database(
        self,
        api_client,
        database_session
    ):
        """Test POST /users creates user in database."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePass123!"
        }

        # Act - call API
        response = api_client.post("/users", json=user_data)

        # Assert - check response
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data

        # Assert - check database
        user = database_session.query(User).get(data["id"])
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"

    def test_get_user_endpoint_returns_database_data(
        self,
        api_client,
        database_session,
        user_factory
    ):
        """Test GET /users/{id} returns data from database."""
        # Arrange - create user in database
        user = user_factory(username="existinguser")
        database_session.add(user)
        database_session.commit()
        user_id = user.id

        # Act - call API
        response = api_client.get(f"/users/{user_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == "existinguser"

    def test_update_user_endpoint_modifies_database(
        self,
        api_client,
        database_session,
        user_factory
    ):
        """Test PUT /users/{id} updates database."""
        # Arrange
        user = user_factory(email="old@example.com")
        database_session.add(user)
        database_session.commit()
        user_id = user.id

        # Act
        response = api_client.put(f"/users/{user_id}", json={
            "email": "new@example.com"
        })

        # Assert - check response
        assert response.status_code == 200

        # Assert - check database updated
        database_session.refresh(user)
        assert user.email == "new@example.com"

    def test_delete_user_endpoint_removes_from_database(
        self,
        api_client,
        database_session,
        user_factory
    ):
        """Test DELETE /users/{id} removes from database."""
        # Arrange
        user = user_factory()
        database_session.add(user)
        database_session.commit()
        user_id = user.id

        # Act
        response = api_client.delete(f"/users/{user_id}")

        # Assert - check response
        assert response.status_code == 204

        # Assert - check database
        deleted_user = database_session.query(User).get(user_id)
        assert deleted_user is None


# ==============================================================================
# INTEGRATION TESTS - WORKFLOWS
# ==============================================================================

@pytest.mark.integration
class TestUserRegistrationWorkflow:
    """Test complete user registration workflow."""

    def test_complete_registration_flow(
        self,
        api_client,
        database_session,
        mock_email_service
    ):
        """
        Test end-to-end user registration workflow:
        1. Register user
        2. User created in database (unverified)
        3. Verification email sent
        4. Email verified
        5. User can login
        """
        # Step 1: Register
        register_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!"
        }
        register_response = api_client.post("/auth/register", json=register_data)

        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]

        # Step 2: Verify user in database (unverified)
        user = database_session.query(User).get(user_id)
        assert user is not None
        assert user.is_verified is False
        assert user.verification_token is not None

        # Step 3: Verify email sent
        mock_email_service.send.assert_called_once()
        email_call = mock_email_service.send.call_args
        assert email_call.kwargs["to"] == "newuser@example.com"
        assert "verify" in email_call.kwargs["subject"].lower()

        # Step 4: Verify email
        verify_response = api_client.post("/auth/verify", json={
            "token": user.verification_token
        })
        assert verify_response.status_code == 200

        # Refresh user from database
        database_session.refresh(user)
        assert user.is_verified is True

        # Step 5: Login succeeds
        login_response = api_client.post("/auth/login", json={
            "username": "newuser",
            "password": "SecurePass123!"
        })
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()


# ==============================================================================
# INTEGRATION TESTS - EXTERNAL SERVICES
# ==============================================================================

@pytest.mark.integration
class TestPaymentIntegration:
    """Test integration with payment service."""

    @pytest.fixture
    def payment_service_container(self):
        """Mock payment service in container."""
        from testcontainers.core.container import DockerContainer

        container = DockerContainer("payment-mock-service:latest")
        container.with_exposed_ports(8080)
        container.start()

        yield f"http://localhost:{container.get_exposed_port(8080)}"

        container.stop()

    def test_process_payment_integrates_with_payment_service(
        self,
        database_session,
        payment_service_container,
        order_factory
    ):
        """Test payment processing with external payment service."""
        # Arrange
        order = order_factory(total=100.00, status="pending")
        database_session.add(order)
        database_session.commit()

        # Act
        from app.services.payment import process_payment
        result = process_payment(
            order_id=order.id,
            amount=100.00,
            gateway_url=payment_service_container
        )

        # Assert - payment processed
        assert result.status == "success"
        assert result.transaction_id is not None

        # Assert - database updated
        database_session.refresh(order)
        assert order.status == "paid"
        assert order.payment_transaction_id == result.transaction_id


# ==============================================================================
# INTEGRATION TESTS - PERFORMANCE
# ==============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_bulk_user_creation_performance(database_session, user_factory):
    """Test that bulk user creation completes in reasonable time."""
    import time

    # Arrange
    num_users = 1000

    # Act
    start_time = time.time()

    users = [user_factory.build() for _ in range(num_users)]
    database_session.bulk_save_objects(users)
    database_session.commit()

    elapsed_time = time.time() - start_time

    # Assert - should complete in < 5 seconds
    assert elapsed_time < 5.0

    # Assert - all users created
    count = database_session.query(User).count()
    assert count == num_users
```

---

## conftest.py for Integration Tests

```python
"""Shared fixtures for integration tests."""

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.main import app, get_db
from app.models import Base
from tests.factories import UserFactory, OrderFactory


# ==============================================================================
# CONTAINERS (Session Scope)
# ==============================================================================

@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container for all integration tests."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Redis container for all integration tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


# ==============================================================================
# DATABASE FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def database_engine(postgres_container):
    """Database engine for all integration tests."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def database_session(database_engine):
    """Fresh database session with transaction rollback."""
    connection = database_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ==============================================================================
# API CLIENT
# ==============================================================================

@pytest.fixture
def api_client(database_session):
    """Test client with database override."""
    def get_test_db():
        yield database_session

    app.dependency_overrides[get_db] = get_test_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==============================================================================
# FACTORIES
# ==============================================================================

@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    return UserFactory


@pytest.fixture
def order_factory():
    """Factory for creating test orders."""
    return OrderFactory


# ==============================================================================
# MOCKS
# ==============================================================================

@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service for testing."""
    mock = Mock()
    monkeypatch.setattr('app.services.email.EmailService', mock)
    return mock


@pytest.fixture
def mock_payment_gateway(monkeypatch):
    """Mock payment gateway for testing."""
    mock = Mock()
    mock.process.return_value = {
        "status": "success",
        "transaction_id": "test_txn_123"
    }
    monkeypatch.setattr('app.services.payment.PaymentGateway', mock)
    return mock
```

---

## Usage Notes

1. **Copy template**: Use this as starting point for integration tests
2. **Mark tests**: Always use `@pytest.mark.integration`
3. **Session scope containers**: Start containers once per test session
4. **Function scope sessions**: Each test gets transaction rollback
5. **Test one integration**: Focus each test on one integration point
6. **Keep tests < 5s**: Use appropriate scopes and cleanup strategies
7. **Run selectively**: `pytest -m integration` or `pytest -m "not integration"`

## Common Patterns

- **Database integration**: Test CRUD operations persist correctly
- **API integration**: Test endpoints interact with database
- **Workflow integration**: Test multi-step processes end-to-end
- **External service**: Test integration with external APIs/services
- **Performance**: Test bulk operations complete in time
