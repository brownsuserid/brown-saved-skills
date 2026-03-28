# Unit Test Template

This template provides a structure for writing high-quality unit tests following best practices.

## Basic Test Template

```python
"""Tests for [module/feature] module."""

import pytest
from unittest.mock import Mock, patch

from app.[module] import [function/class_to_test]


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {
        "field1": "value1",
        "field2": 42,
        "field3": ["item1", "item2"],
    }


@pytest.fixture
def mock_external_service():
    """Mock external service dependency."""
    with patch('app.services.ExternalService') as mock:
        mock.return_value.method.return_value = "mocked_response"
        yield mock


# ==============================================================================
# HAPPY PATH TESTS
# ==============================================================================

def test_function_with_valid_input_returns_expected_output():
    """Test that function returns correct output for valid input."""
    # Arrange
    input_value = "test_input"
    expected_output = "expected_result"

    # Act
    result = function_to_test(input_value)

    # Assert
    assert result == expected_output


def test_class_method_with_valid_data_updates_state(sample_data):
    """Test that method correctly updates object state."""
    # Arrange
    obj = ClassToTest()
    initial_state = obj.get_state()

    # Act
    obj.method_under_test(sample_data)

    # Assert
    assert obj.get_state() != initial_state
    assert obj.field1 == sample_data["field1"]


# ==============================================================================
# EDGE CASES
# ==============================================================================

def test_function_with_empty_string_returns_empty_result():
    """Test that function handles empty string input."""
    # Arrange
    input_value = ""

    # Act
    result = function_to_test(input_value)

    # Assert
    assert result == ""


def test_function_with_none_returns_default_value():
    """Test that function returns default when given None."""
    # Arrange
    input_value = None
    expected_default = "default"

    # Act
    result = function_to_test(input_value)

    # Assert
    assert result == expected_default


@pytest.mark.parametrize("edge_value", [
    0,
    -1,
    float('inf'),
    -float('inf'),
])
def test_function_with_boundary_values(edge_value):
    """Test function behavior at boundary values."""
    # Arrange / Act
    result = function_to_test(edge_value)

    # Assert
    assert isinstance(result, (int, float))
    assert not math.isnan(result)


# ==============================================================================
# ERROR CASES
# ==============================================================================

def test_function_with_invalid_type_raises_type_error():
    """Test that function raises TypeError for invalid input type."""
    # Arrange
    invalid_input = 12345  # Wrong type

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        function_to_test(invalid_input)

    assert "expected string" in str(exc_info.value).lower()


def test_function_with_missing_required_field_raises_value_error():
    """Test that function raises ValueError when required field is missing."""
    # Arrange
    incomplete_data = {"field1": "value1"}  # Missing field2

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        function_to_test(incomplete_data)

    assert "field2" in str(exc_info.value)


# ==============================================================================
# INTEGRATION WITH DEPENDENCIES
# ==============================================================================

def test_function_calls_external_service_correctly(mock_external_service):
    """Test that function calls external service with correct parameters."""
    # Arrange
    input_data = {"key": "value"}

    # Act
    result = function_that_uses_service(input_data)

    # Assert
    mock_external_service.return_value.method.assert_called_once_with(
        key="value"
    )
    assert result == "mocked_response"


def test_function_handles_external_service_failure(mock_external_service):
    """Test that function handles external service errors gracefully."""
    # Arrange
    mock_external_service.return_value.method.side_effect = ConnectionError("Service down")

    # Act & Assert
    with pytest.raises(ServiceUnavailableError):
        function_that_uses_service({"key": "value"})


# ==============================================================================
# PARAMETRIZED TESTS
# ==============================================================================

@pytest.mark.parametrize("input_value,expected_output", [
    ("lowercase", "LOWERCASE"),
    ("UPPERCASE", "UPPERCASE"),
    ("MixedCase", "MIXEDCASE"),
    ("with spaces", "WITH SPACES"),
    ("special!@#", "SPECIAL!@#"),
])
def test_uppercase_conversion(input_value, expected_output):
    """Test uppercase conversion with various inputs."""
    # Act
    result = to_uppercase(input_value)

    # Assert
    assert result == expected_output


@pytest.mark.parametrize("invalid_input", [
    None,
    123,
    [],
    {},
])
def test_function_with_invalid_types_raises_error(invalid_input):
    """Test that function rejects invalid input types."""
    # Act & Assert
    with pytest.raises((TypeError, ValueError)):
        function_to_test(invalid_input)


# ==============================================================================
# STATE-BASED TESTING
# ==============================================================================

class TestStatefulClass:
    """Tests for stateful class operations."""

    @pytest.fixture
    def instance(self):
        """Provide fresh instance for each test."""
        return StatefulClass()

    def test_initial_state_is_correct(self, instance):
        """Test that new instance has correct initial state."""
        assert instance.state == "initial"
        assert instance.counter == 0

    def test_transition_changes_state(self, instance):
        """Test that transition method changes state correctly."""
        # Act
        instance.transition_to("active")

        # Assert
        assert instance.state == "active"

    def test_invalid_transition_raises_error(self, instance):
        """Test that invalid state transition raises error."""
        # Arrange
        instance.transition_to("active")

        # Act & Assert
        with pytest.raises(InvalidTransitionError):
            instance.transition_to("initial")  # Can't go back


# ==============================================================================
# ASYNC TESTS
# ==============================================================================
# NOTE: See references/async-testing-guide.md for comprehensive async patterns

@pytest.mark.asyncio
async def test_async_function_returns_expected_result():
    """Test async function behavior."""
    # Arrange
    input_value = "test"

    # Act
    result = await async_function(input_value)

    # Assert
    assert result == "expected"


@pytest.mark.asyncio
async def test_async_function_with_async_mock(mocker):
    """Test async function with mocked async dependency."""
    from unittest.mock import AsyncMock

    # Arrange
    mock_service = mocker.patch('app.services.fetch_data', new_callable=AsyncMock)
    mock_service.return_value = {"status": "success"}

    # Act
    result = await process_data()

    # Assert
    assert result["status"] == "success"
    mock_service.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_function_with_timeout():
    """Test async function respects timeout."""
    import asyncio

    # Act & Assert
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_async_operation(), timeout=1.0)


@pytest.mark.asyncio
async def test_async_database_query(async_db_session):
    """Test async database operation."""
    # Arrange
    user_id = 123

    # Act
    user = await async_db_session.get_user(user_id)

    # Assert
    assert user.id == user_id
    assert user.email is not None


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test multiple async operations run concurrently."""
    import asyncio

    # Act - runs concurrently
    results = await asyncio.gather(
        async_operation_1(),
        async_operation_2(),
        async_operation_3()
    )

    # Assert
    assert len(results) == 3
    assert all(r.status == "success" for r in results)
```

---

## conftest.py Template

```python
"""Shared fixtures for tests."""

import pytest
from factory import Faker
from pytest_factoryboy import register

from app.database import create_test_database
from tests.factories import UserFactory, OrderFactory


# ==============================================================================
# DATABASE FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def database_engine():
    """Create in-memory database for entire test session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def database_session(database_engine):
    """Provide database session with automatic rollback."""
    connection = database_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ==============================================================================
# ASYNC DATABASE FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
async def async_database_engine():
    """Create async database engine for test session."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_db_session(async_database_engine):
    """Provide async database session with automatic rollback."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(
        async_database_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ==============================================================================
# ASYNC HTTP CLIENT FIXTURES
# ==============================================================================

@pytest.fixture
async def async_http_client():
    """Provide async HTTP client."""
    import httpx

    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
async def async_test_app_client():
    """Provide async test client for FastAPI app."""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ==============================================================================
# FACTORY FIXTURES
# ==============================================================================

# Register factories as fixtures
register(UserFactory)
register(OrderFactory)


@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def _create_user(**kwargs):
        defaults = {
            "username": Faker("user_name"),
            "email": Faker("email"),
            "is_active": True,
        }
        defaults.update(kwargs)
        return User(**defaults)
    return _create_user


# ==============================================================================
# MOCK FIXTURES
# ==============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch('app.cache.redis_client') as mock:
        yield mock


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    with patch('app.services.EmailService') as mock:
        yield mock


# ==============================================================================
# APPLICATION FIXTURES
# ==============================================================================

@pytest.fixture
def app():
    """Create application instance for testing."""
    app = create_app(config="testing")
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client, user_factory):
    """Create authenticated test client."""
    user = user_factory()
    client.post('/auth/login', json={
        "username": user.username,
        "password": "password"
    })
    return client


# ==============================================================================
# CLEANUP FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    ConfigManager.reset()
    CacheManager.reset()
    yield


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
```

---

## factories.py Template

```python
"""Test data factories using Factory Boy."""

import factory
from factory import Faker
from faker import Factory as FakerFactory

from app.models import User, Order, Product


faker = FakerFactory.create()


class UserFactory(factory.Factory):
    """Factory for creating test users."""

    class Meta:
        model = User

    username = Faker("user_name")
    email = Faker("email")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    age = Faker("random_int", min=18, max=100)
    is_active = True
    created_at = Faker("date_time_this_year")


class ProductFactory(factory.Factory):
    """Factory for creating test products."""

    class Meta:
        model = Product

    name = Faker("word")
    description = Faker("text", max_nb_chars=200)
    price = Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    sku = Faker("uuid4")
    in_stock = True


class OrderFactory(factory.Factory):
    """Factory for creating test orders."""

    class Meta:
        model = Order

    order_id = Faker("uuid4")
    user = factory.SubFactory(UserFactory)
    total_amount = Faker("pydecimal", left_digits=5, right_digits=2, positive=True)
    status = "pending"
    created_at = Faker("date_time_this_month")


# Custom factory for specific scenarios
class AdminUserFactory(UserFactory):
    """Factory for admin users."""

    is_admin = True
    is_active = True
    email = factory.Sequence(lambda n: f"admin{n}@example.com")
```

---

## Usage Notes

1. **Copy template**: Start with this template for new test files
2. **Remove unused sections**: Delete sections you don't need
3. **Customize**: Adapt to your specific testing needs
4. **Follow conventions**: Maintain the organization structure
5. **Keep updated**: Update template as patterns evolve

## Template Sections

- **Fixtures**: Setup and teardown code
- **Happy Path**: Normal operation tests
- **Edge Cases**: Boundary conditions
- **Error Cases**: Exception handling
- **Dependencies**: External service integration
- **Parametrized**: Multiple scenario testing
- **State-Based**: Stateful object testing
- **Async**: Asynchronous operation testing

Choose the sections relevant to your code under test.
