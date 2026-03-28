# Async Testing Guide

This guide covers best practices for testing asynchronous code in Python using pytest-asyncio.

## When to Use Async vs Sync Tests

### The Golden Rule

**Match your test style to your code style.** If your code is async, your tests must be async. If your code is sync, your tests should be sync.

### Use Async Tests When:

#### ✅ Required by Syntax
- Testing functions defined with `async def`
- Testing code that uses `await`
- **It's a syntax error** to `await` inside a non-async function

#### ✅ Testing I/O-Bound Operations
- Database queries (especially with async libraries like `asyncpg`, `motor`, `databases`)
- HTTP requests to external APIs (with `aiohttp`, `httpx`)
- File I/O operations (with `aiofiles`)
- Network operations
- Any scenario where CPU is waiting on external resources

#### ✅ Testing Async Frameworks
- FastAPI endpoints and dependencies
- aiohttp web applications
- Async database libraries
- WebSocket handlers
- Any asyncio-based library

#### ✅ Performance Testing of Concurrent Operations
- Testing that multiple I/O operations happen concurrently
- Verifying timeout behavior
- Testing race conditions

### Use Sync Tests When:

#### ✅ Testing Synchronous Code
- Standard Python functions without `async`/`await`
- Traditional blocking code
- Code written for greenlet/gevent frameworks

#### ✅ CPU-Bound Operations
- Async won't help with CPU-bound tasks
- Need multiprocessing for CPU parallelism, not asyncio
- Pure computation, data transformation, algorithms

#### ✅ Simpler Test Setup
- No event loop management needed
- More straightforward test structure
- Easier to debug
- No need for `@pytest.mark.asyncio` decorators

---

## Setting Up Async Tests

### Installation

```bash
# Install pytest-asyncio
uv add --dev pytest-asyncio

# Or with pip
pip install pytest-asyncio
```

### Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # Automatically detect async tests
```

Or in `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

---

## Basic Async Test Pattern

### Simple Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function_returns_expected_result():
    """Test async function behavior."""
    # Arrange
    input_value = "test"

    # Act
    result = await async_function(input_value)

    # Assert
    assert result == "expected_output"
```

### Testing with Async Context Managers

```python
@pytest.mark.asyncio
async def test_async_database_query():
    """Test async database query."""
    async with get_database_session() as session:
        # Arrange
        user_id = 123

        # Act
        user = await session.get_user(user_id)

        # Assert
        assert user.id == user_id
        assert user.email == "test@example.com"
```

---

## Async Fixtures

Async fixtures are essential for managing async setup and teardown.

### Basic Async Fixture

```python
@pytest.fixture
async def async_client():
    """Provide async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client
    # Automatic cleanup when exiting context
```

### Async Database Fixture

```python
@pytest.fixture
async def database_session():
    """Provide async database session with rollback."""
    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Clean up after test
```

### Async Fixture with Dependencies

```python
@pytest.fixture
async def authenticated_user(database_session):
    """Create authenticated user for testing."""
    user = User(username="testuser", email="test@example.com")
    await database_session.add(user)
    await database_session.commit()

    token = create_auth_token(user.id)

    yield {"user": user, "token": token}

    # Cleanup
    await database_session.delete(user)
    await database_session.commit()
```

### Fixture Scopes with Async

```python
# Function scope (default) - fresh for each test
@pytest.fixture
async def fresh_connection():
    conn = await create_async_connection()
    yield conn
    await conn.close()

# Module scope - shared across test file (read-only!)
@pytest.fixture(scope="module")
async def shared_client():
    client = await create_async_client()
    yield client
    await client.close()
```

**Warning:** Be very careful with broader scopes (module, session). Ensure fixtures are read-only or you'll introduce test interdependencies.

---

## Mocking Async Code

### Using AsyncMock (Python 3.8+)

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_async_function_with_mock():
    """Test async function with mocked dependency."""
    # Arrange
    mock_service = AsyncMock()
    mock_service.fetch_data.return_value = {"status": "success"}

    # Act
    result = await process_data(mock_service)

    # Assert
    assert result["status"] == "success"
    mock_service.fetch_data.assert_awaited_once()
```

### Patching Async Functions

```python
@pytest.mark.asyncio
async def test_with_patched_async_function():
    """Test with patched async dependency."""
    with patch('app.services.fetch_remote_data', new_callable=AsyncMock) as mock_fetch:
        # Arrange
        mock_fetch.return_value = {"key": "value"}

        # Act
        result = await process_remote_data()

        # Assert
        assert result["key"] == "value"
        mock_fetch.assert_awaited_once()
```

### Using pytest-mock with Async

```python
@pytest.mark.asyncio
async def test_async_with_pytest_mock(mocker):
    """Test async code with pytest-mock."""
    # Arrange
    mock_api = mocker.patch('app.api.fetch_users', new_callable=AsyncMock)
    mock_api.return_value = [{"id": 1, "name": "Test"}]

    # Act
    users = await get_all_users()

    # Assert
    assert len(users) == 1
    assert users[0]["name"] == "Test"
```

### Mocking Side Effects

```python
@pytest.mark.asyncio
async def test_async_function_with_side_effect():
    """Test async function that raises exception."""
    mock_service = AsyncMock()
    mock_service.operation.side_effect = asyncio.TimeoutError()

    with pytest.raises(asyncio.TimeoutError):
        await call_external_service(mock_service)
```

---

## Testing Async Error Handling

### Testing Exceptions

```python
@pytest.mark.asyncio
async def test_async_function_raises_on_invalid_input():
    """Test that async function raises expected exception."""
    with pytest.raises(ValueError, match="Invalid user ID"):
        await get_user(user_id=-1)
```

### Testing Timeout Behavior

```python
@pytest.mark.asyncio
async def test_operation_respects_timeout():
    """Test that operation times out correctly."""
    import asyncio

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_operation(), timeout=1.0)
```

### Testing Error Recovery

```python
@pytest.mark.asyncio
async def test_retry_on_failure(mocker):
    """Test that function retries on failure."""
    mock_api = mocker.patch('app.api.fetch', new_callable=AsyncMock)
    mock_api.side_effect = [
        Exception("Network error"),  # First call fails
        Exception("Network error"),  # Second call fails
        {"status": "success"}        # Third call succeeds
    ]

    result = await fetch_with_retry(max_retries=3)

    assert result["status"] == "success"
    assert mock_api.await_count == 3
```

---

## Event Loop Management

### Common Issue: "Event Loop Already Running"

This error occurs when trying to start a new event loop while one is already active.

**Problem:**
```python
# ❌ BAD: Trying to run async code in sync context
def test_async_function():
    result = asyncio.run(async_function())  # Error if loop already running
```

**Solution:**
```python
# ✓ GOOD: Use pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()  # Works correctly
```

### Using asyncio_mode = "auto"

With `asyncio_mode = "auto"` in config, pytest-asyncio automatically handles:
- Creating event loops for async tests
- Cleaning up after tests
- Managing fixture event loops

### Manual Event Loop Control (Advanced)

```python
@pytest.fixture
def event_loop():
    """Create custom event loop for test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

---

## Performance Optimization

### Concurrent Test Execution

Async tests can run I/O-bound operations concurrently for faster execution.

**Example: Sequential (6 seconds total)**
```python
@pytest.mark.asyncio
async def test_three_api_calls_sequential():
    """Takes 6 seconds total."""
    result1 = await api_call_1()  # 2 seconds
    result2 = await api_call_2()  # 2 seconds
    result3 = await api_call_3()  # 2 seconds
```

**Better: Concurrent (2 seconds total)**
```python
@pytest.mark.asyncio
async def test_three_api_calls_concurrent():
    """Takes 2 seconds total."""
    result1, result2, result3 = await asyncio.gather(
        api_call_1(),
        api_call_2(),
        api_call_3()
    )
```

### Async Fixtures for Performance

```python
@pytest.fixture(scope="module")
async def expensive_async_setup():
    """Run once per module instead of per test."""
    # Expensive I/O operation
    data = await load_large_dataset_from_api()
    return data

@pytest.mark.asyncio
async def test_with_expensive_data(expensive_async_setup):
    """Reuses data loaded once."""
    result = process(expensive_async_setup)
    assert result is not None
```

---

## Testing Patterns

### Testing FastAPI Endpoints

```python
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_fastapi_endpoint():
    """Test FastAPI endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/users/123")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 123
```

### Testing with Async Database

```python
@pytest.mark.asyncio
async def test_database_transaction(database_session):
    """Test database operations with async session."""
    # Arrange
    user = User(username="testuser")

    # Act
    database_session.add(user)
    await database_session.commit()

    # Assert
    result = await database_session.execute(
        select(User).where(User.username == "testuser")
    )
    found_user = result.scalar_one()
    assert found_user.username == "testuser"
```

### Testing WebSocket Connections

```python
@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket message handling."""
    async with websockets.connect("ws://localhost:8000/ws") as websocket:
        # Send message
        await websocket.send(json.dumps({"type": "ping"}))

        # Receive response
        response = await websocket.recv()
        data = json.loads(response)

        assert data["type"] == "pong"
```

---

## Common Issues and Solutions

### Issue: Tests Hang Indefinitely

**Cause:** Awaiting something that never completes, no timeout.

**Solution:**
```python
@pytest.mark.asyncio
async def test_with_timeout():
    """Add timeout to prevent hanging."""
    async with asyncio.timeout(5.0):  # Python 3.11+
        result = await potentially_slow_operation()

    # Or for older Python:
    result = await asyncio.wait_for(
        potentially_slow_operation(),
        timeout=5.0
    )
```

### Issue: Flaky Tests

**Causes:**
- Race conditions
- Shared mutable state
- Improper cleanup
- Time-dependent code

**Solutions:**
```python
# ✓ GOOD: Proper isolation
@pytest.fixture
async def isolated_resource():
    """Each test gets fresh resource."""
    resource = await create_resource()
    yield resource
    await resource.cleanup()

# ✓ GOOD: Deterministic timing
@pytest.mark.asyncio
async def test_with_frozen_time(freezegun):
    """Use freezegun for deterministic time."""
    with freezegun.freeze_time("2025-01-01"):
        result = await time_dependent_function()
        assert result.timestamp == "2025-01-01"
```

### Issue: AsyncMock Not Working

**Cause:** Using regular `Mock` instead of `AsyncMock`.

**Solution:**
```python
# ❌ BAD: Regular Mock doesn't work with await
mock = Mock()
await mock()  # AttributeError

# ✓ GOOD: Use AsyncMock for async functions
mock = AsyncMock()
await mock()  # Works correctly
```

---

## Best Practices Summary

### Do's ✓

- **Match test style to code style** (async code → async tests)
- **Use `@pytest.mark.asyncio`** decorator for all async tests
- **Use `AsyncMock`** for mocking async functions
- **Use async fixtures** for async setup/teardown
- **Add timeouts** to prevent hanging tests
- **Leverage concurrency** with `asyncio.gather()` for performance
- **Use `asyncio_mode = "auto"`** in pytest configuration
- **Verify async operations** with `.assert_awaited_once()`
- **Isolate tests** with function-scoped fixtures (default)
- **Test error conditions** (exceptions, timeouts, retries)

### Don'ts ❌

- **Don't make sync code async unnecessarily** - adds complexity without benefit
- **Don't use regular `Mock`** for async functions - use `AsyncMock`
- **Don't use `asyncio.run()`** inside async tests - use `await`
- **Don't share mutable state** between async tests
- **Don't use broad fixture scopes** (module/session) with mutable data
- **Don't forget cleanup** - use `yield` in fixtures for guaranteed cleanup
- **Don't rely on execution order** - tests should be independent
- **Don't test implementation details** - test behavior
- **Don't use `time.sleep()`** in async code - use `asyncio.sleep()`
- **Don't skip pytest-asyncio** - it handles event loops correctly

---

## Quick Reference

### Basic Async Test
```python
@pytest.mark.asyncio
async def test_example():
    result = await async_function()
    assert result == expected
```

### Async Fixture
```python
@pytest.fixture
async def resource():
    r = await create()
    yield r
    await r.cleanup()
```

### Async Mock
```python
mock = AsyncMock()
mock.method.return_value = "result"
result = await mock.method()
mock.method.assert_awaited_once()
```

### Testing Exceptions
```python
@pytest.mark.asyncio
async def test_raises():
    with pytest.raises(ValueError):
        await function()
```

### Concurrent Operations
```python
@pytest.mark.asyncio
async def test_concurrent():
    results = await asyncio.gather(
        op1(),
        op2(),
        op3()
    )
```

---

## Further Reading

- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [AsyncMock documentation](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/advanced/async-tests/)
